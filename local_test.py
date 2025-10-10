import json
import os
import asyncio
from main import process_event

# Тестовые события для проверки работы функции
test_events = [
    {
        "name": "Команда /start",
        "event": {
            "body": json.dumps({
                "update_id": 123456789,
                "message": {
                    "message_id": 1,
                    "from": {
                        "id": 987654321,
                        "is_bot": False,
                        "first_name": "Test",
                        "username": "testuser",
                        "language_code": "en"
                    },
                    "chat": {
                        "id": 987654321,
                        "first_name": "Test",
                        "username": "testuser",
                        "type": "private"
                    },
                    "date": 1616229231,
                    "text": "/start"
                }
            })
        }
    },
    {
        "name": "Команда /help",
        "event": {
            "body": json.dumps({
                "update_id": 123456790,
                "message": {
                    "message_id": 2,
                    "from": {
                        "id": 987654321,
                        "is_bot": False,
                        "first_name": "Test",
                        "username": "testuser",
                        "language_code": "en"
                    },
                    "chat": {
                        "id": 987654321,
                        "first_name": "Test",
                        "username": "testuser",
                        "type": "private"
                    },
                    "date": 1616229232,
                    "text": "/help"
                }
            })
        }
    },
    {
        "name": "Текстовое сообщение",
        "event": {
            "body": json.dumps({
                "update_id": 123456791,
                "message": {
                    "message_id": 3,
                    "from": {
                        "id": 987654321,
                        "is_bot": False,
                        "first_name": "Test",
                        "username": "testuser",
                        "language_code": "en"
                    },
                    "chat": {
                        "id": 987654321,
                        "first_name": "Test",
                        "username": "testuser",
                        "type": "private"
                    },
                    "date": 1616229233,
                    "text": "Ищу квартиру в Москве"
                }
            })
        }
    }
]

# Контекст (пустой для тестирования)
test_context = {}

async def test_function():
    """
    Тестирует функцию с различными событиями
    """
    print("Начало тестирования функции...")
    
    # Установим токен бота для тестирования (можно использовать фиктивный токен для локального тестирования)
    os.environ["BOT_TOKEN"] = "123456789:ABCDEF1234567890ABCDEF1234567890ABC"  # Фиктивный токен для тестирования
    
    for test_case in test_events:
        print(f"
--- Тест: {test_case['name']} ---")
        print(f"Событие: {test_case['event']}")
        
        try:
            # Создаем новый event loop для каждого теста
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Запускаем функцию
            result = await process_event(test_case['event'], test_context)
            print(f"Результат: {result}")
            
            loop.close()
            
        except Exception as e:
            print(f"Ошибка при тестировании: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    # Запускаем тесты
    asyncio.run(test_function())