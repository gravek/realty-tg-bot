import json
import os
from telegram import Bot
from openai import OpenAI
import asyncio

# Инициализация клиентов
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
ASSISTANT_ID = os.getenv('OPENAI_ASSISTANT_ID')
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

async def process_message(chat_id, message_text, message_id):
    bot = Bot(token=BOT_TOKEN)
    try:
        await bot.send_chat_action(chat_id=chat_id, action='typing')

        # Создаём тред
        thread = client.beta.threads.create(
            messages=[{"role": "user", "content": message_text}]
        )

        # Запускаем ассистента
        run = client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=ASSISTANT_ID
        )

        # Ждём завершения (простой polling)
        import time
        while True:
            run_status = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
            if run_status.status in ['completed', 'failed', 'cancelled']:
                break
            time.sleep(1)

        if run_status.status == 'failed':
            response = "Извини, не удалось обработать запрос."
        else:
            messages = client.beta.threads.messages.list(thread_id=thread.id)
            response = messages.data[0].content[0].text.value

        await bot.send_message(
            chat_id=chat_id,
            text=response,
            reply_to_message_id=message_id
        )
        return {"status": "ok"}

    except Exception as e:
        error_msg = f"Ошибка: {str(e)}"
        print(error_msg)
        await bot.send_message(
            chat_id=chat_id,
            text=f"Произошла ошибка: {str(e)}",
            reply_to_message_id=message_id
        )
        return {"status": "error", "message": str(e)}

# === Vercel Handler ===
def handler(event, context=None):
    try:
        # Парсим тело запроса
        body = event.get('body')
        if not body:
            return {
                'statusCode': 400,
                'body': json.dumps({"status": "error", "message": "Empty body"})
            }

        # Если тело в base64 (Vercel может так присылать)
        import base64
        if event.get('isBase64Encoded', False):
            body = base64.b64decode(body).decode('utf-8')

        update = json.loads(body)

        # Проверяем, есть ли сообщение
        if 'message' not in update or 'text' not in update['message']:
            return {
                'statusCode': 200,
                'body': json.dumps({"status": "no message"})
            }

        chat_id = update['message']['chat']['id']
        text = update['message']['text']
        message_id = update['message']['message_id']

        # Запускаем асинхронную обработку
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(process_message(chat_id, text, message_id))
        loop.close()

        return {
            'statusCode': 200,
            'body': json.dumps(result)
        }

    except json.JSONDecodeError as e:
        return {
            'statusCode': 400,
            'body': json.dumps({"status": "error", "message": f"Invalid JSON: {str(e)}"})
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({"status": "error", "message": str(e)})
        }

# Для Vercel
def telegram_webhook(event, context):
    return handler(event, context)
