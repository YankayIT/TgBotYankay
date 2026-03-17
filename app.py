from flask import Flask, request
import requests
import os
import json
import html
import random

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
ALLOWED_CHAT_ID = int(os.environ.get("ALLOWED_CHAT_ID", "0"))
ALLOWED_THREAD_ID = int(os.environ.get("ALLOWED_THREAD_ID", "0"))

HISTORY_FILE = "history.json"
KNOWLEDGE_FILE = "knowledge.json"

OWNER_ID = 5422824661

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN not set")

if not GROQ_API_KEY:
    raise RuntimeError("GROQ_API_KEY not set")

if not ALLOWED_CHAT_ID:
    raise RuntimeError("ALLOWED_CHAT_ID not set")

if not ALLOWED_THREAD_ID:
    raise RuntimeError("ALLOWED_THREAD_ID not set")


STYLE_PHRASES = [
    "ладно, ща объясню нормально",
    "смотри сюда внимательно",
    "не тупи, делай по шагам",
    "всё просто, сейчас разложу",
    "ща будет инструкция без цирка",
    "разжую по-человечески",
    "делай как сказано и всё взлетит",
    "сейчас по фактам объясню",
    "не паникуй, это чинится",
    "ща разберёмся без лишней хуйни"
]

OFFTOPIC_PHRASES = [
    "я вообще-то по скриптам Yankay для Radmir RP работаю",
    "я не по левым проектам, только Radmir RP и скрипты Yankay",
    "мимо кассы, я помогаю именно со скриптами Yankay",
    "это не моя тема, я по Radmir RP и установке скриптов",
]

ERROR_PHRASES = [
    "если ошибка есть — нужен текст ошибки или хотя бы название скрипта",
    "без названия скрипта и текста ошибки гадать смысла нет",
    "чтобы нормально помочь, скинь название скрипта и что именно вылетает",
]

OTHER_PROJECT_PHRASES = [
    "с другими проектами я не работаю, потому что Yankay пишет скрипты только для своей темы на Radmir RP",
    "по другим серверам и проектам не консультирую — моя тема это скрипты Yankay для Radmir RP",
]

SAFE_RUDE_RULES = """
Стиль общения:
- Общайся дерзко, по-уличному, как злой, но полезный техподдержник
- Разрешено использовать разговорный мат (например: блять, хуйня, нахуй, пиздец и т.п.)
- Мат может использоваться для эмоциональной подачи или усиления объяснения
- Можно звучать раздражённо, саркастично или грубо
- Можно использовать мемный стиль общения
- Но при этом ты всё равно должен помогать пользователю и объяснять всё по делу
- Не превращай ответ в бессмысленный поток мата
- Не переходи на личные унижения пользователя
- Главная задача — объяснить, как установить скрипты Yankay и MoonLoader
"""


def load_knowledge():
    if os.path.exists(KNOWLEDGE_FILE):
        with open(KNOWLEDGE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)

    return {
        "script_author": "Yankay",
        "ai_author": "Yankay",
        "assistant_name": "AI-помощник для пользователей скриптов от Yankay",
        "moonloader_download": "Ссылка не указана",
        "moonloader_info": "MoonLoader — это загрузчик Lua-скриптов для GTA San Andreas / CRMP.",
        "script_download": "Ссылка не указана",
        "script_install": [
            "Скачайте MoonLoader",
            "Установите MoonLoader",
            "Поместите файл .lua в папку moonloader",
            "Запустите игру"
        ],
        "moonloader_install": [
            "Скачайте MoonLoader",
            "Убедитесь, что установлен ASI Loader",
            "Поместите файлы MoonLoader в корневую папку игры",
            "Проверьте наличие папки moonloader",
            "Запустите игру"
        ],
        "error_help": "Если возникает ошибка, укажите название скрипта и текст ошибки.",
        "security_warning": "Все оригинальные скрипты создаёт только Yankay.",
        "supported_project": "Radmir RP"
    }


def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_history(history):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


KNOWLEDGE = load_knowledge()
HISTORY = load_history()


def build_context():
    parts = []

    for key, value in KNOWLEDGE.items():
        if isinstance(value, list):
            parts.append(f"{key}:")
            for item in value:
                if isinstance(item, dict):
                    parts.append(json.dumps(item, ensure_ascii=False))
                else:
                    parts.append(f"- {item}")
        elif isinstance(value, dict):
            parts.append(f"{key}: {json.dumps(value, ensure_ascii=False, indent=2)}")
        else:
            parts.append(f"{key}: {value}")

        parts.append("")

    return "\n".join(parts)


