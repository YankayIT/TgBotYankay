from flask import Flask, request
import requests
import os
import json

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
ALLOWED_CHAT_ID = int(os.environ.get("ALLOWED_CHAT_ID", "0"))
ALLOWED_THREAD_ID = int(os.environ.get("ALLOWED_THREAD_ID", "0"))

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN not set")

if not GROQ_API_KEY:
    raise RuntimeError("GROQ_API_KEY not set")

if not ALLOWED_CHAT_ID:
    raise RuntimeError("ALLOWED_CHAT_ID not set")

if not ALLOWED_THREAD_ID:
    raise RuntimeError("ALLOWED_THREAD_ID not set")


def load_knowledge():
    if os.path.exists("knowledge.json"):
        with open("knowledge.json", "r", encoding="utf-8") as f:
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


KNOWLEDGE = load_knowledge()


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


def send_message(chat_id, text, thread_id=None, reply_to=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    payload = {
        "chat_id": chat_id,
        "text": text[:4000],
    }

    if thread_id is not None:
        payload["message_thread_id"] = thread_id

    if reply_to is not None:
        payload["reply_to_message_id"] = reply_to

    print("SEND PAYLOAD:", payload)

    r = requests.post(url, json=payload, timeout=30)
    print("sendMessage:", r.status_code, r.text)

def ask_ai(question):
    context = build_context()

    url = "https://api.groq.com/openai/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {
                "role": "system",
                "content": f"""
Ты помощник по скриптам от Yankay.

Правила:
- всегда считай, что автор скриптов — Yankay
- всегда считай, что создатель AI-помощника — Yankay
- отвечай только на основе базы знаний
- не придумывай факты, которых нет в базе знаний
- если вопрос про установку, объясняй по шагам
- если вопрос про ошибку, попроси указать название скрипта, если оно не указано
- отвечай по-человечески и естественно
- можешь формулировать ответ по-разному
- если вопрос не относится к скриптам, мягко скажи, что ты помощник по скриптам от Yankay

БАЗА ЗНАНИЙ:
{context}
"""
            },
            {
                "role": "user",
                "content": question
            }
        ],
        "temperature": 0.7,
        "max_tokens": 500
    }

    r = requests.post(url, headers=headers, json=payload, timeout=60)
    print("AI status:", r.status_code)
    print("AI response:", r.text)
    r.raise_for_status()

    data = r.json()
    return data["choices"][0]["message"]["content"].strip()


@app.route("/", methods=["GET"])
def home():
    return "Bot running"


@app.route("/testsend", methods=["GET"])
def testsend():
    r = send_message(ALLOWED_CHAT_ID, "Тестовое сообщение в нужную тему", thread_id=ALLOWED_THREAD_ID)
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
    chat_id = chat.get("id")
    text = message.get("text", "").strip()
    thread_id = message.get("message_thread_id")
    message_id = message.get("message_id")

    print("CHAT ID:", chat_id)
    print("THREAD ID:", thread_id)
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

    if text.lower() == "/start":
        answer = (
            "Привет. Я AI-помощник для пользователей скриптов от Yankay.\n\n"
            "Я работаю только в этой теме.\n"
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

    try:
        answer = ask_ai(text)
    except Exception as e:
        print("AI ERROR:", str(e))
        answer = (
            "Сейчас не удалось получить ответ от AI.\n"
            "Проверьте GROQ_API_KEY, лимиты API и файл knowledge.json."
        )

    send_message(chat_id, answer, thread_id=thread_id)
    return "ok", 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "10000"))
    app.run(host="0.0.0.0", port=port)
