import json
import os
import asyncio
from telegram import Bot
from openai import OpenAI
from flask import Flask, request, jsonify

# Создаем экземпляр Flask-приложения
# Vercel будет автоматически использовать его как точку входа
app = Flask(__name__)

# -------------------------------------------------
# Конфигурация (переменные окружения)
# -------------------------------------------------
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ASSISTANT_ID = os.getenv("OPENAI_ASSISTANT_ID")

# Проверки вынесены на уровень модуля для быстрой диагностики при запуске
if not BOT_TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN не задан")
if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY не задан")
if not ASSISTANT_ID:
    raise RuntimeError("OPENAI_ASSISTANT_ID не задан")

client = OpenAI(api_key=OPENAI_API_KEY)

# -------------------------------------------------
# Асинхронная обработка одного сообщения (код без изменений)
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
        for _ in range(30):  # max ~9 сек
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
        try:
            await bot.send_message(
                chat_id=chat_id,
                text=err,
                reply_to_message_id=message_id,
            )
        except Exception as send_exc:
            print(f"Не удалось отправить сообщение об ошибке: {send_exc}")
        return {"status": "error", "message": str(exc)}

# -------------------------------------------------
# Flask-route (новая точка входа)
# -------------------------------------------------
@app.route('/api/telegram_webhook', methods=['POST'])
def telegram_webhook():
    try:
        # Получаем JSON из тела запроса с помощью Flask
        update = request.get_json(force=True)

        # ------------------- только текстовые сообщения -------------------
        msg = update.get("message", {})
        if not msg or not msg.get("text"):
            return jsonify({"status": "ignored"})

        chat_id = msg["chat"]["id"]
        text = msg["text"]
        message_id = msg["message_id"]

        # ------------------- запуск async -------------------
        # Запускаем асинхронную функцию и дожидаемся результата
        result = asyncio.run(process_message(chat_id, text, message_id))

        # Возвращаем JSON-ответ
        return jsonify(result)

    except json.JSONDecodeError as e:
        print(f"JSON Decode Error: {e}")
        return jsonify({"error": f"bad json: {e}"}), 400
    except Exception as e:
        print(f"Unhandled Exception: {e}")
        return jsonify({"error": str(e)}), 500

# Переменная `handler` больше не нужна,
# Vercel автоматически обнаружит и использует объект `app`
