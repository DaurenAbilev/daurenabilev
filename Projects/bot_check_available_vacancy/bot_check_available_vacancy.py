from telethon import TelegramClient
from telethon.sessions import StringSession
from dotenv import load_dotenv
from telethon.errors import ChatForwardsRestrictedError, RPCError

import asyncio
import os
import json
import re

TARGET_CHAT_QA = "@qa_vacancy_parcing"
TARGET_CHAT_DATA = "@data_vacancy_parcing"
STATE_FILE = "channel_state.json"

# QA-слова ищутся с границами слов в "шапке" поста (см. get_header)
QA_KEYWORDS = [
    "qa",
    "qa engineer",
    "manual qa",
    "automation qa",
    "qa automation",
    "aqa",
    "qaa",
    "sdet",
    "test engineer",
    "test automation",
    "test analyst",
    "quality assurance",
    "qc engineer",
    "software tester",
    "tester",
    "testing",
    "тестировщик",
    "автотестировщик",
    "ручной тестировщик",
    "ручное тестирование",
    "инженер по тестированию",
    "инженер ручного тестирования",
]

# однозначные фразы, которые достаточно найти и в теле поста
QA_STRONG_KEYWORDS = [
    "qa engineer",
    "manual qa",
    "automation qa",
    "qa automation",
    "test automation",
    "quality assurance",
    "software tester",
    "test engineer",
    "sdet",
    "aqa",
    "qaa",
    "тестировщик",
    "автотестировщик",
    "инженер по тестированию",
]

# блокируются при совпадении в любом месте текста
QA_EXCLUDE = [

    "senior qa",
    "sr qa",
    "lead qa",
    "qa lead",
    "principal qa",
    "qa manager",
    "head of qa",

    # гражданство / нахождение в РФ, РБ (сами компании из РФ/РБ допустимы)
    "только рф",
    "только рб",
    "только для граждан рф",
    "гражданство рф",
    "гражданство рб",
    "гражданин рф",
    "гражданин рб",
    "гражданство россии",
    "гражданство республики беларусь",
    "резидент рф",
    "резидент рб",
    "проживание в рф",
    "проживание в рб",
    "нахождение в рф",
    "находиться в рф",
    "находящихся в рф",
    "жительство в рф",
    "russian citizenship",
    "russian citizens only",
    "тк рф",
    "самозанятый рф",
    "🇺🇦",

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
    "1с",
    "casino",

    "fullstack technical lead",
    "senior quality assurance engineer",
    "middle crm analyst",
    "customer success specialist",
    "performance engineer",
    "senior lead php",
    "principal full stack engineer",
    "lead ux designer",
    "senior software engineer",
    "senior ai engineer",
    "ai engineer",
    "bi analyst",
    "senior ux/ui designer",
    "ux/ui designer",
    "ai process forward deployed engineer",
    "mobile developer",
    "senior flutter developer",
    "mobile engineer",

    # сферы: gambling / игры (mobile QA для приложений остаётся)
    "gambling",
    "igaming",
    "i-gaming",
    "betting",
    "беттинг",
    "букмекер",
    "гемблинг",
    "казино",
    "gaming",
    "game qa",
    "game tester",
    "game testing",
    "gamedev",
    "game dev",
    "unity",
    "unreal",
    "cocos",
    "игровой тестировщик",
    "тестировщик игр",

    # стеки / направления, которые не подходят
    "java",
    "kotlin",
    "c#",
    ".net",
    "dotnet",
    "php",
    "sap",
    "security",
    "pentest",
    "penetration testing",
    "cybersecurity",
    "performance testing",
    "performance test",
    "load testing",
    "jmeter",
    "нагрузочное тестирование",
    "нагрузочный тестировщик",
    "embedded",
    "firmware",
]

# блокируются только в шапке
QA_EXCLUDE_LEVEL = [
    # пропускаются, если в шапке есть junior/middle (например "Middle/Senior")
    "senior",
    "sr",
    "sr.",
    "lead",
    "team lead",
    "principal",
    "staff",
    "head",
    "head of",
    "manager",
    "ведущий",
    "старший",
    "тимлид",
    "руководитель",
]

