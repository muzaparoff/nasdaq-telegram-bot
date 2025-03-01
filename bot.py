import os
import time
import logging
import requests
import yfinance as yf
from telegram import Bot
from googletrans import Translator
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Configure logging with stream handler for better Docker container visibility
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)
logger.propagate = True

# Environment variables for configuration
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")  # Your channel or chat ID    
NEWSAPI_KEY = os.environ.get("NEWSAPI_KEY")

if not all([TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, NEWSAPI_KEY]):
    raise ValueError("Missing required environment variables. Please set TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, and NEWSAPI_KEY")

# Format chat ID properly for public channels
if TELEGRAM_CHAT_ID.startswith('@'):    
    print("\nError: Channel username format is not supported.\nTo get the correct channel ID:\n1. Forward a message from your channel to @userinfobot\n2. Look for 'Forwarded from chat #<number>' in the response\n3. Use that number (including the minus sign) as your TELEGRAM_CHAT_ID\n4. Ensure the bot is added as an administrator to the channel with posting permissions\n")
    raise ValueError("Invalid TELEGRAM_CHAT_ID format. Please use numeric channel ID instead of channel username.")

# Ensure proper format for channel ID
try:
    # Convert to integer to validate format
    int(TELEGRAM_CHAT_ID)
    # Add -100 prefix if needed for public channels
    if not TELEGRAM_CHAT_ID.startswith('-100'):
        if TELEGRAM_CHAT_ID.startswith('-'):
            TELEGRAM_CHAT_ID = f"-100{TELEGRAM_CHAT_ID[1:]}"
        else:
            TELEGRAM_CHAT_ID = f"-100{TELEGRAM_CHAT_ID}"
    print(f"\nUsing channel ID: {TELEGRAM_CHAT_ID}")
    print("Important: Please verify the following:\n1. The bot has been added to the channel\n2. The bot has been promoted to administrator\n3. The bot has 'Post Messages' permission enabled\n")
except ValueError:
    raise ValueError("Invalid TELEGRAM_CHAT_ID format. Channel ID must be a numeric value.")

bot = Bot(token=TELEGRAM_TOKEN)
translator = Translator()

# List of major S&P 500 companies to track
TRACKED_COMPANIES = [
    # Technology
    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NVDA', 'AVGO', 'CSCO', 'ADBE', 'CRM',
    # Finance
    'BRK-B', 'JPM', 'V', 'MA', 'BAC', 'WFC', 'GS', 'MS', 'BLK', 'C',
    # Healthcare
    'UNH', 'JNJ', 'LLY', 'PFE', 'MRK', 'ABT', 'TMO', 'DHR', 'BMY', 'ABBV',
    # Consumer
    'PG', 'KO', 'PEP', 'COST', 'WMT', 'MCD', 'DIS', 'HD', 'NKE', 'SBUX',
    # Energy
    'XOM', 'CVX', 'COP', 'SLB', 'EOG'
]

# Configure retry strategy for requests
retry_strategy = Retry(
    total=3,  # number of retries
    backoff_factor=1,  # wait 1, 2, 4 seconds between retries
    status_forcelist=[429, 500, 502, 503, 504]  # HTTP status codes to retry on
)
http_adapter = HTTPAdapter(max_retries=retry_strategy)
session = requests.Session()
session.mount('http://', http_adapter)
session.mount('https://', http_adapter)

