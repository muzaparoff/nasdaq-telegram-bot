# nasdaq-telegram-bot
## Install
```
pip install -r requirements.txt
'''
## Run
``` 
python main.py
'''

## Docker Build
'''
docker build -t nasdaq-telegram-bot .
'''

## Docker Run
'''
docker run -d -e TELEGRAM_TOKEN=<TOKEN> -e TELEGRAM_CHAT_ID=<CHAT_ID> nasdaq-telegram-bot