QA_EXCLUDE_ROLE = [
    # не-QA роли; пропускаются, если в шапке есть QA-слово ("QA Full Stack")
    "frontend engineer",
    "full stack developer",
    "full-stack developer",
    "full-stack engineer",
    "full stack engineer",
    "golang developer",
    "go developer",
    "php developer",
    "ios developer",
    "android developer",
    "react native",
    "devops engineer",
    "sre",
    "site reliability engineer",
    "product manager",
    "project manager",
    "product designer",
    "designer",
    "marketer",
    "smm",
    "recruiter",
    "system analyst",
    "data scientist",
    "data engineer",
    "data analyst",
    "ml engineer",
    "software engineer",
    "#marketing",
    "#hr",
    "#sales",
    "#finance",
    "#account",
    "#management",
    "#design",
    "#development",
    "#devops",
    "#product",
    "#pr",
]

# резюме, реклама, подборки-дайджесты; блокируются только в шапке
QA_EXCLUDE_ADS = [
    "#resume",
    "#cv",
    "#резюме",
    "#ищуработу",
    "#opentowork",
    "ищу работу",
    "открыт к новым предложениям",
    "в поиске работы",
    "подборка",
    "дайджест вакансий",
    "post a job",
    "vseti.app",
    "сайт для всех, кто ищет работу",
    "чат с вашими резюме",
    "полезные телеграм-каналы",
    "если вы тестировщик или хотите",
    "оффера за 10 минут",
    "бесплатный онлайн-курс",
    "самый большой канал",
    "почему одних qa",
    "1000+ свежих",
    "6 часов, чтобы попробовать",
    "match с вакансией",
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

    "casino",

    "forward deployed infrastructure engineer",
    "google workspace / gcp migration engineer",
    "инвестиционный аналитики",
    "middle product analyst",
    "artificial intelligence specialist",
    "ai / genai engineer (llm & rag)",
    "ai solution consultant",
    "clinical ai specialist",
    "🇺🇦"


]

