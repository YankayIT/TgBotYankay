from flask import Flask, request
import requests
import os

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN not set")

if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY not set")

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
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"

    prompt = f"""
Ты помощник по одному конкретному скрипту.

Отвечай только на основе базы знаний ниже.
Если точного ответа нет, так и скажи.
Объясняй простым языком, пошагово, если вопрос про установку или запуск.

БАЗА ЗНАНИЙ:
{KNOWLEDGE}

ВОПРОС ПОЛЬЗОВАТЕЛЯ:
{question}
"""

    data = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ]
    }

    r = requests.post(url, json=data, timeout=60)
    print("AI status:", r.status_code)
    print("AI response:", r.text)
    r.raise_for_status()

    result = r.json()
    return result["candidates"][0]["content"]["parts"][0]["text"]

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
