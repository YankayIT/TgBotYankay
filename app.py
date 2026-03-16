from flask import Flask, request
import requests
import os

app = Flask(__name__)

TOKEN = os.environ.get("BOT_TOKEN")

def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    r = requests.post(url, json={
        "chat_id": chat_id,
        "text": text
    }, timeout=30)
    print("sendMessage:", r.status_code, r.text)

@app.route("/", methods=["GET"])
def home():
    return "Bot running"

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(silent=True)
    print("INCOMING UPDATE:", data)

    if not data:
        return "no data", 200

    if "message" in data:
        chat_id = data["message"]["chat"]["id"]
        text = data["message"].get("text", "")
        send_message(chat_id, f"Ты написал: {text}")

    return "ok", 200
