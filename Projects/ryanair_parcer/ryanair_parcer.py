import requests
from telethon import TelegramClient
from dotenv import load_dotenv
import json
import os 
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
import asyncio
from telethon.sessions import StringSession

def get_env_variables():

    load_dotenv()

    API_ID = os.getenv("API_ID")
    API_HASH = os.getenv("API_HASH")
    USER_ID = os.getenv("USER_ID")
    RYANAIR_COOKIE = os.getenv("RYANAIR_COOKIE")
    STRING_SESSION = os.getenv("STRING_SESSION")

    if not API_ID:
        raise ValueError("API_ID is missing")
    if not API_HASH:
        raise ValueError("API_HASH is missing")
    if not USER_ID:
        raise ValueError("USER_ID is missing")
    if not RYANAIR_COOKIE:
        raise ValueError("RYANAIR_COOKIE is missing")
    if not STRING_SESSION:
        raise ValueError("STRING_SESSION is missing")
    
    

    API_ID = int(API_ID)

    return  API_ID, API_HASH, USER_ID, RYANAIR_COOKIE, STRING_SESSION


def get_lowest_prices(DateOut, DateIn, Origin, Destination, RYANAIR_COOKIE):

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
        'Cookie': RYANAIR_COOKIE
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

async def _async_send(API_ID, API_HASH, USER_ID, STRING_SESSION, text):
    async with TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH) as client:
        await client.send_message(USER_ID, text)

def send_telegram_notification(API_ID, API_HASH, USER_ID, STRING_SESSION, text):
    try:
        asyncio.run(_async_send(API_ID, API_HASH, USER_ID, STRING_SESSION, text))
        print("📱 Уведомление успешно отправлено в Telegram!")
    except Exception as e:
        print(f"❌ Ошибка при отправке в Telegram: {e}")

def main():

    API_ID, API_HASH, USER_ID, RYANAIR_COOKIE, STRING_SESSION = get_env_variables()

    to_1, from_1 = get_lowest_prices("2026-06-20T00:00:00.000", "2026-06-23T00:00:00.000", "ROM", "CTA", RYANAIR_COOKIE)
    to_2, from_2 = get_lowest_prices("2026-06-21T00:00:00.000", "2026-06-24T00:00:00.000", "ROM", "CTA", RYANAIR_COOKIE)

    to_1_message = "✈️ Рим → Катания\n"

    for datetime_str, amount in to_1:
        time_only = datetime_str[11:16] 
        date_only = datetime_str[5:10]
        to_1_message += f"{date_only} {time_only} - {amount}€.\n"

    from_1_message = "✈️ Катания → Рим\n"

    for datetime_str, amount in from_1:
        time_only = datetime_str[11:16] 
        date_only = datetime_str[5:10]
        from_1_message += f"{date_only} {time_only} - {amount}€.\n"

    for datetime_str, amount in to_2:
        time_only = datetime_str[11:16] 
        date_only = datetime_str[5:10]
        to_1_message += f"{date_only} {time_only} - {amount}€.\n"

    for datetime_str, amount in from_2:
        time_only = datetime_str[11:16] 
        date_only = datetime_str[5:10]
        from_1_message += f"{date_only} {time_only} - {amount}€.\n"

    text = to_1_message + "\n" + from_1_message
    print(text)

    send_telegram_notification(API_ID, API_HASH, USER_ID, STRING_SESSION, text)
    

main()