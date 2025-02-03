# NASDAQ Telegram Bot

A Telegram bot that fetches and delivers NASDAQ-related news articles in Russian. The bot automatically translates news from English to Russian and sends them to a specified Telegram channel or chat.

## Features

- Fetches latest NASDAQ-related news using NewsAPI
- Automatically translates news from English to Russian
- Formats news articles for better readability
- Supports both direct messages and channel posting
- Configurable via environment variables

## Prerequisites

- Python 3.9 or higher
- Telegram Bot Token (from [@BotFather](https://t.me/botfather))
- NewsAPI Key (from [NewsAPI.org](https://newsapi.org))
- Telegram Channel/Chat ID

## Environment Variables

The following environment variables are required:

- `TELEGRAM_TOKEN`: Your Telegram bot token
- `TELEGRAM_CHAT_ID`: Your channel or chat ID (numeric format)
- `NEWSAPI_KEY`: Your NewsAPI.org API key

## Local Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/nasdaq-telegram-bot.git
cd nasdaq-telegram-bot
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the bot:
```bash
python bot.py
```

## Docker Deployment

### Build the Image
```bash
docker build -t nasdaq-telegram-bot .
```

### Run with Docker
```bash
docker run -d \
  -e TELEGRAM_TOKEN=<YOUR_TOKEN> \
  -e TELEGRAM_CHAT_ID=<YOUR_CHAT_ID> \
  -e NEWSAPI_KEY=<YOUR_NEWSAPI_KEY> \
  nasdaq-telegram-bot
```

## Channel Setup

1. Create a Telegram channel if you haven't already
2. Add your bot as an administrator to the channel
3. Get the channel ID by:
   - Forwarding a message from your channel to [@userinfobot](https://t.me/userinfobot)
   - Looking for 'Forwarded from chat #<number>' in the response
   - Use that number (including the minus sign) as your TELEGRAM_CHAT_ID

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.