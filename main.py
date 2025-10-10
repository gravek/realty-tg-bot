import asyncio
import logging
import os
import json
from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, CommandStart
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage  # Временно; потом Redis/PostgreSQL
import asyncpg  # Для БД (Yandex PostgreSQL)
import nest_asyncio

# Для AI: YandexGPT (замените на ваш API key)
# from openai import AsyncOpenAI  # YandexGPT совместим с OpenAI API
# client = AsyncOpenAI(base_url="https://llm.api.cloud.yandex.net/foundationModels/v1/completion", api_key=os.getenv("YANDEX_API_KEY"))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
nest_asyncio.apply()

# States for conversation (расширили для AI)
class RealtyStates(StatesGroup):
    asking_location = State()
    asking_property_type = State()
    asking_budget = State()
    asking_rooms = State()
    recommending = State()  # Новое: для AI-рекомендаций
    details = State()  # Для уточнения о апартаментах

# БД config (Yandex Managed PostgreSQL)
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'your-db.host.yandexcloud.net'),
    'port': int(os.getenv('DB_PORT', 5432)),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'database': os.getenv('DB_NAME', 'realty_db'),
}

# Глобальные? Нет, инициализируем в process_event для stateless
async def get_bot_dp():
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN environment variable is not set")
    
    bot = Bot(token=BOT_TOKEN)
    storage = MemoryStorage()  # TODO: Заменить на PostgreSQLStorage для диалогов
    dp = Dispatcher(storage=storage)
    
    # Router
    router = Router()
    dp.include_router(router)
    
    # Регистрация хендлеров (здесь же, чтобы stateless)
    register_handlers(router)
    
    return bot, dp

def register_handlers(router: Router):
    @router.message(CommandStart())
    async def command_start_handler(message: Message, state: FSMContext) -> None:
        logger.info(f"Received /start from {message.from_user.id}")
        await state.clear()
        user_id = message.from_user.id
        # Сохранить пользователя в БД (заглушка)
        await save_user_to_db(user_id, "new_session")
        
        await message.answer(
            "Здравствуйте! 👋\n\n"
            "Я AI-консультант по апартаментам в Грузии (Аджария, Чакви).\n"
            "Расскажите, что вас интересует: квартира у моря, бюджет, комнаты?\n\n"
            "Или /find для опроса."
        )

    @router.message(Command("help"))
    async def command_help_handler(message: Message) -> None:
        await message.answer(
            "🤖 Помощь:\n"
            "/start - Старт\n"
            "/find - Опрос\n"
            "/help - Это\n\n"
            "Пример: 'Ищу апартаменты в Чакви до 100k$'"
        )

    @router.message(Command("find"))
    async def command_find_handler(message: Message, state: FSMContext) -> None:
        await state.set_state(RealtyStates.asking_location)
        await message.answer("📍 Город/район? (e.g., Чакви, Аджария)")

    @router.message(F.text)
    async def handle_text_message(message: Message, state: FSMContext) -> None:
        user_id = message.from_user.id
        current_state = await state.get_state()
        text = message.text.lower()
        
        logger.info(f"Text from {user_id}: {text}")
        
        if current_state:
            if current_state == RealtyStates.asking_location.state:
                await handle_location_response(message, state)
            # ... (остальные handle_ как в оригинале, но с БД)
            elif current_state == RealtyStates.recommending.state:
                await handle_ai_recommendation(message, state, text)
        else:
            # Free text: AI-анализ
            await handle_free_text_request(message, state)

    # ... (handle_location_response, handle_property_type_response и т.д. — как в оригинале, но добавьте await save_dialog_to_db(user_id, text) в каждый)

    async def handle_free_text_request(message: Message, state: FSMContext) -> None:
        user_id = message.from_user.id
        text = message.text
        
        # Сохранить диалог
        await save_dialog_to_db(user_id, text)
        
        # AI-рекомендация (заглушка; интегрируйте YandexGPT)
        recommendations = await get_ai_recommendations(text)  # RAG query
        
        await state.set_state(RealtyStates.recommending)
        await message.answer(
            f"🔍 По вашему запросу '{text}':\n\n"
            f"{recommendations}\n\n"
            "Уточните? (e.g., 'Фото апартаментов')"
        )

    async def handle_ai_recommendation(message: Message, state: FSMContext, query: str) -> None:
        # AI-диалог
        response = await query_yandex_gpt(query, context="апартаменты в Чакви")  # RAG + GPT
        await save_dialog_to_db(message.from_user.id, query, response)
        await message.answer(response)
        if "купить" in query:
            await message.answer("Ссылка на сайт: https://akoukounov.sourcecraft.site/realty-landing/")

# БД функции (asyncpg)
async def get_db_pool():
    return await asyncpg.create_pool(**DB_CONFIG)

async def save_user_to_db(user_id: int, session_info: str):
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO users (id, session_info) VALUES ($1, $2) ON CONFLICT (id) DO UPDATE SET session_info = $2",
            user_id, session_info
        )

async def save_dialog_to_db(user_id: int, user_msg: str, bot_msg: str = None):
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO dialogs (user_id, user_msg, bot_msg, timestamp) VALUES ($1, $2, $3, NOW())",
            user_id, user_msg, bot_msg
        )

async def get_ai_recommendations(query: str) -> str:
    # RAG: Query pgvector
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        # Пример: similarity search по embeddings
        row = await conn.fetchrow(
            "SELECT content FROM properties ORDER BY embedding <=> $1 LIMIT 1",
            query  # В реале: embed(query) via sentence-transformers
        )
        if row:
            return f"🏠 Рекомендация: {row['content']}\nЦена: 150k GEL\nФото: [URL]"
    return "Идеально подойдут апартаменты в Чакви, ул. Батумская 16А. Бюджет от 100k$."

async def query_yandex_gpt(prompt: str, context: str) -> str:
    # Заглушка; реал: client.chat.completions.create
    return f"На основе {context}: {prompt} — рекомендую апартаменты в Чакви! Подробности на сайте."

# Process event (основной handler для CF)
async def process_event(event, context):
    try:
        logger.info(f"Event: {event}")
        update_data = json.loads(event['body'])
        
        bot, dp = await get_bot_dp()  # Инициализация на каждый вызов
        await dp.feed_raw_update(bot, update_data)
        
        # Graceful shutdown: Ждём pending tasks
        await asyncio.sleep(0.1)  # Минимальная задержка для cleanup
        
        return {'statusCode': 200, 'body': 'OK'}
    except Exception as e:
        logger.error(f"Process error: {e}", exc_info=True)
        return {'statusCode': 500, 'body': str(e)}
    finally:
        # Закрыть bot/dp
        if 'bot' in locals():
            await bot.session.close()

# Local test
async def main():
    bot, dp = await get_bot_dp()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())