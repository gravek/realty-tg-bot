import json
import os
import asyncio
import re
from telegram import Bot, InputMediaPhoto
from openai import OpenAI
from flask import Flask, request, jsonify
import time

app = Flask(__name__)

# Конфигурация
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ASSISTANT_ID = os.getenv("OPENAI_ASSISTANT_ID")
THREAD_CACHE = {}  # {chat_id: thread_id}

if not BOT_TOKEN or not OPENAI_API_KEY or not ASSISTANT_ID:
    raise RuntimeError("Missing environment variables")

client = OpenAI(api_key=OPENAI_API_KEY)

async def process_message(chat_id: int, text: str, message_id: int):
    bot = Bot(token=BOT_TOKEN)
    try:
        # === /start: сброс истории ===
        if text.strip().lower() == "/start":
            if chat_id in THREAD_CACHE:
                del THREAD_CACHE[chat_id]
            response = (
                "Привет! Я — ваш помощник по недвижимости в Аджарии 🌊\n\n"
                "Подберу апартаменты с видом на море, доходностью 8–12% и премиум-инфраструктурой.\n"
                "Напишите: покупка, аренда, инвестиции?\n\n"
                "Или сразу к менеджеру: @a4k5o6"
            )
            await bot.send_message(chat_id=chat_id, text=response, reply_to_message_id=message_id)
            return {"status": "ok"}

        # === История: кэш thread_id ===
        thread_id = THREAD_CACHE.get(chat_id)
        if not thread_id:
            thread = await asyncio.to_thread(client.beta.threads.create)
            thread_id = thread.id
            THREAD_CACHE[chat_id] = thread_id

        # === Добавляем сообщение ===
        await asyncio.to_thread(
            client.beta.threads.messages.create,
            thread_id=thread_id,
            role="user",
            content=text
        )

        # === Запуск с лимитами токенов ===
        await bot.send_chat_action(chat_id=chat_id, action="typing")
        run = await asyncio.to_thread(
            client.beta.threads.runs.create,
            thread_id=thread_id,
            assistant_id=ASSISTANT_ID,
            # max_completion_tokens=300,
            # max_prompt_tokens=3000,
        )

        # === Ожидание с typing ===
        timeout = 60
        interval = 2.0  # ← каждые 2 сек — оптимально
        elapsed = 0

        while elapsed < timeout:
            status = await asyncio.to_thread(
                client.beta.threads.runs.retrieve,
                thread_id=thread_id,
                run_id=run.id,
            )

            if status.status in {"completed", "failed", "cancelled", "expired"}:
                print(f"[DEBUG] Run status: {status.status}, elapsed: {elapsed}s (break)", flush=True)
                break

            # Ждём перед следующей проверкой
            await asyncio.to_thread(time.sleep, interval)
            # await asyncio.sleep(interval)
            elapsed += interval

            # typing — не чаще чем раз в 4 сек
            if int(elapsed) % 5 == 0:
                await bot.send_chat_action(chat_id=chat_id, action="typing")
        else:
            print(f"[DEBUG] Timeout! Run status: {status.status}, elapsed: {elapsed}s, ", flush=True)
            response = "Ой, я слишком долго думаю 🤔\nПопробуйте, пожалуйста еще раз или сразу напишите менеджеру @a4k5o6 — он ответит мгновенно!"
            await bot.send_message(chat_id=chat_id, text=response, reply_to_message_id=message_id)
            return {"status": "timeout"}

        
        if status.status != "completed":
            response = "АХ! У меня что-то разомкнулось 🤖! \nПовторите, пожалуйста, еще раз! \n https://a.d-cd.net/JQAAAgAH4-A-480.jpg."
        else:
            msgs = await asyncio.to_thread(
                client.beta.threads.messages.list,
                thread_id=thread_id,
            )
            response = msgs.data[0].content[0].text.value

            # Логируем длину ответа для настройки лимитов
            response_tokens = len(response.split()) * 1.3  # Примерная оценка
            print(f"[DEBUG] Response length: {len(response)} chars, ~{int(response_tokens)} tokens")

        
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
                reply_to_message_id=message_id,
                disable_web_page_preview=True
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
                # Для send_media_group (album)
                media = []
                for i, url in enumerate(urls[:10]):
                    caption = clean_response[:1024] if i == 0 else None
                    if caption and 'http' in caption:  # Wrap URLs in HTML to disable preview
                        caption = re.sub(r'(https?://[^\s]+)', r'<a href="\1">Фото</a>', caption)
                    media.append(InputMediaPhoto(media=url, caption=caption, parse_mode='HTML'))  # ← parse_mode=HTML
                await bot.send_media_group(
                    chat_id=chat_id,
                    media=media,
                    reply_to_message_id=message_id
                )

                # Для дополнительного текста
                if len(clean_response) > 1024:
                    extra_text = clean_response[1024:]
                    if 'http' in extra_text:  # Wrap URLs
                        extra_text = re.sub(r'(https?://[^\s]+)', r'<a href="\1">Ссылка</a>', extra_text)
                    await bot.send_message(
                        chat_id=chat_id,
                        text=extra_text,
                        reply_to_message_id=message_id,
                        parse_mode='HTML',  # ← Для поддержки <a>
                        disable_web_page_preview=True  # ← Добавьте
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
