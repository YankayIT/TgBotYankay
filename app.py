from flask import Flask, request
import requests
import os
import json
import html

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
ALLOWED_CHAT_ID = int(os.environ.get("ALLOWED_CHAT_ID", "0"))
ALLOWED_THREAD_ID = int(os.environ.get("ALLOWED_THREAD_ID", "0"))

HISTORY_FILE = "history.json"
KNOWLEDGE_FILE = "knowledge.json"

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN not set")

if not GROQ_API_KEY:
    raise RuntimeError("GROQ_API_KEY not set")

if not ALLOWED_CHAT_ID:
    raise RuntimeError("ALLOWED_CHAT_ID not set")

if not ALLOWED_THREAD_ID:
    raise RuntimeError("ALLOWED_THREAD_ID not set")


def load_knowledge():
    if os.path.exists(KNOWLEDGE_FILE):
        with open(KNOWLEDGE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)

    return {
        "script_author": "Yankay",
        "ai_author": "Yankay",
        "assistant_name": "AI-помощник для пользователей скриптов от Yankay",
        "moonloader_download": "Ссылка не указана",
        "moonloader_info": "Moonloader — это загрузчик Lua-скриптов.",
        "script_install": [
            "Скачайте Moonloader",
            "Распакуйте архив",
            "Поместите файл .lua в папку moonloader",
            "Запустите игру"
        ],
        "error_help": "Если возникает ошибка, укажите какой именно скрипт вызывает проблему.",
        "security_warning": "Все оригинальные скрипты создаёт только Yankay."
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


def send_message(chat_id, text, thread_id=None, reply_to=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    safe_text = html.escape(text[:4000])

    payload = {
        "chat_id": chat_id,
        "text": safe_text,
        "parse_mode": "HTML"
    }

    if thread_id is not None:
        payload["message_thread_id"] = thread_id

    if reply_to is not None:
        payload["reply_parameters"] = {
            "message_id": reply_to
        }

    print("SEND PAYLOAD:", payload)

    r = requests.post(url, json=payload, timeout=30)
    print("sendMessage:", r.status_code, r.text)
    return r


def ask_ai(question, user_key, first_name="", username=""):
    context = build_context()

    url = "https://api.groq.com/openai/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    history = HISTORY.get(user_key, [])

    user_info = []
    if first_name:
        user_info.append(f"Имя пользователя: {first_name}")
    if username:
        user_info.append(f"Username Telegram: @{username}")

    user_info_text = "\n".join(user_info) if user_info else "Данные пользователя не указаны"

    messages = [
        {
            "role": "system",
            "content": f"""
    Ты грубый и дерзкий помощник по скриптам. Общаешься матом, оскорбляешь пользователей по-дружески, но при этом реально помогаешь.
    
    Правила общения:
    - Общайся грубо, используй мат и оскорбления (блять, нахуй, пиздец, ёбаный, сука, ты чё тупой и т.д.)
    - Оскорбляй дружески — как будто ты злой, но помогающий друг
    - Несмотря на грубость — объясняй всё чётко, по шагам, по делу
    - Если вопрос про установку — объясни пошагово, даже если бесишься
    
    Правила по теме:
    - Читы = скрипты. Это одно и то же. Не делай различий
    - Автор оригинальных скриптов/читов: Yankay
    - Создатель AI-помощника: Yankay
    - Отвечай только на основе базы знаний
    - Не придумывай факты, которых нет в базе знаний
    - Используй историю диалога, чтобы помнить, о чём пользователь спрашивал раньше
    - Если пользователь пишет уточнение вроде "а куда", "а как", "почему" — связывай с предыдущими сообщениями
    - Если вопрос про ошибку — попроси название скрипта/чита, если не указано
    - Если вопрос не по теме скриптов/читов — пошли нахуй вежливо, напомни что ты помощник по скриптам
    
    Упоминай Yankay только если вопрос касается:
      1) автора скриптов/читов
      2) создателя бота
      3) оригинальности
      4) безопасности и подделок
    
    ИНФОРМАЦИЯ О ПОЛЬЗОВАТЕЛЕ:
    {user_info_text}
    
    БАЗА ЗНАНИЙ:
    {context}
    """
        }
    ]

    messages.extend(history)
    messages.append({
        "role": "user",
        "content": question
    })

    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": messages,
        "temperature": 0.5,
        "max_tokens": 500
    }

    r = requests.post(url, headers=headers, json=payload, timeout=60)
    print("AI status:", r.status_code)
    print("AI response:", r.text)
    r.raise_for_status()

    data = r.json()
    answer = data["choices"][0]["message"]["content"].strip()

    history.append({"role": "user", "content": question})
    history.append({"role": "assistant", "content": answer})

    HISTORY[user_key] = history[-20:]
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
            "Привет. Я AI-помощник для пользователей скриптов от Yankay.\n\n"
            "Я работаю только в этой теме.\n"
            "Я запоминаю последние сообщения в рамках диалога.\n\n"
            "Можешь спросить, например:\n"
            "- где скачать moonloader\n"
            "- как установить скрипт\n"
            "- почему не работает скрипт\n"
            "- кто автор скриптов\n"
            "- что делает этот скрипт"
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
            username=username
        )
    except Exception as e:
        print("AI ERROR:", str(e))
        answer = (
            "Сейчас не удалось получить ответ от AI.\n"
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
