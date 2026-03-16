from flask import Flask, request
import requests
import os

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

with open("knowledge.txt", "r", encoding="utf-8") as f:
    KNOWLEDGE = f.read()

def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, json={
        "chat_id": chat_id,
        "text": text
    }, timeout=30)

def ask_ai(question):

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"

    prompt = f"""
Ты помощник по одному конкретному скрипту.

Отвечай только на основе информации ниже.
Если ответа нет — скажи что информации нет.

БАЗА ЗНАНИЙ:
{KNOWLEDGE}

Вопрос пользователя:
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
    r.raise_for_status()

    result = r.json()

    return result["candidates"][0]["content"]["parts"][0]["text"]

@app.route("/", methods=["GET"])
def home():
    return "Bot running"

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(silent=True)

    if not data:
        return "ok", 200

    if "message" in data:
        chat_id = data["message"]["chat"]["id"]
        text = data["message"].get("text", "")

        try:
            answer = ask_ai(text)
        except Exception as e:
            print("AI ERROR:", e)
            answer = "Ошибка AI"

        send_message(chat_id, answer)

    return "ok", 200
