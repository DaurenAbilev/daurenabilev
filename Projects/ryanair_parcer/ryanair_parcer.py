import requests
from telethon import TelegramClient
from dotenv import load_dotenv
import json
import os 
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
import asyncio

def get_env_variables():

    load_dotenv()

    API_ID = os.getenv("API_ID")
    API_HASH = os.getenv("API_HASH")
    USER_ID = os.getenv("USER_ID")

    if not API_ID:
        raise ValueError("API_ID is missing")
    if not API_HASH:
        raise ValueError("API_HASH is missing")
    if not USER_ID:
        raise ValueError("USER_ID is missing")

    API_ID = int(API_ID)

    return  API_ID, API_HASH, USER_ID


def get_lowest_prices(DateOut, DateIn, Origin, Destination ):

    url = "https://www.ryanair.com/api/booking/v4/en-fi/availability?"    

    params = {
        "ADT": 1,
        "Origin": Origin,
        "Destination":  Destination,
        "DateIn": DateIn,
        "DateOut": DateOut,
        "OriginIsMac": "true",
        "RoundTrip": "true",
        "ToUs": "AGREED"
    }

    headers = {
        'client-version': '3.200.0',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36',
        'Cookie': 'fr-correlation-id=87e1794f-50f4-456d-b683-cb9043fe3234; rid=04232d75-841a-4074-8f36-63c8c3dac95d; xid=3de259d7-6f27-4287-9a1d-0c4bd17e5752; STORAGE_PREFERENCES={"STRICTLY_NECESSARY":true,"PERFORMANCE":true,"FUNCTIONAL":true,"TARGETING":true,"SOCIAL_MEDIA":true,"PIXEL":true,"__VERSION":5}; RY_COOKIE_CONSENT=true; _ga=GA1.1.1840741331.1780400087; mkt=/fi/en/; sid=62af766b-a0b4-411a-98c7-fb43dc4649b2; pid=72e54d4b-ec8a-4155-9608-243a74704842; _ga_YBBVD7Z3XL=GS2.1.s1780400087$o1$g1$t1780400394$j25$l0$h0; rid.sig=jyna6R42wntYgoTpqvxHMK7H+KyM6xLed+9I3KsvYZaVt7P36AL6zp9dGFPu5uVxaIiFpNXrszr+LfNCdY3IT3oCSYLeNv/ujtjsDqOzkY5JmUFsCdAEz3kpPbhCUwiArp5oaa75tpJtO3kFwYQ8l0DbH67AtcN/PMbniLsiM5qn+2AjrrtoNJicE3ZQwFHVipe4lWPSRfq2OIyUrlFhwEDt20+wCX7l1mCubNXtG6nZrUA07sFUFhn4RUxnjwjJ6d9qjjBasXLvYSqyYN7UaVMNyLndpWgNuGvtBrpXwIevPY1jhVsZ2eeP+z2FUiGtb5RVHJ3sZUuk+ZwdV69pY/p8EfPGRuWw2fe//JXwp95VYtpUt5tD3YhOKGYR9L9NZluKQz8vWgbAMnZ4lmUIIw6p4w9tYz3ea+Htq09FnrRy7k1wI6RyI3wkKh7OHf4y/fAhXU6Vv2F+aUwowblr2PG8LdTlM/2G/v+xiozozl0RaW28jRLPb/wXLd7T4TIWmPfTDomIv1oz2cM0GGezAliZao1sP6Q9CRBvvInb1xz0dryYCoexOF48YokGJBICFf04mRJNLnld11tJsvSNoVe7ajLqQCZ43pjY4D6SenqkJeIt2BYwwTGgJJxvfzYEnAnTG8MmQqaBdab5nrxxk2Ul3pud/fD8BfT/0XC/NNdCX4rTzEpg+9s5gQU9atgHEr3ZrNmFFNKf5NIx6HVBapKi1yLHax4ulEMEGKcOQcfBJTttUmop+t1Z2YG7nlv9WYi85PjRDG89Xn/QhuQstO2mydmMX4tp3uTrAx4sNk0XAIboiNceOPf9QVHc/I4bhctC1hlzy7VL39UbqoMuIh9ZuDzGJkaS+n1gfHKe8R4WJ3H/lJFzgiRIpcK9BKR/dyit8/qTwvIIZkhZoQFg0arzMem+jFLtNmJn+j28i/7RBuk8CQZT9ckAX8ic8OzF3G6B8zztZT4B7rjFyyuSGg=='
    }

    try:
        response = requests.get(url=url, params=params, headers=headers,timeout=(10,20), verify=False)
        response.raise_for_status()
        print(f"Актуальный статус код: {response.status_code}")
    except requests.exceptions.ConnectTimeout:
        print(f"Connect timeout count")
        return None
    except requests.exceptions.ReadTimeout:
        print(f"Read timeout count")
        return None
    except requests.exceptions.RequestException:
        print(f"Request expetions count")
        return None        
    
    data = response.json()    
    prices = {}
    for trip in data.get("trips", []):
        for date in trip.get("dates", []):
            if date.get("dateOut",[]) == DateOut:
                expected_response = date.get("flights", [])
                for flight in expected_response:
                    regularFare = flight.get("regularFare", {})
                    fares =regularFare.get("fares", [])
    
                    if fares:
                        time_list = flight.get("time", []) 
                        if time_list:
                            time = time_list[0]
                            amount = fares[0].get("amount")
                            #print(time[:16])
                            prices[time] = amount
    to_1 = list(prices.items())[-2:]

    for trip in data.get("trips", []):
        for date in trip.get("dates", []):
            if date.get("dateOut",[]) == DateIn:
                expected_response = date.get("flights", [])
                for flight in expected_response:
                    regularFare = flight.get("regularFare", {})
                    fares =regularFare.get("fares", [])
    
                    if fares:
                        time_list = flight.get("time", []) 
                        if time_list:
                            time = time_list[0]
                            amount = fares[0].get("amount")
                            #print(time[:16])
                            prices[time] = amount

    from_1 = list(prices.items())[-2:]
    return to_1, from_1   

