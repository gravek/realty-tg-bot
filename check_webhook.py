import os
import json
import requests
import sys

def check_webhook(bot_token):
    """
    Проверяет текущую конфигурацию вебхука для бота
    """
    if not bot_token:
        print("Ошибка: Не указан токен бота")
        return False
    
    try:
        # Получаем информацию о вебхуке
        get_webhook_info_url = f"https://api.telegram.org/bot{bot_token}/getWebhookInfo"
        response = requests.get(get_webhook_info_url, timeout=10)
        
        if response.status_code == 200:
            webhook_info = response.json()
            print("Текущая конфигурация вебхука:")
            print(json.dumps(webhook_info, indent=2, ensure_ascii=False))
            
            # Проверяем наличие ошибок
            if webhook_info.get("ok") == False:
                print(f"Ошибка API: {webhook_info.get('description')}")
                return False
            
            result = webhook_info.get("result", {})
            url = result.get("url")
            if url:
                print(f"Вебхук установлен на URL: {url}")
                return True
            else:
                print("Вебхук не установлен")
                return False
        else:
            print(f"Ошибка при получении информации о вебхуке. Код ответа: {response.status_code}")
            print(response.text)
            return False
    except Exception as e:
        print(f"Ошибка при проверке вебхука: {e}")
        return False

def set_webhook(bot_token, webhook_url):
    """
    Устанавливает вебхук для бота
    """
    if not bot_token or not webhook_url:
        print("Ошибка: Не указан токен бота или URL вебхука")
        return False
    
    try:
        set_webhook_url = f"https://api.telegram.org/bot{bot_token}/setWebhook"
        data = {
            "url": webhook_url,
            "allowed_updates": ["message", "callback_query"]
        }
        
        response = requests.post(set_webhook_url, json=data, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            if result.get("ok"):
                print(f"Вебхук успешно установлен на URL: {webhook_url}")
                return True
            else:
                print(f"Ошибка установки вебхука: {result.get('description')}")
                return False
        else:
            print(f"Ошибка при установке вебхука. Код ответа: {response.status_code}")
            print(response.text)
            return False
    except Exception as e:
        print(f"Ошибка при установке вебхука: {e}")
        return False

if __name__ == "__main__":
    # Получаем токен бота из аргументов командной строки или переменной окружения
    bot_token = None
    if len(sys.argv) > 1:
        bot_token = sys.argv[1]
    else:
        bot_token = os.environ.get("BOT_TOKEN")
    
    if not bot_token:
        print("Укажите токен бота через аргумент командной строки или переменную окружения BOT_TOKEN")
        sys.exit(1)
    
    # Проверяем текущую конфигурацию вебхука
    print("Проверка текущей конфигурации вебхука...")
    check_webhook(bot_token)
    
    # Если нужно установить вебхук, раскомментируйте следующие строки и укажите правильный URL
    # webhook_url = "https://functions.yandexcloud.net/d4e2ojv9nmgbbil7ocf7"
    # print(f"Установка вебхука на URL: {webhook_url}")
    # set_webhook(bot_token, webhook_url)