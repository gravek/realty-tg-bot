import json
import os
import sys
from main import process_event

# Тестовое событие для проверки работы функции
test_event = {
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

# Контекст (пустой для тестирования)
test_context = {}

# Установим токен бота для тестирования
os.environ["BOT_TOKEN"] = "YOUR_BOT_TOKEN_HERE"  # Замените на реальный токен для тестирования

def debug_function():
    print("Testing function with /start command...")
    print(f"Event data: {test_event}")
    
    try:
        result = process_event(test_event, test_context)
        print(f"Function result: {result}")
    except Exception as e:
        print(f"Error occurred: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_function()