def fetch_yahoo_finance_news():
    logger.info("Starting to fetch news from Yahoo Finance")
    articles = []
    retry_delay = 2
    max_retries = 3
    
    for symbol in TRACKED_COMPANIES:
        logger.info(f"Fetching news for {symbol}")
        retries = 0
        while retries < max_retries:
            try:
                stock = yf.Ticker(symbol)
                news = stock.news
                if news and isinstance(news, list):
                    for item in news:
                        if not isinstance(item, dict):
                            logger.warning(f"Invalid news item format for {symbol}")
                            continue
                            
                        summary = item.get("summary", "")
                        if not summary:
                            logger.debug(f"Empty summary for news item from {symbol}")
                            continue
                            
                        article = {
                            "source": {"name": "Yahoo Finance"},
                            "title": item.get("title", "").strip(),
                            "description": summary.strip(),
                            "content": summary.strip(),
                            "publishedAt": item.get("providerPublishTime", "")
                        }
                        
                        if article["title"] and (article["description"] or article["content"]):
                            articles.append(article)
                            logger.debug(f"Added article: {article['title']}")
                    break
                else:
                    raise ValueError("Invalid news data format")
                
            except Exception as e:
                retries += 1
                logger.error(f"Error fetching Yahoo Finance data for {symbol}: {str(e)}")
                if retries < max_retries:
                    logger.info(f"Attempt {retries}/{max_retries} failed for {symbol}. Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    retry_delay = min(retry_delay * 2, 30)
                else:
                    logger.error(f"Failed to fetch Yahoo Finance data for {symbol} after {max_retries} attempts")
    
    logger.info(f"Completed Yahoo Finance fetch with {len(articles)} articles")
    return articles

def fetch_nasdaq_news():
    """
    Fetches recent news for S&P 500 companies using NewsAPI.org with enhanced sources.
    Implements optimized rate limiting and retry logic with improved query complexity.
    """
    articles = []
    url = "https://newsapi.org/v2/everything"
    
    # Enhanced list of financial news sources
    financial_sources = [
        'Bloomberg', 'Reuters', 'CNBC', 'WSJ', 'MarketWatch',
        'Financial Times', 'Forbes', 'Business Insider', 'The Economist',
        'Seeking Alpha', 'Investing.com', 'TheStreet', 'Barron\'s',
        'Motley Fool', 'Zacks', 'Benzinga'
    ]
    sources_query = ' OR '.join([f'source:"{source}"' for source in financial_sources])
    
    # More conservative batch size and retry settings
    batch_size = 1  # Reduced to 1 company per request to minimize rate limiting
    max_retries = 5
    base_delay = 120  # Increased base delay between requests to 120 seconds
    
    # Additional market-related keywords for better news coverage
    market_keywords = [
        'stock', 'market', 'earnings', 'trading', 'investment',
        'shares', 'price', 'financial', 'company', 'investor'
    ]
    market_query = ' OR '.join(market_keywords)
    
    for i in range(0, len(TRACKED_COMPANIES), batch_size):
        company_batch = TRACKED_COMPANIES[i:i + batch_size]
        company_query = ' OR '.join(company_batch)
        
        params = {
            "q": f"({company_query}) AND ({market_query}) AND ({sources_query})",
            "sortBy": "publishedAt",
            "language": "en",
            "pageSize": 50,  # Reduced for better rate limit management
            "apiKey": NEWSAPI_KEY
        }
        
        retries = 0
        while retries < max_retries:
            try:
                response = session.get(url, params=params, timeout=60)
                
                if response.status_code == 200:
                    newsapi_articles = response.json().get("articles", [])
                    for article in newsapi_articles:
                        title = article.get("title", "").strip()
                        description = article.get("description", "").strip()
                        content = article.get("content", "").strip()
                        
                        if title and (description or content):
                            articles.append({
                                "source": article.get("source", {"name": "Unknown Source"}),
                                "title": title,
                                "description": description,
                                "content": content,
                                "publishedAt": article.get("publishedAt", ""),
                                "urlToImage": article.get("urlToImage", ""),
                                "url": article.get("url", "")
                            })
                    break
                    
                elif response.status_code == 429:
                    retry_after = int(response.headers.get('Retry-After', base_delay))
                    logger.warning(f"NewsAPI rate limit reached, waiting {retry_after} seconds...")
                    time.sleep(retry_after + (base_delay * retries))  # Add exponential backoff
                else:
                    logger.error(f"Error fetching news from NewsAPI: {response.text}")
                    time.sleep(base_delay * (2 ** retries))
                    if response.status_code >= 500:  # Server errors need longer cooldown
                        time.sleep(base_delay * 3)
                    
            except Exception as e:
                logger.error(f"Error in NewsAPI request: {str(e)}")
                time.sleep(base_delay * (2 ** retries))
                
            retries += 1
            if retries == max_retries:
                logger.error(f"Failed to fetch news for batch after {max_retries} attempts")
                time.sleep(base_delay * 3)  # Longer cooldown after max retries
        
        if i + batch_size < len(TRACKED_COMPANIES):
            # Increase delay between batches to avoid rate limits
            time.sleep(base_delay)
    
    articles.sort(key=lambda x: x.get('publishedAt', ''), reverse=True)
    return articles[:50]

def format_news(article):
    """
    Format a single news article:
      - First line: Source name with bold headline
      - Following lines: Unique sentences prefixed with dash (-)
      - Maximum 15 sentences, no minimum requirement
    """
    from nltk.tokenize import sent_tokenize
    
    # Extract article components with better validation
    source = article.get("source", {})
    if not isinstance(source, dict):
        print("Invalid source format")
        return None
    source_name = source.get("name", "Unknown Source")
    
    title = article.get("title", "").strip()
    if not title:
        print("Article missing title")
        return None
    
    description = article.get("description", "").strip()
    content = article.get("content", "").strip()
    
    # Ensure we have at least some content
    if not (description or content):
        print("Article missing both description and content")
        return None
    
    # Clean and combine content more effectively
    content_parts = []
    if description:
        content_parts.append(description.strip())
    if content:
        # Remove common truncation markers and clean content
        cleaned_content = content.split('[+')[0].split('…')[0].split('...')[0].strip()
        if cleaned_content:
            content_parts.append(cleaned_content)
    
    # Combine all parts with proper sentence separation
    full_content = ". ".join(content_parts)
    if not full_content.endswith(('.', '!', '?')):
        full_content += "."
    
    try:
        # Get all sentences
        sentences = sent_tokenize(full_content)
        
        # Remove duplicates while preserving order
        unique_sentences = []
        seen = set()
        for sentence in sentences:
            # Clean and normalize the sentence
            cleaned = sentence.strip()
            if not cleaned:
                continue
            # Allow sentences of reasonable length
            if len(cleaned) < 20:  # Increased minimum length for more meaningful content
                continue
            # Filter out common formatting artifacts and unwanted patterns
            if any(marker in cleaned for marker in ['[', ']', '{', '}', '<', '>', '|']):
                continue
            if cleaned.startswith(('http', 'www', '//', '@')):
                continue
            normalized = cleaned.lower()
            if normalized not in seen and not any(word in normalized for word in ['subscribe', 'click here', 'read more']):
                seen.add(normalized)
                unique_sentences.append(cleaned)
        
        # Take up to 15 complete sentences, excluding those too similar to title
        formatted_sentences = []
        title_lower = title.lower()
        
        for sentence in unique_sentences:
            # Skip sentences that are too similar to the title
            if sentence.lower() == title_lower or \
               (len(sentence) >= 20 and title_lower in sentence.lower()):  # Increased length threshold and removed reverse check
                continue
                
            # Accept sentences with more types of ending punctuation
            if sentence[-1] in ['.', '!', '?', ':', ';'] or len(sentence) >= 30:  # Allow longer sentences without strict punctuation
                formatted_sentences.append(sentence)
            if len(formatted_sentences) >= 15:
                break
        
        # Format the message with source name and headline (without markdown)
        message = ""
        
        # Add image if available
        if article.get("urlToImage"):
            message += f"{article['urlToImage']}\n\n"
            
        message += f"{source_name}: {title}\n\n"
        
        # Add all sentences with line breaks between them (up to 15)
        for i, sentence in enumerate(formatted_sentences[:15]):
            message += f"– {sentence}\n"
            
        # Add source URL if available
        if article.get("url"):
            message += f"\nSource: {article['url']}"
            
        # Add channel name with @ symbol after a blank line
        message += "\n\n@nasdaq_news"
        
        # Validate final message
        if not message or len(message.strip()) < 50:  # Ensure minimum content length
            print("Generated message too short")
            return None
            
        return message
        
    except Exception as e:
        print(f"Error formatting news: {str(e)}")
        return None

def translate_to_russian(text):
    """
    Translate the provided text to Russian.
    Returns None if translation fails to indicate error.
    """
    if not text or not isinstance(text, str):
        print("Translation error: Invalid input text")
        return None
    
    try:
        translation = translator.translate(text, dest='ru')
        if translation and translation.text:
            return translation.text
        print("Translation error: Empty translation result")
        return None
    except Exception as e:
        print(f"Translation error: {str(e)}")
        return None

def send_news():
    logger.info("Starting news sending process")
    articles = fetch_nasdaq_news()
    if not articles:
        logger.warning("No articles fetched.")
        return

    sent_count = 0
    for i, article in enumerate(articles):
        try:
            logger.info(f"Processing article {i+1} of {len(articles)}")
            message = format_news(article)
            if not message:
                logger.warning(f"Skipping article {i+1}: Could not format message")
                continue

            logger.info("Translating message to Russian")
            message_ru = translate_to_russian(message)
            if not message_ru:
                logger.warning(f"Skipping article {i+1}: Translation failed")
                continue

            logger.info(f"Sending message to chat {TELEGRAM_CHAT_ID}")
            bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message_ru)
            sent_count += 1
            logger.info(f"Successfully sent message {sent_count}")

            if i < len(articles) - 1:
                logger.info("Waiting 30 seconds before sending next article...")
                time.sleep(30)

        except Exception as e:
            logger.error(f"Error processing article {i+1}: {str(e)}")
            continue

    logger.info(f"Finished sending news. Successfully sent {sent_count} articles.")

if __name__ == "__main__":
    send_news()