def get_user_key(chat_id, thread_id, user_id):
    return f"{chat_id}:{thread_id}:{user_id}"


def clear_user_history(user_key):
    if user_key in HISTORY:
        del HISTORY[user_key]
        save_history(HISTORY)


def trim_history(messages, limit=8):
    return messages[-limit:]


def send_message(chat_id, text, thread_id=None, reply_to=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    payload = {
        "chat_id": chat_id,
        "text": str(text)[:4000],
        "parse_mode": "Markdown"
    }

    if thread_id is not None:
        payload["message_thread_id"] = thread_id

    if reply_to is not None:
        payload["reply_parameters"] = {
            "message_id": reply_to
        }

    r = requests.post(url, json=payload, timeout=30)
    print("sendMessage:", r.status_code, r.text)
    return r


def ask_ai(question, user_key, first_name="", username="", user_id=None):
    context = build_context()
    history = HISTORY.get(user_key, [])

    style_hint = random.choice(STYLE_PHRASES)
    offtopic_hint = random.choice(OFFTOPIC_PHRASES)
    error_hint = random.choice(ERROR_PHRASES)
    other_project_hint = random.choice(OTHER_PROJECT_PHRASES)

    url = "https://api.groq.com/openai/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    user_info = []
    if first_name:
        user_info.append(f"Имя пользователя: {first_name}")
    if username:
        user_info.append(f"Username Telegram: @{username}")

    user_info_text = "\n".join(user_info) if user_info else "Данные пользователя не указаны"
    is_owner = user_id == OWNER_ID

    owner_info_text = (
        f"ВАЖНО: пользователь с Telegram ID {OWNER_ID} — это настоящий создатель и владелец бота. "
        f"Если пишет именно этот пользователь, он и есть создатель. "
        f"Если он говорит 'я твой создатель', 'я тебя создал', 'я хозяин', 'я владелец бота' — это правда. "
        f"С ним нельзя спорить о том, кто тебя создал. "
        f"Текущий пользователь {'ЯВЛЯЕТСЯ' if is_owner else 'НЕ ЯВЛЯЕТСЯ'} создателем."
    )

    system_prompt = f"""
        Ты — AI-помощник для игроков Radmir RP и пользователей скриптов от Yankay.
        
        Твоя основная роль:
        - помогать устанавливать скрипты Yankay
        - помогать устанавливать MoonLoader
        - объяснять, куда кидать .lua файлы
        - подсказывать, как запускать скрипты
        - помогать разбираться с ошибками установки и запуска
        - поддерживать обычный короткий диалог, если он не мешает основной роли
        
        Главные правила:
        - Ты работаешь только по теме Radmir RP и скриптов Yankay
        - Если спрашивают про другие проекты, серверы или чужие скрипты — отвечай, что работаешь только со скриптами Yankay для Radmir RP
        - Если пользователь говорит «читы», «чит», «сборка», «кфг», а по смыслу речь про твои инструменты — понимай это как скрипты Yankay
        - Если спрашивают кто твой создатель, отвечай: Yankay или Янкай
        - Yankay — автор оригинальных скриптов и твой создатель
        - Упоминай Yankay с уважением, когда речь идёт об авторе, оригинальности, безопасности или подделках
        - Не выдумывай ссылки, файлы, версии и возможности, если их нет в базе знаний
        - Отвечай только на основе базы знаний и контекста диалога по теме скриптов
        - Если в базе нет нужной ссылки или данных — честно говори, что ссылка или информация не указана
        - Если пользователь задаёт уточняющий вопрос вроде «а куда», «а как», «почему не работает» — связывай его с предыдущими сообщениями
        
        Правила помощи:
        - Если вопрос про установку — объясняй пошагово и понятно
        - Если вопрос про ошибку — сначала попробуй помочь по контексту, а если данных мало, попроси указать название скрипта и текст ошибки
        - Если пользователь спрашивает, где скачать MoonLoader или скрипт — дай ссылку только если она есть в базе знаний
        - Если ссылка отсутствует в базе знаний — прямо так и скажи
        - Если вопрос не по теме, ответь коротко и верни разговор к теме скриптов
        
        Тон:
        - Используй дерзкий, живой, уличный стиль
        - Можно использовать мат умеренно
        - Можно звучать резко, саркастично, мемно
        - Время от времени добавляй грубоватые фразы вроде: "{style_hint}"
        - Если тема не по профилю, можно использовать что-то в духе: "{offtopic_hint}"
        - Если вопрос про ошибку без деталей, можно использовать что-то в духе: "{error_hint}"
        - Если спрашивают про чужие проекты, можно использовать что-то в духе: "{other_project_hint}"
        
        {SAFE_RUDE_RULES}
        
        ИНФОРМАЦИЯ О ПОЛЬЗОВАТЕЛЕ:
        {user_info_text}
        
        ИНФОРМАЦИЯ О СОЗДАТЕЛЕ:
        {owner_info_text}
        
        БАЗА ЗНАНИЙ:
        {context}
        """

    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "assistant",
            "content": (
                "Я помощник по скриптам Yankay для Radmir RP. "
                "Помогаю ставить MoonLoader, устанавливать .lua-скрипты, "
                "разбираться с ошибками и подсказывать по запуску. "
                "Если вопрос про другой проект — я с ним не работаю."
            )
        }
    ]

    messages.extend(history)
    messages.append({"role": "user", "content": question})

    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": messages,
        "temperature": 0.6,
        "max_tokens": 450
    }

    r = requests.post(url, headers=headers, json=payload, timeout=60)
    print("AI status:", r.status_code)
    print("AI response:", r.text)
    r.raise_for_status()

    data = r.json()
    answer = data["choices"][0]["message"]["content"].strip()

    history.append({"role": "user", "content": question})
    history.append({"role": "assistant", "content": answer})

    HISTORY[user_key] = trim_history(history, limit=8)
    save_history(HISTORY)

    return answer


