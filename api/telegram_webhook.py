# api/telegram_webhook.py
import json
import os
import asyncio
import base64
from telegram import Bot
from openai import OpenAI

# -------------------------------------------------
# Конфигурация (переменные окружения)
# -------------------------------------------------
BOT_TOKEN      = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ASSISTANT_ID   = os.getenv("OPENAI_ASSISTANT_ID")

if not BOT_TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN не задан")
if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY не задан")
if not ASSISTANT_ID:
    raise RuntimeError("OPENAI_ASSISTANT_ID не задан")

client = OpenAI(api_key=OPENAI_API_KEY)

# -------------------------------------------------
# Асинхронная обработка одного сообщения
# -------------------------------------------------
async def process_message(chat_id: int, text: str, message_id: int):
    bot = Bot(token=BOT_TOKEN)
    try:
        await bot.send_chat_action(chat_id=chat_id, action="typing")

        # ---- OpenAI Assistant ----
        thread = await asyncio.to_thread(
            client.beta.threads.create,
            messages=[{"role": "user", "content": text}]
        )
        run = await asyncio.to_thread(
            client.beta.threads.runs.create,
            thread_id=thread.id,
            assistant_id=ASSISTANT_ID,
        )

        # Простой polling (Vercel позволяет до ~10 сек)
        import time
        for _ in range(30):                     # max ~9 сек
            status = await asyncio.to_thread(
                client.beta.threads.runs.retrieve,
                thread_id=thread.id,
                run_id=run.id,
            )
            if status.status in {"completed", "failed", "cancelled"}:
                break
            time.sleep(0.3)

        if status.status != "completed":
            response = "Извини, не успел получить ответ."
        else:
            msgs = await asyncio.to_thread(
                client.beta.threads.messages.list,
                thread_id=thread.id,
            )
            response = msgs.data[0].content[0].text.value

        await bot.send_message(
            chat_id=chat_id,
            text=response,
            reply_to_message_id=message_id,
        )
        return {"status": "ok"}

    except Exception as exc:
        err = f"Ошибка: {exc}"
        print(err)
        await bot.send_message(
            chat_id=chat_id,
            text=err,
            reply_to_message_id=message_id,
        )
        return {"status": "error", "message": str(exc)}

# -------------------------------------------------
# Vercel‑handler (единственная точка входа)
# -------------------------------------------------
def telegram_webhook(event, context=None):
    try:
        body = event.get("body") or ""
        if not body:
            return {"statusCode": 400, "body": json.dumps({"error": "empty body"})}

        # Vercel иногда присылает base64
        if event.get("isBase64Encoded", False):
            body = base64.b64decode(body).decode("utf-8")

        update = json.loads(body)

        # ------------------- только текстовые сообщения -------------------
        msg = update.get("message", {})
        if not msg.get("text"):
            return {"statusCode": 200, "body": json.dumps({"status": "ignored"})}

        chat_id    = msg["chat"]["id"]
        text       = msg["text"]
        message_id = msg["message_id"]

        # ------------------- запуск async -------------------
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(
            process_message(chat_id, text, message_id)
        )
        loop.close()

        return {"statusCode": 200, "body": json.dumps(result)}

    except json.JSONDecodeError as e:
        return {"statusCode": 400, "body": json.dumps({"error": f"bad json: {e}"})}
    except Exception as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}

# -------------------------------------------------
# ОБЯЗАТЕЛЬНО: Vercel ищет переменную `handler`
# -------------------------------------------------
handler = telegram_webhook
