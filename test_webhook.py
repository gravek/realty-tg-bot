import os
import json
import requests

def test_webhook():
    # Получаем токен бота из переменной окружения
    bot_token = os.environ.get("BOT_TOKEN")
    if not bot_token:
        print("BOT_TOKEN environment variable is not set")
        return
    
    # Получаем URL вебхука из переменной окружения или используем тестовый
    webhook_url = os.environ.get("WEBHOOK_URL", "https://functions.yandexcloud.net/d4e2ojv9nmgbbil7ocf7")
    
    # Проверяем текущий вебхук
    get_webhook_info_url = f"https://api.telegram.org/bot{bot_token}/getWebhookInfo"
    response = requests.get(get_webhook_info_url)
    
    if response.status_code == 200:
        webhook_info = response.json()
        print("Current webhook info:")
        print(json.dumps(webhook_info, indent=2))
        
        # Проверяем, совпадает ли URL вебхука
        current_webhook_url = webhook_info.get("result", {}).get("url")
        if current_webhook_url == webhook_url:
            print("Webhook URL is correctly set")
        else:
            print(f"Webhook URL mismatch. Expected: {webhook_url}, Actual: {current_webhook_url}")
    else:
        print(f"Failed to get webhook info. Status code: {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    test_webhook()