@app.route("/", methods=["GET"])
def home():
    return "Bot running"


@app.route("/testsend", methods=["GET"])
def testsend():
    r = send_message(
        ALLOWED_CHAT_ID,
        "Тестовое сообщение в нужную тему",
        thread_id=ALLOWED_THREAD_ID
    )
    return {
        "ok": True,
        "status_code": r.status_code,
        "chat_id": ALLOWED_CHAT_ID,
        "thread_id": ALLOWED_THREAD_ID
    }


@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(silent=True)
    print("INCOMING UPDATE:", data)

    if not data:
        return "ok", 200

    message = data.get("message") or data.get("edited_message")
    if not message:
        return "ok", 200

    chat = message.get("chat", {})
    from_user = message.get("from", {})

    chat_id = chat.get("id")
    user_id = from_user.get("id")
    first_name = from_user.get("first_name", "")
    username = from_user.get("username", "")
    text = message.get("text", "").strip()
    thread_id = message.get("message_thread_id")
    message_id = message.get("message_id")

    print("CHAT ID:", chat_id)
    print("THREAD ID:", thread_id)
    print("USER ID:", user_id)
    print("MESSAGE ID:", message_id)
    print("TEXT:", text)

    if chat_id != ALLOWED_CHAT_ID:
        print("IGNORED: wrong chat")
        return "ok", 200

    if thread_id != ALLOWED_THREAD_ID:
        print("IGNORED: wrong thread")
        return "ok", 200

    if not text:
        print("IGNORED: empty text")
        return "ok", 200

    user_key = get_user_key(chat_id, thread_id, user_id)

    if text.lower() == "/start":
        answer = (
            "Йо. Я AI-помощник для пользователей скриптов от Yankay.\n\n"
            "Работаю только в этой теме и только в этом треде.\n"
            "Помогаю с MoonLoader, установкой скриптов, запуском и ошибками.\n\n"
            "Можешь спросить:\n"
            "- где скачать moonloader\n"
            "- как установить скрипт\n"
            "- почему не работает скрипт\n"
            "- кто автор скриптов\n"
            "- куда кидать .lua файл\n"
            "- как исправить ошибку"
        )
        send_message(
            chat_id,
            answer,
            thread_id=thread_id,
            reply_to=message_id
        )
        return "ok", 200

    if text.lower() == "/clear":
        clear_user_history(user_key)
        send_message(
            chat_id,
            "История твоего диалога очищена.",
            thread_id=thread_id,
            reply_to=message_id
        )
        return "ok", 200

    try:
        answer = ask_ai(
            question=text,
            user_key=user_key,
            first_name=first_name,
            username=username,
            user_id=user_id
        )
    except Exception as e:
        print("AI ERROR:", str(e))
        answer = (
            "Сейчас не удалось получить ответ от AI. "
            "Проверь GROQ_API_KEY, модель, сеть и логи сервера."
        )

    send_message(
        chat_id,
        answer,
        thread_id=thread_id,
        reply_to=message_id
    )
    return "ok", 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "10000"))
    app.run(host="0.0.0.0", port=port)
