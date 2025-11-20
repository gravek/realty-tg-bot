# api/webhook.py
import os
from flask import Flask, request, jsonify
from telegram import Bot, InputMediaPhoto
import asyncio
from Elaj_agent_1 import run_workflow, WorkflowInput

app = Flask(__name__)
bot = Bot(token=os.environ["TELEGRAM_BOT_TOKEN"])

async def handle_message(chat_id: int, text: str, message_id: int):
    try:
        # Приветствие
        if text.strip().lower() == "/start":
            welcome = (
                "Приветствую! \n\n"
                "Я — Эладж, ваш агент по премиум-недвижимости Аджарии 🌊\n\n"
                "Апартаменты на первой линии • Доходность 10–12% • Вид на море\n\n"
                "Напишите, что вас интересует: покупка, аренда, инвестиции?\n"
                "Или сразу к менеджеру → @a4k5o6"
            )
            await bot.send_message(chat_id=chat_id, text=welcome, reply_to_message_id=message_id)
            return

        await bot.send_chat_action(chat_id=chat_id, action="typing")

        # ←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←
        # Здесь запускается ваш настоящий агент из Agents SDK
        result = await run_workflow(WorkflowInput(input_as_text=text))
        response = result["output_text"]
        # →→→→→→→→→→→→→→→→→→→→→→→→→→→→→→→→→

        # Поддержка фото и альбомов (как вы прописали в промпте)
        if response.startswith("[photos:"):
            urls = [u.strip() for u in response.split("]", 1)[0][8:].split("|") if u.strip()]
            text_part = response.split("]", 1)[1].strip() if "]" in response[8:] else ""
        elif response.startswith("[photo:"):
            url = response.split("]", 1)[0][7:].strip()
            text_part = response.split("]", 1)[1].strip() if "]" in response[7:] else ""
            await bot.send_photo(chat_id=chat_id, photo=url, caption=text_part[:1024], reply_to_message_id=message_id)
            if len(text_part) > 1024:
                await bot.send_message(chat_id=chat_id, text=text_part[1024:], reply_to_message_id=message_id)
            return
        else:
            urls = []
            text_part = response

        # Альбом до 10 фото
        if urls:
            media = [InputMediaPhoto(media=url, caption=text_part[:1024] if i == 0 else None)
                     for i, url in enumerate(urls[:10])]
            await bot.send_media_group(chat_id=chat_id, media=media, reply_to_message_id=message_id)
            if len(text_part) > 1024:
                await bot.send_message(chat_id=chat_id, text=text_part[1024:], reply_to_message_id=message_id)
        else:
            await bot.send_message(chat_id=chat_id, text=text_part, reply_to_message_id=message_id, disable_web_page_preview=True)

    except Exception as e:
        print("Ошибка:", e)
        await bot.send_message(
            chat_id=chat_id,
            text="Техническая заминка 🤖\nПишите сразу @a4k5o6 — он ответит мгновенно!",
            reply_to_message_id=message_id
        )

@app.post("/")
async def webhook():
    update = request.get_json()
    msg = update.get("message", {})
    if not msg or "text" not in msg:
        return jsonify(ok=True)

    chat_id = msg["chat"]["id"]
    text = msg["text"]
    message_id = msg["message_id"]

    asyncio.create_task(handle_message(chat_id, text, message_id))
    return jsonify(ok=True)