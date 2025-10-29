# Realty Telegram Bot

A Telegram bot that uses OpenAI's Assistant API to respond to messages through GitHub Actions.


## Features

- Handles Telegram messages through webhooks
- Integrates with OpenAI Assistant API
- Shows typing indicator while processing
- Supports markdown formatting in responses


## Setup

1. Create a new Telegram bot through [@BotFather](https://t.me/botfather) and get the bot token.

2. Set up repository secrets in GitHub:
   - `TELEGRAM_BOT_TOKEN`: Your Telegram bot token
   - `OPENAI_API_KEY`: Your OpenAI API key
   - `OPENAI_ASSISTANT_ID`: ID of your OpenAI assistant

3. Set up webhook for your Telegram bot:
   ```bash
   curl -F "url=<your-github-actions-webhook-url>" https://api.telegram.org/bot<your-bot-token>/setWebhook
   ```

## Required Environment Variables

```
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
OPENAI_API_KEY=your_openai_api_key
OPENAI_ASSISTANT_ID=your_assistant_id
```
