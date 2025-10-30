import os
import json
from http.server import BaseHTTPRequestHandler
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from openai import OpenAI

# Initialize the OpenAI client
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
ASSISTANT_ID = os.getenv('OPENAI_ASSISTANT_ID')

async def handle_message(update: Update):
    bot = Bot(token=os.getenv('TELEGRAM_BOT_TOKEN'))
    chat_id = update.message.chat_id
    message_id = update.message.message_id
    user_message = update.message.text

    # Send typing action
    await bot.send_chat_action(chat_id=chat_id, action='typing')

    try:
        # Create a new thread with the user's message
        thread = client.beta.threads.create(
            messages=[{
                "role": "user",
                "content": user_message
            }]
        )

        # Create a run with the assistant
        run = client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=ASSISTANT_ID
        )

        # Wait for completion and get messages
        messages = client.beta.threads.messages.list(thread_id=thread.id)
        assistant_message = messages.data[0].content[0].text.value

        # Send the response
        await bot.send_message(
            chat_id=chat_id,
            text=assistant_message,
            reply_to_message_id=message_id
        )

    except Exception as e:
        error_message = f"Sorry, an error occurred: {str(e)}"
        await bot.send_message(
            chat_id=chat_id,
            text=error_message,
            reply_to_message_id=message_id
        )

async def webhook(request_body):
    update = Update.de_json(request_body, None)
    if update and update.message:
        await handle_message(update)
    return {"status": "ok"}

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        request_body = self.rfile.read(content_length).decode('utf-8')
        
        # Process the update
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(webhook(json.loads(request_body)))
        
        # Send response
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(result).encode('utf-8'))
        return
