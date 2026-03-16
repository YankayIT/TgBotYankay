import logging
import os
from flask import Flask, request, jsonify
import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv('BOT_TOKEN', '').strip()
WEBHOOK_SECRET = os.getenv('WEBHOOK_SECRET', '').strip()
AI_MODE = os.getenv('AI_MODE', 'echo').strip().lower()  # echo | faq

if not BOT_TOKEN:
    raise RuntimeError('BOT_TOKEN environment variable is required')

app = Flask(__name__)
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

FAQ = {
    'цена': 'Пока здесь стоит тестовый ответ. Замени его на свою цену.',
    'доставка': 'Доставка занимает 1–3 дня. Замени текст на свой.',
    'возврат': 'Для возврата напишите номер заказа и причину. Замени под свой процесс.'
}


def send_message(chat_id: int, text: str) -> None:
    response = requests.post(
        f"{TELEGRAM_API}/sendMessage",
        json={
            'chat_id': chat_id,
            'text': text,
        },
        timeout=30,
    )
    response.raise_for_status()



def build_reply(user_text: str) -> str:
    text = user_text.lower().strip()

    if AI_MODE == 'faq':
        for key, answer in FAQ.items():
            if key in text:
                return answer
        return 'Не нашёл готового ответа в FAQ. Добавь правила в словарь FAQ в app.py.'

    return f'Ты написал: {user_text}'


@app.get('/')
def healthcheck():
    return jsonify({'ok': True, 'service': 'telegram-render-bot'})


@app.post(f'/{WEBHOOK_SECRET}')
def telegram_webhook():
    update = request.get_json(silent=True) or {}
    message = update.get('message') or update.get('edited_message')

    if not message:
        return 'ok', 200

    chat = message.get('chat') or {}
    chat_id = chat.get('id')
    text = message.get('text', '')

    if not chat_id:
        return 'ok', 200

    try:
        reply = build_reply(text)
        send_message(chat_id, reply)
    except Exception:
        logger.exception('Failed to process update')

    return 'ok', 200


if __name__ == '__main__':
    port = int(os.getenv('PORT', '10000'))
    app.run(host='0.0.0.0', port=port)
