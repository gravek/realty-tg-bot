from http.server import BaseHTTPRequestHandler
import json
import os
from telegram import Bot
from openai import OpenAI
import asyncio
import sys

# Initialize clients
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
ASSISTANT_ID = os.getenv('OPENAI_ASSISTANT_ID')

async def process_message(bot, chat_id, message_text, message_id):
    try:
        # Send typing action
        await bot.send_chat_action(chat_id=chat_id, action='typing')
        
        # Create OpenAI thread
        thread = client.beta.threads.create(
            messages=[{"role": "user", "content": message_text}]
        )
        
        # Run assistant
        run = client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=ASSISTANT_ID
        )
        
        # Get response
        messages = client.beta.threads.messages.list(thread_id=thread.id)
        if messages.data:
            response = messages.data[0].content[0].text.value
        else:
            response = "Sorry, I couldn't generate a response."
            
        # Send response
        await bot.send_message(
            chat_id=chat_id,
            text=response,
            reply_to_message_id=message_id
        )
        
    except Exception as e:
        error_message = f"Error processing message: {str(e)}"
        print(error_message, file=sys.stderr)
        await bot.send_message(
            chat_id=chat_id,
            text=f"Sorry, an error occurred: {str(e)}",
            reply_to_message_id=message_id
        )

class handler(BaseHTTPRequestHandler):
    async def handle_telegram_update(self, update_data):
        try:
            bot = Bot(token=os.getenv('TELEGRAM_BOT_TOKEN'))
            
            # Check if we have a message
            if 'message' in update_data and 'text' in update_data['message']:
                chat_id = update_data['message']['chat']['id']
                message_text = update_data['message']['text']
                message_id = update_data['message']['message_id']
                
                await process_message(bot, chat_id, message_text, message_id)
                return {"status": "ok"}
            
            return {"status": "no message found"}
            
        except Exception as e:
            print(f"Error in handle_telegram_update: {str(e)}", file=sys.stderr)
            return {"status": "error", "message": str(e)}

    def do_POST(self):
        try:
            # Read request body
            content_length = int(self.headers['Content-Length'])
            request_body = self.rfile.read(content_length).decode('utf-8')
            update_data = json.loads(request_body)
            
            # Process update
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(self.handle_telegram_update(update_data))
            
            # Send response
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(result).encode('utf-8'))
            
        except Exception as e:
            print(f"Error in do_POST: {str(e)}", file=sys.stderr)
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode('utf-8'))

    def do_GET(self):
        # Simple health check
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({"status": "healthy"}).encode('utf-8'))
