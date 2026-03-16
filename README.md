# Telegram bot for Render

## Files
- `app.py` — Flask webhook app
- `requirements.txt` — Python dependencies
- `render.yaml` — optional Blueprint deploy config for Render

## Local run
```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
export BOT_TOKEN=123456:ABC
export WEBHOOK_SECRET=mysecret
python app.py
```

## Render deploy
1. Push these files to GitHub.
2. In Render create a new **Web Service** from the repo.
3. Build command: `pip install -r requirements.txt`
4. Start command: `gunicorn app:app`
5. Add env vars:
   - `BOT_TOKEN` = your Telegram bot token
   - `WEBHOOK_SECRET` = any random secret path, for example `tg-hook-123`
   - `AI_MODE` = `faq` or `echo`
6. Deploy.

## Set Telegram webhook
After deploy, call:
```bash
curl "https://api.telegram.org/bot<BOT_TOKEN>/setWebhook?url=https://<your-service>.onrender.com/<WEBHOOK_SECRET>"
```

## Check webhook
```bash
curl "https://api.telegram.org/bot<BOT_TOKEN>/getWebhookInfo"
```
