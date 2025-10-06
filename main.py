import asyncio
import logging
import os
import json
from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, CommandStart
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.methods import SetWebhook

# Configure logging
logging.basicConfig(level=logging.INFO)

# Initialize bot and dispatcher
BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is not set")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Router for handling messages
router = Router()
dp.include_router(router)

# States for conversation
class RealtyStates(StatesGroup):
    asking_location = State()
    asking_property_type = State()
    asking_budget = State()
    asking_rooms = State()

# In-memory storage for user data (in production, use a database)
user_states = {}
user_preferences = {}

# Command handlers
@router.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    user_id = message.from_user.id
    # Reset user state
    if user_id in user_states:
        del user_states[user_id]
    if user_id in user_preferences:
        del user_preferences[user_id]
    
    await message.answer(
        "Здравствуйте! 👋\n\n"
        "Я AI-консультант по недвижимости. Я помогу вам подобрать идеальное жилье, "
        "соответствующее вашим требованиям и бюджету.\n\n"
        "Для начала подбора просто опишите, какую недвижимость вы ищете, или ответьте на несколько вопросов.\n\n"
        "Напишите, например:\n"
        "- \"Ищу квартиру в Москве, бюджет 5 млн\"\n"
        "- \"Нужен дом в Подмосковье до 10 млн\"\n"
        "- \"Хочу студию в центре Санкт-Петербурга\"\n\n"
        "Или отправьте команду /find для пошагового подбора."
    )

@router.message(Command("help"))
async def command_help_handler(message: Message) -> None:
    await message.answer(
        "🤖 Я AI-консультант по недвижимости\n\n"
        "Доступные команды:\n"
        "/find - Пошаговый подбор недвижимости\n"
        "/start - Начать сначала\n"
        "/help - Показать эту справку\n\n"
        "Просто опишите, какую недвижимость вы ищете, и я подберу для вас лучшие варианты!"
    )

@router.message(Command("find"))
async def command_find_handler(message: Message, state: FSMContext) -> None:
    user_id = message.from_user.id
    await state.set_state(RealtyStates.asking_location)
    await message.answer("📍 В каком городе или районе вы хотите искать недвижимость?")

# Handle free text requests
@router.message(F.text)
async def handle_text_message(message: Message, state: FSMContext) -> None:
    user_id = message.from_user.id
    current_state = await state.get_state()
    
    # If user is in a conversation state, handle accordingly
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
            await message.answer(
                "Извините, не понял ваш запрос. Напишите /start чтобы начать сначала или /help для помощи."
            )
    else:
        # Handle free text request
        await handle_free_text_request(message)

async def handle_free_text_request(message: Message) -> None:
    user_text = message.text
    await message.answer(
        f"🔍 Я проанализировал ваш запрос: \"{user_text}\"\n\n"
        "На основе вашего описания я могу предложить следующие варианты недвижимости:\n\n"
        "🏠 Вариант 1: \n"
        "- Тип: Квартира\n"
        "- Местоположение: Москва, район Центральный\n"
        "- Цена: 4 800 000 ₽\n"
        "- Площадь: 45 м²\n"
        "- Комнат: 1\n"
        "- [Подробнее] - ссылка на объект\n\n"
        "🏘 Вариант 2:\n"
        "- Тип: Квартира\n"
        "- Местоположение: Москва, район Северный\n"
        "- Цена: 5 200 000 ₽\n"
        "- Площадь: 52 м²\n"
        "- Комнат: 2\n"
        "- [Подробнее] - ссылка на объект\n\n"
        "🏢 Вариант 3:\n"
        "- Тип: Апартаменты\n"
        "- Местоположение: Москва, район Пресненский\n"
        "- Цена: 6 500 000 ₽\n"
        "- Площадь: 65 м²\n"
        "- Комнат: 2\n"
        "- [Подробнее] - ссылка на объект\n\n"
        "Хотите получить больше вариантов? Напишите /find для детального подбора или уточните параметры поиска."
    )

