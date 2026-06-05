from telethon import TelegramClient
import asyncio
from dotenv import load_dotenv
import os
import json
from telethon.sessions import StringSession

TARGET_CHAT = "@qa_vacancy_parcing"
STATE_FILE = "channel_state.json"

QA_KEYWORDS = [
    "qa",
    "test engineer",
    "tester",
    "testing",
    "тестировщик",
    "qa engineer",
    "manual qa",
    "automation qa",
    "aqa"
]

EXCLUDE_SENIOR = [
    "senior",
    "sr",
    "lead",
    "principal",
    "qa manager",
    "head of qa"
]

EXCLUDE_JAVA_AQA = [
    "aqa java",
    "automation java",
    "selenium java",
    "java test automation"
]

CHANNELS = [
    "@easy_qa_jobs",
    "@remote_jobs_relocate",
    "@zarubezhom_jobs",
    "@HRTech_Jobs",
    "@it_jobs_agregator",
    "@revacancy",
    "@jobsearchIT",
    "@it_vakansii_jobs",
    "@remotejun",
    "@qa_jobs_rabota",
    "@Remoteit",
    "@newdirections",
    "@refer_me_it",
    "@jun_qa",
    "@itvacancykz",
    "@jobfortm",
    "@aitujobs",
    "@datajobschannel",
    "@analitiki_rabota",
    "@data_analysis_jobs",
    "@jtbl_vacancy",

]

def get_env_variables():

    load_dotenv()

    API_ID = os.getenv("API_ID")
    API_HASH = os.getenv("API_HASH")
    STRING_SESSION = os.getenv("STRING_SESSION")

    if not API_ID:
        raise ValueError("API_ID is missing")
    if not API_HASH:
        raise ValueError("API_HASH is missing")
    if not STRING_SESSION:
        raise ValueError("STRING_SESSION is missing")    

    API_ID = int(API_ID)

    return  API_ID, API_HASH, STRING_SESSION

API_ID, API_HASH, STRING_SESSION = get_env_variables() # API_ID API_HASH можно получить через сайт тг 



def load_state():
    if not os.path.exists(STATE_FILE):
        return {}
    with open(STATE_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as file:
        json.dump(state, file, ensure_ascii=False, indent=2)

async def init_channel_if_needed(client, channel, state):
    if channel in state:
        return False

    latest_messages = await client.get_messages(channel, limit=1)

    if latest_messages:
        state[channel] = latest_messages[0].id
    else:
        state[channel] = 0

    return True
            
async def get_new_messages(client, channel, last_message_id):
    messages = []

    async for message in client.iter_messages(channel, min_id=last_message_id):
        messages.append(message)

    messages.reverse()  # чтобы были от старых к новым
    return messages

def is_relevant_vacancy(text):

    text = text.lower()

    if not any(k in text for k in QA_KEYWORDS):
        return False

    if any(k in text for k in EXCLUDE_SENIOR):
        return False

    if any(k in text for k in EXCLUDE_JAVA_AQA):
        return False

    return True


async def main():

    state = load_state()

    async with TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH) as client:
        for channel in CHANNELS:

            initialized = await init_channel_if_needed(client, channel, state)

            if initialized:
                await client.send_message(TARGET_CHAT, f"{channel}: первый запуск, старые сообщения пропущены")
                save_state(state)
                continue
            
            last_message_id = state.get(channel, 0)
            new_messages = await get_new_messages(client, channel, last_message_id)

            if not new_messages:
                print(f"{channel}: новых сообщений нет")
                #await client.send_message(TARGET_CHAT, f"{channel}: новых сообщений нет")
                continue

            print(f"{channel}: найдено {len(new_messages)} новых сообщений")

            max_id = last_message_id

            for message in new_messages:
                text = (message.message or "").lower()
                print(f"[{message.id}] {text}")

                if is_relevant_vacancy(text):
                    await client.forward_messages(TARGET_CHAT, message)

                if message.id > max_id:
                    max_id = message.id

            state[channel] = max_id
            save_state(state)
        
asyncio.run(main())