CHANNELS = [
    "@remote_jobs_relocate",
    "@zarubezhom_jobs",
    "@HRTech_Jobs",
    "@it_jobs_agregator",
    "@revacancy",
    "@jobsearchIT",
    "@it_vakansii_jobs",
    #"@remotejun",                  ### из чата нельзя пересылать сообщения
    "@qa_jobs_rabota",
    #"@Remoteit",                   ### из чата нельзя пересылать сообщения
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
    "@pythonrabota",
    "@Relocated_job", 
    "qajoboffer", 
    "qajobsru", 
    "rabotadlaqa"
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

HEADER_LENGTH = 300
LEVEL_JUNIOR_MIDDLE = ["junior", "jun", "middle", "intern", "стажер", "стажёр", "стажировка"]

OFFICE_PATTERN = re.compile(r"офис|office", re.IGNORECASE)
REMOTE_PATTERN = re.compile(
    r"удаленк|удалённ|удаленн|remote|гибрид|hybrid|релокац|relocation", re.IGNORECASE
)
HOME_REGION_PATTERN = re.compile(
    r"kzt|тенге|kazakhstan|almaty|astana|алматы|астана|казахстан"
    r"|uzbekistan|ташкент|tashkent|узбекистан",
    re.IGNORECASE,
)
ABROAD_PATTERN = re.compile(
    r"belarus|беларусь|минск|minsk|russia|росси|москв|moscow|санкт-петербург|petersburg"
    r"|ukraine|украин|poland|warsaw|romania|india|japan|germany|berlin|cyprus|georgia"
    r"|tbilisi|armenia|yerevan|turkey|dubai|uae|serbia|bulgaria|portugal|spain|usa"
    r"|london|netherlands",
    re.IGNORECASE,
)


def find_words(words, text):
    """Слова из words, найденные в text как отдельные слова (не подстроки)."""
    return [w for w in words if re.search(r"(?<!\w)" + re.escape(w) + r"(?!\w)", text)]


def get_header(text):
    """Шапка поста: первые HEADER_LENGTH символов + строки с хештегами."""
    lines = text.split("\n")
    tag_lines = [l for l in lines if l.count("#") >= 2 or l.startswith("tags:")]
    return text[:HEADER_LENGTH] + "\n" + "\n".join(tag_lines)


def is_office_abroad(text):
    """Офис вне Казахстана/Узбекистана без удалёнки, гибрида и релокации."""
    top = text[:600]
    return bool(
        OFFICE_PATTERN.search(top)
        and not REMOTE_PATTERN.search(top)
        and not HOME_REGION_PATTERN.search(top)
        and ABROAD_PATTERN.search(top)
    )


def is_relevant_vacancy_qa(text):

    text = text.lower()
    header = get_header(text)

    if not (find_words(QA_KEYWORDS, header) or find_words(QA_STRONG_KEYWORDS, text)):
        return False

    if find_words(QA_EXCLUDE, text):
        return False

    if find_words(QA_EXCLUDE_ADS, header):
        return False

    # Middle/Senior и Junior/Middle остаются
    if not find_words(LEVEL_JUNIOR_MIDDLE, header) and find_words(QA_EXCLUDE_LEVEL, header):
        return False

    # не-QA роль в шапке, при этом QA-слова в шапке нет
    if not find_words(QA_KEYWORDS, header) and find_words(QA_EXCLUDE_ROLE, header):
        return False

    # рубрика "📍 Маркетинг" и т.п. допустима только "📍 QA"
    if "📍" in header and not re.search(r"📍\s*(qa|тест)", header):
        return False

    if is_office_abroad(text):
        return False

    return True

def is_relevant_vacancy_data(text):

    text = text.lower()
    header = get_header(text)

    if not find_words(DATA_KEYWORDS, text):
        return False

    # senior/lead/manager и т.п. смотрим только в шапке, остальное во всём тексте
    level_words = [k for k in DATA_EXCLUDE if k in QA_EXCLUDE_LEVEL]
    other_words = [k for k in DATA_EXCLUDE if k not in QA_EXCLUDE_LEVEL]

    if not find_words(LEVEL_JUNIOR_MIDDLE, header) and find_words(level_words, header):
        return False

    if find_words(other_words, text):
        return False

    return True


async def process_channel(client, channel, state):

    initialized = await init_channel_if_needed(client, channel, state)

    if initialized:
        #await client.send_message(TARGET_CHAT_QA, f"{channel}: первый запуск, старые сообщения пропущены")
        save_state(state)
        return

    last_message_id = state.get(channel, 0)
    new_messages = await get_new_messages(client, channel, last_message_id)

    if not new_messages:
        print(f"{channel}: новых сообщений нет")
        #await client.send_message(TARGET_CHAT, f"{channel}: новых сообщений нет")
        return

    print(f"{channel}: найдено {len(new_messages)} новых сообщений")

    max_id = last_message_id

    for message in new_messages:
        text = (message.message or "").lower()
        print(f"[{message.id}] {text}")

        if is_relevant_vacancy_qa(text):
            try: 
                await client.forward_messages(TARGET_CHAT_QA, message)
            except ChatForwardsRestrictedError: 
                await client.send_message(
                    TARGET_CHAT_QA, 
                    f"⚠️ Не удалось переслать сообщение.\n"
                    f"ID сообщения: {message.id}\n"
                    f"Источник: {channel}"
                )
                print(f"Нельзя отправить исходное сообщение {message.id}")
                print(f"{message}")

        if is_relevant_vacancy_data(text):
            try: 
                await client.forward_messages(TARGET_CHAT_DATA, message)
            except ChatForwardsRestrictedError:
                await client.send_message(
                    TARGET_CHAT_DATA, 
                    f"⚠️ Не удалось переслать сообщение.\n"
                    f"ID сообщения: {message.id}\n"
                    f"Источник: {channel}"
                )
                print(f"Нельзя отправить исходное сообщение {message.id}")
                print(f"{message}")

        if message.id > max_id:
            max_id = message.id

    state[channel] = max_id
    save_state(state)


async def main():

    state = load_state()
    failed_channels = []

    async with TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH) as client:
        for channel in CHANNELS:
            try:
                await process_channel(client, channel, state)
            except (RPCError, ValueError, ConnectionError, asyncio.TimeoutError) as error:
                # сбой Telegram (RpcCallFailError, "Request was unsuccessful N time(s)" и т.п.):
                # пропускаем канал, state для него не обновился - сообщения подхватятся в след. прогоне
                failed_channels.append(channel)
                print(f"{channel}: ошибка {type(error).__name__}: {error}, канал пропущен")

    if failed_channels:
        print(f"Каналов пропущено из-за ошибок: {len(failed_channels)}: {', '.join(failed_channels)}")

asyncio.run(main())
