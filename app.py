from flask import Flask, request
import requests
import os

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

if not GROQ_API_KEY:
    raise RuntimeError("GROQ_API_KEY not set")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN not set")

with open("knowledge.txt", "r", encoding="utf-8") as f:
    KNOWLEDGE = f.read()

def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    r = requests.post(url, json={
        "chat_id": chat_id,
        "text": text[:4000]
    }, timeout=30)
    print("sendMessage:", r.status_code, r.text)

def ask_ai(question):
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
                "content": (
                    "Ты помощник по одному конкретному скрипту. "
                    "Отвечай только на основе базы знаний. "
                    "Если точного ответа нет, так и скажи. "
                    "Если вопрос про установку или запуск — объясняй просто и по шагам.\n\n"
                    f"БАЗА ЗНАНИЙ:\n{KNOWLEDGE}"
                )
            },
            {
                "role": "user",
                "content": question
            }
        ],
        "temperature": 0.2
    }

    r = requests.post(url, headers=headers, json=payload, timeout=60)
    print("AI status:", r.status_code)
    print("AI response:", r.text)
    r.raise_for_status()

    data = r.json()
    return data["choices"][0]["message"]["content"]

@app.route("/", methods=["GET"])
def home():
    return "Bot running"

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(silent=True)
    print("INCOMING UPDATE:", data)

    if not data:
        return "ok", 200

    if "message" in data:
        chat_id = data["message"]["chat"]["id"]
        text = data["message"].get("text", "").strip()

        if text == "/start":
            answer = (
                "Привет. Я AI-помощник по скрипту.\n\n"
                "Можешь спросить, например:\n"
                "- как установить скрипт\n"
                "- как запустить\n"
                "- что он делает\n"
                "- какие функции есть\n"
                "- почему появляется ошибка"
            )
        else:
            try:
                answer = ask_ai(text)
            except Exception as e:
                print("AI ERROR:", str(e))
                answer = "Не удалось получить ответ от AI. Проверь GEMINI_API_KEY и knowledge.txt."

        send_message(chat_id, answer)

    return "ok", 200
