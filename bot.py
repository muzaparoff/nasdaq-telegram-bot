import os
import requests
from telegram import Bot
from googletrans import Translator

# Environment variables for configuration
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")  # Your channel or chat ID
NEWSAPI_KEY = os.environ.get("NEWSAPI_KEY")

if not all([TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, NEWSAPI_KEY]):
    raise ValueError("Missing required environment variables. Please set TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, and NEWSAPI_KEY")

# Format chat ID properly for public channels
if TELEGRAM_CHAT_ID.startswith('@'):
    # If it's a channel username, we need to get the channel ID first
    print("Please use channel ID instead of channel username. Channel ID should start with -100 for public channels.")
    raise ValueError("Invalid TELEGRAM_CHAT_ID format. Please use channel ID instead of channel username.")
elif not TELEGRAM_CHAT_ID.startswith('-100') and TELEGRAM_CHAT_ID.startswith('-'):
    TELEGRAM_CHAT_ID = f"-100{TELEGRAM_CHAT_ID[1:]}"
elif not TELEGRAM_CHAT_ID.startswith('-'):
    TELEGRAM_CHAT_ID = f"-100{TELEGRAM_CHAT_ID}"

bot = Bot(token=TELEGRAM_TOKEN)
translator = Translator()

def fetch_nasdaq_news():
    """
    Fetches recent Nasdaq-related news using NewsAPI.org.
    You need to sign up at https://newsapi.org for an API key.
    """
    url = "https://newsapi.org/v2/everything"
    params = {
        "q": "NASDAQ",  # search term
        "sortBy": "publishedAt",
        "language": "en",
        "apiKey": NEWSAPI_KEY
    }
    response = requests.get(url, params=params)
    if response.status_code == 200:
        articles = response.json().get("articles", [])
        return articles
    else:
        print("Error fetching news:", response.text)
        return []

def format_news(article):
    """
    Format a single news article:
      - Use the title as the topic (first sentence).
      - Create a summary (limit total to 10 sentences). For simplicity,
        we use title and description split into sentences.
    """
    from nltk.tokenize import sent_tokenize
    # Ensure you have nltk sentence tokenizer data downloaded:
    # In your setup, run: python -m nltk.downloader punkt

    title = article.get("title", "No Title")
    description = article.get("description", "")
    content = f"{title}. {description}"
    sentences = sent_tokenize(content)
    # Limit to 10 sentences maximum
    sentences = sentences[:10]
    # First sentence is treated as the topic title
    topic = sentences[0]
    summary = " ".join(sentences[1:]) if len(sentences) > 1 else ""
    return topic, summary

def translate_to_russian(text):
    """
    Translate the provided text to Russian.
    """
    try:
        translation = translator.translate(text, dest='ru')
        return translation.text
    except Exception as e:
        print("Translation error:", e)
        return text

def send_news():
    articles = fetch_nasdaq_news()
    if not articles:
        print("No articles fetched.")
        return

    for article in articles:
        topic, summary = format_news(article)
        # Translate both topic and summary to Russian
        topic_ru = translate_to_russian(topic)
        summary_ru = translate_to_russian(summary)
        message = f"*{topic_ru}*\n{summary_ru}"
        try:
            bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message, parse_mode='Markdown')
            print("Sent message:", topic_ru)
        except Exception as e:
            print("Error sending message:", e)

if __name__ == "__main__":
    send_news()