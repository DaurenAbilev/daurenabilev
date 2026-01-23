import csv
import json
import math
import os
from datetime import datetime, timezone

import requests

PAIR = "EURKZT"
LAMBDA = 0.1
Z_THRESHOLD = 3.0
COOLDOWN_HOURS = 3
WARMUP_HOURS = 48
EPS = 1e-12

API_URL = "https://halykbank.kz/api/gradation-ccy"

STATE_PATH = os.path.join(os.path.dirname(__file__), "state.json")
HISTORY_PATH = os.path.join(os.path.dirname(__file__), "history.csv")


def now_utc_iso():
    return datetime.now(timezone.utc).isoformat()


def parse_iso(ts):
    return datetime.fromisoformat(ts)


def hours_between(ts_a, ts_b):
    dt_a = parse_iso(ts_a)
    dt_b = parse_iso(ts_b)
    return abs((dt_a - dt_b).total_seconds()) / 3600.0


def to_float(value):
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = value.strip().replace(" ", "").replace(",", ".")
        try:
            return float(cleaned)
        except ValueError:
            return None
    return None


def fetch_raw_rates():
    headers = {
        "accept": "*/*",
        "user-agent": "Mozilla/5.0",
    }
    response = requests.get(API_URL, headers=headers, timeout=20)
    response.raise_for_status()
    return response.json()


def normalize_rates(raw):
    entries = raw
    if isinstance(raw, dict):
        for key in ("data", "rates", "items", "result", "content"):
            if isinstance(raw.get(key), list):
                entries = raw[key]
                break
        else:
            entries = [raw]
    if not isinstance(entries, list):
        entries = [entries]

    normalized = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        pair = entry.get("pair") or entry.get("pairCode") or entry.get("ccyPair")
        if not pair:
            base = (
                entry.get("ccy")
                or entry.get("currency")
                or entry.get("base")
                or entry.get("baseCcy")
                or entry.get("fromCcy")
                or entry.get("currencyFrom")
                or entry.get("ccyCode")
            )
            quote = (
                entry.get("ccy2")
                or entry.get("quote")
                or entry.get("term")
                or entry.get("quoteCcy")
                or entry.get("toCcy")
                or entry.get("currencyTo")
            )
            if base and quote:
                pair = f"{base}/{quote}"
            elif base:
                base_str = str(base)
                if "/" in base_str or "-" in base_str:
                    pair = base_str
                elif (
                    len(base_str) == 6
                    and base_str.isalpha()
                    and base_str.upper().endswith("KZT")
                ):
                    pair = base_str
                else:
                    # Halyk rates are often quoted versus KZT.
                    pair = f"{base_str}/KZT"
        date = entry.get("date") or entry.get("rateDate") or entry.get("asOf")
        branch = entry.get("branch") or entry.get("branchId") or entry.get("office") or entry.get("filial")

        tiers_raw = None
        for key in ("tiers", "gradations", "rates", "items", "rateList", "lines"):
            val = entry.get(key)
            if isinstance(val, list):
                tiers_raw = val
                break
        if tiers_raw is None:
            buy = entry.get("buy") or entry.get("buyRate")
            sell = entry.get("sell") or entry.get("sellRate")
            if buy is not None or sell is not None:
                tiers_raw = [{"from": 0, "to": None, "buy": buy, "sell": sell}]

        tiers = []
        if isinstance(tiers_raw, list):
            for tier in tiers_raw:
                if not isinstance(tier, dict):
                    continue
                tiers.append(
                    {
                        "from": tier.get("from")
                        if "from" in tier
                        else tier.get("fromAmount") or tier.get("amountFrom"),
                        "to": tier.get("to")
                        if "to" in tier
                        else tier.get("toAmount") or tier.get("amountTo"),
                        "buy": tier.get("buy")
                        if "buy" in tier
                        else tier.get("buyRate") or tier.get("rateBuy"),
                        "sell": tier.get("sell")
                        if "sell" in tier
                        else tier.get("sellRate") or tier.get("rateSell"),
                    }
                )

        normalized.append(
            {
                "date": date,
                "branch": branch,
                "pair": pair,
                "tiers": tiers,
            }
        )
    return normalized


def select_price(normalized, pair):
    def norm_pair(value):
        return (value or "").replace("/", "").replace("-", "").upper()

    target = norm_pair(pair)
    for entry in normalized:
        if norm_pair(entry.get("pair")) != target:
            continue
        tiers = entry.get("tiers") or []
        chosen = None
        for tier in tiers:
            if tier.get("from") in (0, "0", None):
                chosen = tier
                break
        if chosen is None and tiers:
            chosen = tiers[0]
        if not chosen:
            continue
        buy = to_float(chosen.get("buy"))
        sell = to_float(chosen.get("sell"))
        if buy is not None and sell is not None:
            return (buy + sell) / 2.0
        if buy is not None:
            return buy
        if sell is not None:
            return sell
    raise ValueError(f"Pair {pair} not found in normalized data")


def fetch_price(pair):
    raw = fetch_raw_rates()
    normalized = normalize_rates(raw)
    return select_price(normalized, pair)


def load_state():
    if not os.path.exists(STATE_PATH):
        return {
            "prev_price": None,
            "mu": 0.0,
            "var": 1e-8,
            "last_alert_time": None,
            "n": 0,
        }
    with open(STATE_PATH, "r", encoding="utf-8") as handle:
        return json.load(handle)


def save_state(state):
    with open(STATE_PATH, "w", encoding="utf-8") as handle:
        json.dump(state, handle, ensure_ascii=True, indent=2)


def save_row(ts, price, r_value, z_value, alert_flag):
    is_new = not os.path.exists(HISTORY_PATH)
    with open(HISTORY_PATH, "a", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        if is_new:
            writer.writerow(["time", "price", "r", "z", "alert"])
        writer.writerow([ts, price, r_value, z_value, alert_flag])


def send_alert(message, ts, price, r_value, z_value):
    text = f"{message} | time={ts} price={price} r={r_value} z={z_value}"
    print(text)


def main():
    state = load_state()

    price = fetch_price(PAIR)
    ts = now_utc_iso()

    if state["prev_price"] is None:
        state["prev_price"] = price
        save_row(ts, price, "", "", "")
        save_state(state)
        return

    r_value = math.log(price / state["prev_price"])
    state["mu"] = LAMBDA * r_value + (1 - LAMBDA) * state["mu"]
    err = r_value - state["mu"]
    state["var"] = LAMBDA * (err ** 2) + (1 - LAMBDA) * state["var"]
    sigma = math.sqrt(state["var"] + EPS)
    z_value = err / sigma
    state["n"] += 1

    alert_flag = "no_alert"
    if state["n"] >= WARMUP_HOURS:
        in_cooldown = False
        if state["last_alert_time"]:
            in_cooldown = hours_between(ts, state["last_alert_time"]) < COOLDOWN_HOURS
        if abs(z_value) >= Z_THRESHOLD and not in_cooldown:
            send_alert("EUR/KZT strong 1h move", ts, price, r_value, z_value)
            state["last_alert_time"] = ts
            alert_flag = "alert"

    save_row(ts, price, r_value, z_value, alert_flag)
    state["prev_price"] = price
    save_state(state)


if __name__ == "__main__":
    main()
