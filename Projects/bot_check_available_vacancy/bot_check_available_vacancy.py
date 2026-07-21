from telethon import TelegramClient
from telethon.sessions import StringSession
from dotenv import load_dotenv

import asyncio
import os
import json

TARGET_CHAT_QA = "@qa_vacancy_parcing"
TARGET_CHAT_DATA = "@data_vacancy_parcing"
STATE_FILE = "channel_state.json"

QA_KEYWORDS = [
    "qa",
    "qa engineer",
    "manual qa",
    "automation qa",
    "aqa",
    "test engineer",
    "software tester",
    "tester",
    "testing",
    "тестировщик",
    "инженер по тестированию",
]

QA_EXCLUDE = [

    "senior qa",
    "sr qa",
    "lead qa",
    "qa lead",
    "principal qa",
    "qa manager",
    "head of qa",

    "только рф",
    "москва",
    "рф",
    "рб",
    "минск",
    "russia",

    "backend engineer",
    "backend developer",
    "frontend developer",
    "fullstack developer",
    ".net developer",
    "python developer",
    "java developer",
    "business analyst",
    "ai product analyst",
    "ai integrator",

    "aqa java",
    "automation java",
    "selenium java",
    "java test automation",

    "1c",
    "casino",
]

DATA_KEYWORDS = [

    "data analyst",
    "data analytics",
    "data analysis",
    "аналитик данных",
    "дата аналитик",

    "product analyst",
    "product analytics",

    "bi analyst",
    "business intelligence analyst",

    "sql analyst",

    "#dataanalyst",
    "#data_analyst",
    "#dataanalytics",

    "data scientist",
    "data science",
    "data scientist intern",
    "data science intern",
    "датасаентист",
    "дата саентист",

    "#datascience",
    "#data_science",

    "machine learning",
    "machine learning engineer",
    "ml engineer",
    "mlops",
    "machine learning intern",

    "#machinelearning",
    "#machine_learning",
    "#ml",
    "#mlops",

    "ai engineer",
    "ai/ml engineer",
    "ai ml engineer",

    "#ai_ml",
    "#aiml",

    "devops",
    "devops engineer",
    "site reliability engineer",
    "sre",

    "#devops",
    "#sre",
]

DATA_EXCLUDE = [
    
    "senior",
    "sr",
    "lead",
    "principal",
    "staff",
    "head",
    "manager",

    "только рф",
    "москва",
    "рф",
    "рб",
    "минск",
    "russia",

    "backend engineer",
    "frontend developer",
    "frontend engineer",
    "fullstack developer",
    "java developer",
    "python developer",
    ".net developer",
    "golang developer",
    "php developer",

    "casino"
]

CHANNELS = [
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
    "@itvacancykz",
    "@jobfortm",
    "@aitujobs",
    "@datajobschannel",
    "@analitiki_rabota",
    "@data_analysis_jobs",
    "@jtbl_vacancy",
    "@itcom_kz",
    "@runello_rus_datascience",
    "@foranalysts",
    "@JobOfferInside",
    "@nodatanojobs",
    "@remote_kazakhstan",
    "@data_hr",
    "@vacancy_cs",
    "@qajobsoffers",
    "@pythonrabota"
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

def is_relevant_vacancy_qa(text):

    text = text.lower()

    if not any(k in text for k in QA_KEYWORDS):
        return False

    if any(k in text for k in QA_EXCLUDE):
        return False

    return True

def is_relevant_vacancy_data(text):

    text = text.lower()

    if not any(k in text for k in DATA_KEYWORDS):
        return False

    if any(k in text for k in DATA_EXCLUDE):
        return False

    return True


async def main():

    state = load_state()

    async with TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH) as client:
        for channel in CHANNELS:

            initialized = await init_channel_if_needed(client, channel, state)

            if initialized:
                #await client.send_message(TARGET_CHAT_QA, f"{channel}: первый запуск, старые сообщения пропущены")
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

                if is_relevant_vacancy_qa(text):
                    await client.forward_messages(TARGET_CHAT_QA, message)

                if is_relevant_vacancy_data(text):
                    await client.forward_messages(TARGET_CHAT_DATA, message)

                if message.id > max_id:
                    max_id = message.id

            state[channel] = max_id
            save_state(state)
        
asyncio.run(main())