async def handle_location_response(message: Message, state: FSMContext) -> None:
    location = message.text
    await state.update_data(location=location)
    await state.set_state(RealtyStates.asking_property_type)
    await message.answer(
        f"📍 Отлично! Вы выбрали: {location}\n\n"
        "🏠 Какой тип недвижимости вас интересует?\n"
        "Например: квартира, дом, комната, таунхаус, апартаменты"
    )

async def handle_property_type_response(message: Message, state: FSMContext) -> None:
    property_type = message.text
    await state.update_data(property_type=property_type)
    await state.set_state(RealtyStates.asking_budget)
    await message.answer(
        f"🏠 Тип недвижимости: {property_type}\n\n"
        "💰 Какой у вас бюджет? Укажите сумму в рублях.\n"
        "Например: 5000000 или 5 млн"
    )

async def handle_budget_response(message: Message, state: FSMContext) -> None:
    budget_text = message.text
    # Simple budget processing
    budget = budget_text
    if "млн" in budget_text.lower():
        try:
            num = float("".join(filter(str.isdigit, budget_text)))
            budget = int(num * 1000000)
        except ValueError:
            pass
    
    await state.update_data(budget=budget)
    await state.set_state(RealtyStates.asking_rooms)
    await message.answer(
        f"💰 Бюджет: {budget} ₽\n\n"
        "🛏 Сколько комнат вам нужно?\n"
        "Например: 1, 2, 3, студия"
    )

async def handle_rooms_response(message: Message, state: FSMContext) -> None:
    rooms = message.text
    user_data = await state.get_data()
    
    # Get all preferences
    location = user_data.get("location", "Не указано")
    property_type = user_data.get("property_type", "Не указано")
    budget = user_data.get("budget", "Не указано")
    
    # Clear state
    await state.clear()
    
    # Provide recommendations
    try:
        budget_num = int(budget)
        price_95 = round(budget_num * 0.95)
        price_100 = round(budget_num)
        price_105 = round(budget_num * 1.05)
    except (ValueError, TypeError):
        price_95 = price_100 = price_105 = "Не определено"
    
    area_range = "40-55" if rooms in ["1", "студия"] else "60-90"
    
    await message.answer(
        f"🛏 Спасибо за информацию!\n\n"
        f"Ваши предпочтения:\n"
        f"📍 Местоположение: {location}\n"
        f"🏠 Тип недвижимости: {property_type}\n"
        f"💰 Бюджет: {budget} ₽\n"
        f"🛏 Комнат: {rooms}\n\n"
        f"На основе этих данных я подобрал для вас следующие варианты:\n\n"
        f"🏠 Вариант 1: \n"
        f"- {property_type} в {location}\n"
        f"- Цена: {price_95:,} ₽\n"
        f"- Площадь: {area_range} м²\n"
        f"- [Подробнее] - ссылка на объект\n\n"
        f"🏘 Вариант 2:\n"
        f"- {property_type} в {location}\n"
        f"- Цена: {price_100:,} ₽\n"
        f"- Площадь: {area_range} м²\n"
        f"- [Подробнее] - ссылка на объект\n\n"
        f"🏢 Вариант 3:\n"
        f"- {property_type} в {location}\n"
        f"- Цена: {price_105:,} ₽\n"
        f"- Площадь: {area_range} м²\n"
        f"- [Подробнее] - ссылка на объект\n\n"
        f"Хотите изменить параметры поиска? Напишите /find для нового поиска или /start чтобы начать сначала."
    )

# Handler for AWS Lambda or Yandex Cloud Functions
async def process_event(event, context):
    """
    Process event from Yandex Cloud Functions
    """
    try:
        # Parse update from event body
        update_data = json.loads(event['body'])
        
        # Process update
        update = dp.resolve_update(update_data)
        await dp.feed_update(bot, update)
        
        return {
            'statusCode': 200,
            'body': ''
        }
    except Exception as e:
        logging.error(f"Error processing event: {e}")
        return {
            'statusCode': 500,
            'body': str(e)
        }

# For local testing
async def main():
    # Set webhook for Telegram
    webhook_url = os.environ.get("WEBHOOK_URL")
    if webhook_url:
        await bot(SetWebhook(url=webhook_url))
        logging.info(f"Webhook set to {webhook_url}")
    
    # Start polling (for local testing)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())