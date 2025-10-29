import os
import json
import asyncio
from telegram import Bot, Update
from telegram.constants import ParseMode
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

        # Get the assistant's response
        messages = client.beta.threads.messages.list(thread_id=thread.id)
        assistant_message = messages.data[0].content[0].text.value

        # Send the response back to Telegram
        await bot.send_message(
            chat_id=chat_id,
            text=assistant_message,
            reply_to_message_id=message_id,
            parse_mode=ParseMode.MARKDOWN
        )

    except Exception as e:
        error_message = f"Sorry, an error occurred: {str(e)}"
        await bot.send_message(
            chat_id=chat_id,
            text=error_message,
            reply_to_message_id=message_id
        )

def main():
    # Get the webhook data from GitHub Actions
    with open(os.environ['GITHUB_EVENT_PATH']) as f:
        event_data = json.load(f)
    
    # Convert webhook data to Telegram Update object
    update = Update.de_json(event_data, None)
    
    # Handle the message
    asyncio.run(handle_message(update))

if __name__ == "__main__":
    main()
