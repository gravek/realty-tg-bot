import asyncio
import logging
import os
import json
from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message
from aiogram.filters import Command, CommandStart
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# States for conversation
class RealtyStates(StatesGroup):
    asking_location = State()
    asking_property_type = State()
    asking_budget = State()
    asking_rooms = State()

# Инициализация бота и диспетчера внутри функции (stateless для serverless)
async def get_bot_dp():
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN environment variable is not set")
    
    bot = Bot(token=BOT_TOKEN)
    storage = MemoryStorage()  # Временное хранилище, без БД
    dp = Dispatcher(storage=storage)
    
    # Router
    router = Router()
    dp.include_router(router)
    
    # Регистрация хендлеров
    @router.message(CommandStart())
    async def command_start_handler(message: Message, state: FSMContext) -> None:
        logger.info(f"Received /start from {message.from_user.id}")
        await state.clear()
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
            elif current_state == RealtyStates.asking_property_type.state:
                await handle_property_type_response(message, state)
            elif current_state == RealtyStates.asking_budget.state:
                await handle_budget_response(message, state)
            elif current_state == RealtyStates.asking_rooms.state:
                await handle_rooms_response(message, state)
            else:
                await message.answer("Извините, не понял. Напишите /start.")
        else:
            await handle_free_text_request(message)

    async def handle_location_response(message: Message, state: FSMContext) -> None:
        location = message.text
        await state.update_data(location=location)
        await state.set_state(RealtyStates.asking_property_type)
        await message.answer(
            f"📍 Отлично! Вы выбрали: {location}\n\n"
            "🏠 Какой тип недвижимости? (e.g., квартира, апартаменты)"
        )

    async def handle_property_type_response(message: Message, state: FSMContext) -> None:
        property_type = message.text
        await state.update_data(property_type=property_type)
        await state.set_state(RealtyStates.asking_budget)
        await message.answer(
            f"🏠 Тип: {property_type}\n\n"
            "💰 Бюджет? (e.g., 100k$ или 5000000 руб)"
        )

    async def handle_budget_response(message: Message, state: FSMContext) -> None:
        budget = message.text
        await state.update_data(budget=budget)
        await state.set_state(RealtyStates.asking_rooms)
        await message.answer(
            f"💰 Бюджет: {budget}\n\n"
            "🛏 Сколько комнат? (e.g., 1, 2, студия)"
        )

    async def handle_rooms_response(message: Message, state: FSMContext) -> None:
        rooms = message.text
        user_data = await state.get_data()
        location = user_data.get("location", "Не указано")
        property_type = user_data.get("property_type", "Не указано")
        budget = user_data.get("budget", "Не указано")
        
        await state.clear()
        
        await message.answer(
            f"🛏 Спасибо!\n\n"
            f"Ваши параметры:\n"
            f"📍 {location}\n"
            f"🏠 {property_type}\n"
            f"💰 {budget}\n"
            f"🛏 {rooms}\n\n"
            "Рекомендую апартаменты в Чакви, ул. Батумская 16А. Подробности: https://akoukounov.sourcecraft.site/realty-landing/"
        )

    async def handle_free_text_request(message: Message) -> None:
        text = message.text
        await message.answer(
            f"🔍 По вашему запросу '{text}':\n\n"
            "Рекомендую апартаменты в Чакви, ул. Батумская 16А.\n"
            "Цена: от 100k$. Подробности: https://akoukounov.sourcecraft.site/realty-landing/"
        )

    return bot, dp

# Обработчик события для Yandex Cloud Functions
async def process_event(event, context):
    try:
        logger.info(f"Event: {event}")
        update_data = json.loads(event['body'])
        
        bot, dp = await get_bot_dp()  # Инициализация на каждый вызов
        await dp.feed_raw_update(bot, update_data)
        
        # Минимальная задержка для завершения асинхронных задач
        await asyncio.sleep(0.1)
        
        return {'statusCode': 200, 'body': 'OK'}
    except Exception as e:
        logger.error(f"Process error: {e}", exc_info=True)
        return {'statusCode': 500, 'body': str(e)}
    finally:
        if 'bot' in locals():
            await bot.session.close()

# Локальный тест (опционально)
async def main():
    bot, dp = await get_bot_dp()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())