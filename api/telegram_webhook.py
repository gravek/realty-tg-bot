import os
import json
from flask import Flask, request, jsonify
from telegram import Bot, InputMediaPhoto
import asyncio
import redis
from typing import List, Dict

# ==================== REDIS (Upstash) ====================
# Добавь в Vercel/Railway/Render переменную окружения: REDIS_URL
# Пример: rediss://:xxxxxx@eu1-something.upstash.io:6379
redis_client = redis.from_url(os.environ["REDIS_URL"])

def get_chat_history(chat_id: int) -> List[Dict]:
    raw = redis_client.get(f"elaj:chat:{chat_id}")
    if raw:
        return json.loads(raw)
    return []

def save_chat_history(chat_id: int, history: List[Dict]):
    # Храним 30 дней (можно увеличить)
    redis_client.setex(f"elaj:chat:{chat_id}", 30 * 24 * 3600, json.dumps(history))

# ==================== AGENT CODE (без изменений) ====================
from agents import FileSearchTool, RunContextWrapper, Agent, ModelSettings, Runner, RunConfig, trace
from pydantic import BaseModel

file_search = FileSearchTool(vector_store_ids=["vs_691f2fe03e688191b02f782af77e8f9b"])

class ElajAgent1Context:
    def __init__(self, workflow_input_as_text: str):
        self.workflow_input_as_text = workflow_input_as_text

def elaj_agent_1_instructions(run_context: RunContextWrapper[ElajAgent1Context], _agent):
    workflow_input_as_text = run_context.context.workflow_input_as_text
    return f"""Вы — Эладж, профессиональный агент по продвижению доходной недвижимости... {workflow_input_as_text}"""
    # (весь твой длинный промпт остаётся без изменений — вставь его полностью сюда)

elaj_agent_1 = Agent(
    name="Elaj_agent_1",
    instructions=elaj_agent_1_instructions,
    model="gpt-4.1",
    tools=[file_search],
    model_settings=ModelSettings(temperature=1, top_p=1, max_tokens=1024, store=True)
)

class WorkflowInput(BaseModel):
    input_as_text: str

async def run_workflow_with_history(chat_id: int, text: str) -> str:
    # 1. Загружаем историю из Redis
    history: List[Dict] = get_chat_history(chat_id)

    # 2. Добавляем новое сообщение пользователя
    user_msg = {
        "role": "user",
        "content": [{"type": "input_text", "text": text}]
    }
    history.append(user_msg)

    # 3. Ограничиваем длину (экономим токены + не превышаем лимит модели)
    history = history[-20:]  # ≈ 10 пар вопрос-ответ

    # 4. Запускаем агента с полной историей
    with trace("Elaj_agent_1"):
        result = await Runner.run(
            elaj_agent_1,
            input=history,  # ← ВСЯ ИСТОРИЯ!
            run_config=RunConfig(trace_metadata={
                "__trace_source__": "agent-builder",
                "workflow_id": "wf_691f400a1a7c8190b2e160dc5cde22bf0a9d46819d43210a"
            }),
            context=ElajAgent1Context(workflow_input_as_text=text)
        )

    response_text = result.final_output_as(str)

    # 5. Сохраняем ответ бота в историю
    assistant_msg = {
        "role": "assistant",
        "content": [{"type": "input_text", "text": response_text}]
    }
    history.append(assistant_msg)
    save_chat_history(chat_id, history)

    return response_text

# ==================== TELEGRAM HANDLER ====================
app = Flask(__name__)

async def handle_message_async(chat_id: int, text: str, message_id: int):
    try:
        bot = Bot(token=os.environ["TELEGRAM_BOT_TOKEN"])

        # /start — сбрасываем историю
        if text.strip().lower() == "/start":
            # Полностью очищаем память о предыдущем диалоге
            redis_client.delete(f"elaj:chat:{chat_id}")

            welcome = (
                "Добро пожаловать обратно 🌊\n\n"
                "Я — Эладж, ваш личный агент по премиум-недвижимости на черноморском побережье Аджарии.\n\n"
                "• Первая линия моря\n"
                "• Видовые апартаменты с доходностью 10–12% годовых\n"
                "• Полное сопровождение сделки и управление арендой\n\n"
                "Чем могу помочь сегодня?\n"
                "— Подобрать объект для покупки\n"
                "— Найти апартаменты для отдыха\n"
                "— Рассчитать инвестиционную доходность\n\n"
                "Или пишите сразу менеджеру → @a4k5o6 (Андрей)\n\n"
                "P.S. Команда /start всегда начинает наш диалог с чистого листа"
            )

            await bot.send_message(
                chat_id=chat_id,
                text=welcome,
                reply_to_message_id=message_id,
                disable_web_page_preview=True
            )
            return

        await bot.send_chat_action(chat_id=chat_id, action="typing")

        # ← Главное изменение: теперь агент получает всю историю
        response = await run_workflow_with_history(chat_id, text)

        # === Обработка фото и альбомов (остаётся как у тебя) ===
        if response.startswith("[photos:"):
            urls = [u.strip() for u in response.split("]", 1)[0][8:].split("|") if u.strip()]
            text_part = response.split("]", 1)[1].strip() if "]" in response else ""
        elif response.startswith("[photo:"):
            url = response.split("]", 1)[0][7:].strip()
            text_part = response.split("]", 1)[1].strip() if "]" in response else ""
            await bot.send_photo(chat_id=chat_id, photo=url, caption=text_part[:1024], reply_to_message_id=message_id)
            if len(text_part) > 1024:
                await bot.send_message(chat_id=chat_id, text=text_part[1024:], reply_to_message_id=message_id)
            return
        else:
            urls = []
            text_part = response

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
        try:
            await bot.send_message(
                chat_id=chat_id,
                text="Техническая заминка\nПишите сразу @a4k5o6 — он ответит мгновенно!",
                reply_to_message_id=message_id
            )
        except:
            pass

# ==================== WEBHOOK ====================
@app.route('/api/telegram_webhook', methods=['POST', 'GET'])
def webhook():
    if request.method == 'GET':
        return jsonify({"status": "Elaj Bot + Redis history ready"})

    update = request.get_json()
    msg = update.get("message", {})
    if not msg or "text" not in msg:
        return jsonify(ok=True)

    chat_id = msg["chat"]["id"]
    text = msg["text"]
    message_id = msg["message_id"]

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(handle_message_async(chat_id, text, message_id))
    finally:
        loop.close()

    return jsonify(ok=True)

if __name__ == "__main__":
    app.run(debug=True)