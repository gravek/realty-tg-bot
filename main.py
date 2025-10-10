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
        "Здравствуйте! 👋

"
        "Я AI-консультант по недвижимости. Я помогу вам подобрать идеальное жилье, "
        "соответствующее вашим требованиям и бюджету.

"
        "Для начала подбора просто опишите, какую недвижимость вы ищете, или ответьте на несколько вопросов.

"
        "Напишите, например:
"
        "- "Ищу квартиру в Москве, бюджет 5 млн"
"
        "- "Нужен дом в Подмосковье до 10 млн"
"
        "- "Хочу студию в центре Санкт-Петербурга"

"
        "Или отправьте команду /find для пошагового подбора."
    )

@router.message(Command("help"))
async def command_help_handler(message: Message) -> None:
    await message.answer(
        "🤖 Я AI-консультант по недвижимости

"
        "Доступные команды:
"
        "/find - Пошаговый подбор недвижимости
"
        "/start - Начать сначала
"
        "/help - Показать эту справку

"
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
        f"🔍 Я проанализировал ваш запрос: "{user_text}"

"
        "На основе вашего описания я могу предложить следующие варианты недвижимости:

"
        "🏠 Вариант 1: 
"
        "- Тип: Квартира
"
        "- Местоположение: Москва, район Центральный
"
        "- Цена: 4 800 000 ₽
"
        "- Площадь: 45 м²
"
        "- Комнат: 1
"
        "- [Подробнее] - ссылка на объект

"
        "🏘 Вариант 2:
"
        "- Тип: Квартира
"
        "- Местоположение: Москва, район Северный
"
        "- Цена: 5 200 000 ₽
"
        "- Площадь: 52 м²
"
        "- Комнат: 2
"
        "- [Подробнее] - ссылка на объект

"
        "🏢 Вариант 3:
"
        "- Тип: Апартаменты
"
        "- Местоположение: Москва, район Пресненский
"
        "- Цена: 6 500 000 ₽
"
        "- Площадь: 65 м²
"
        "- Комнат: 2
"
        "- [Подробнее] - ссылка на объект

"
        "Хотите получить больше вариантов? Напишите /find для детального подбора или уточните параметры поиска."
    )

async def handle_location_response(message: Message, state: FSMContext) -> None:
    location = message.text
    await state.update_data(location=location)
    await state.set_state(RealtyStates.asking_property_type)
    await message.answer(
        f"📍 Отлично! Вы выбрали: {location}

"
        "🏠 Какой тип недвижимости вас интересует?
"
        "Например: квартира, дом, комната, таунхаус, апартаменты"
    )

async def handle_property_type_response(message: Message, state: FSMContext) -> None:
    property_type = message.text
    await state.update_data(property_type=property_type)
    await state.set_state(RealtyStates.asking_budget)
    await message.answer(
        f"🏠 Тип недвижимости: {property_type}

"
        "💰 Какой у вас бюджет? Укажите сумму в рублях.
"
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
        f"💰 Бюджет: {budget} ₽

"
        "🛏 Сколько комнат вам нужно?
"
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
        f"🛏 Спасибо за информацию!

"
        f"Ваши предпочтения:
"
        f"📍 Местоположение: {location}
"
        f"🏠 Тип недвижимости: {property_type}
"
        f"💰 Бюджет: {budget} ₽
"
        f"🛏 Комнат: {rooms}

"
        f"На основе этих данных я подобрал для вас следующие варианты:

"
        f"🏠 Вариант 1: 
"
        f"- {property_type} в {location}
"
        f"- Цена: {price_95:,} ₽
"
        f"- Площадь: {area_range} м²
"
        f"- [Подробнее] - ссылка на объект

"
        f"🏘 Вариант 2:
"
        f"- {property_type} в {location}
"
        f"- Цена: {price_100:,} ₽
"
        f"- Площадь: {area_range} м²
"
        f"- [Подробнее] - ссылка на объект

"
        f"🏢 Вариант 3:
"
        f"- {property_type} в {location}
"
        f"- Цена: {price_105:,} ₽
"
        f"- Площадь: {area_range} м²
"
        f"- [Подробнее] - ссылка на объект

"
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