async def _async_send(API_ID, API_HASH, USER_ID, text):
    async with TelegramClient('session_name', API_ID, API_HASH) as client:
        await client.send_message(USER_ID, text)

def send_telegram_notification(API_ID, API_HASH, USER_ID, text):
    try:
        asyncio.run(_async_send(API_ID, API_HASH, USER_ID, text))
        print("📱 Уведомление успешно отправлено в Telegram!")
    except Exception as e:
        print(f"❌ Ошибка при отправке в Telegram: {e}")

def main():

    API_ID, API_HASH, USER_ID = get_env_variables()

    to_1, from_1 = get_lowest_prices("2026-06-20T00:00:00.000", "2026-06-23T00:00:00.000", "ROM", "CTA")
    to_2, from_2 = get_lowest_prices("2026-06-21T00:00:00.000", "2026-06-24T00:00:00.000", "ROM", "CTA")

    to_1_message = "Билеты в Мессину:\n"

    for datetime_str, amount in to_1:
        time_only = datetime_str[11:16] 
        date_only = datetime_str[:10]
        to_1_message += f"📅 {date_only} | ⏰ {time_only} | 💰 {amount} EUR\n"

    from_1_message = "Билеты из Мессину:\n"

    for datetime_str, amount in from_1:
        time_only = datetime_str[11:16] 
        date_only = datetime_str[:10]
        from_1_message += f"📅 {date_only} | ⏰ {time_only} | 💰 {amount} EUR\n"

    for datetime_str, amount in to_2:
        time_only = datetime_str[11:16] 
        date_only = datetime_str[:10]
        to_1_message += f"📅 {date_only} | ⏰ {time_only} | 💰 {amount} EUR\n"

    for datetime_str, amount in from_2:
        time_only = datetime_str[11:16] 
        date_only = datetime_str[:10]
        from_1_message += f"📅 {date_only} | ⏰ {time_only} | 💰 {amount} EUR\n"

    text = to_1_message + "\n" + from_1_message
    print(text)

    send_telegram_notification(API_ID, API_HASH, USER_ID, text)
    

main()