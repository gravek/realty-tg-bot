import json
import os
import asyncio
import re
from telegram import Bot, InputMediaPhoto
from openai import OpenAI
from flask import Flask, request, jsonify

app = Flask(__name__)

# Конфигурация
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ASSISTANT_ID = os.getenv("OPENAI_ASSISTANT_ID")

if not BOT_TOKEN or not OPENAI_API_KEY or not ASSISTANT_ID:
    raise RuntimeError("Missing environment variables")

client = OpenAI(api_key=OPENAI_API_KEY)

async def process_message(chat_id: int, text: str, message_id: int):
    bot = Bot(token=BOT_TOKEN)
    try:
        await bot.send_chat_action(chat_id=chat_id, action="typing")

        # OpenAI Assistant (без изменений)
        thread = await asyncio.to_thread(
            client.beta.threads.create,
            messages=[{"role": "user", "content": text}]
        )
        run = await asyncio.to_thread(
            client.beta.threads.runs.create,
            thread_id=thread.id,
            assistant_id=ASSISTANT_ID,
        )

        import time
        for _ in range(30):
            status = await asyncio.to_thread(
                client.beta.threads.runs.retrieve,
                thread_id=thread.id,
                run_id=run.id,
            )
            if status.status in {"completed", "failed", "cancelled"}:
                break
            time.sleep(0.3)

        if status.status != "completed":
            response = "АХ! У меня что-то разомкнулось 🤖! \nПовторите, пожалуйста, еще раз! \n https://a.d-cd.net/JQAAAgAH4-A-480.jpg."
        else:
            msgs = await asyncio.to_thread(
                client.beta.threads.messages.list,
                thread_id=thread.id,
            )
            response = msgs.data[0].content[0].text.value

        # Парсинг ответа на фото/альбом
        photo_match = re.match(r'\[photo: (https?://[^\]]+)\]', response)
        photos_match = re.match(r'\[photos: ([^\]]+)\]', response)

        clean_response = response  # Текст без маркера

        if photo_match:
            url = photo_match.group(1).strip()
            clean_response = response[photo_match.end():].strip()
            await bot.send_photo(
                chat_id=chat_id,
                photo=url,
                caption=clean_response[:1024],  # Лимит caption
                reply_to_message_id=message_id
            )
            if len(clean_response) > 1024:
                await bot.send_message(
                    chat_id=chat_id,
                    text=clean_response[1024:],
                    reply_to_message_id=message_id
                )
            return {"status": "ok"}

        elif photos_match:
            urls = [u.strip() for u in photos_match.group(1).split('|') if u.strip()]
            clean_response = response[photos_match.end():].strip()
            if urls:
                media = []
                for i, url in enumerate(urls[:10]):  # Макс 10 в альбоме
                    caption = clean_response[:1024] if i == 0 else None
                    media.append(InputMediaPhoto(media=url, caption=caption))
                await bot.send_media_group(
                    chat_id=chat_id,
                    media=media,
                    reply_to_message_id=message_id
                )
                if len(clean_response) > 1024:
                    await bot.send_message(
                        chat_id=chat_id,
                        text=clean_response[1024:],
                        reply_to_message_id=message_id
                    )
                return {"status": "ok"}

        # Если нет фото, отправляем просто текст
        await bot.send_message(
            chat_id=chat_id,
            text=clean_response,
            reply_to_message_id=message_id,
        )
        return {"status": "ok"}

    except Exception as exc:
        err = f"Ошибка: {exc}"
        print(err)
        await bot.send_message(chat_id=chat_id, text=err, reply_to_message_id=message_id)
        return {"status": "error", "message": str(exc)}

@app.route('/api/telegram_webhook', methods=['POST'])
def telegram_webhook():
    try:
        update = request.get_json(force=True)
        msg = update.get("message", {})
        if not msg or not msg.get("text"):
            return jsonify({"status": "ignored"})

        chat_id = msg["chat"]["id"]
        text = msg["text"]
        message_id = msg["message_id"]

        return jsonify(asyncio.run(process_message(chat_id, text, message_id)))

    except Exception as e:
        print(f"Unhandled Exception: {e}")
        return jsonify({"error": str(e)}), 500
