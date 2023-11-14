import os

import requests
from dotenv import find_dotenv, load_dotenv

load_dotenv(
    find_dotenv(filename=".env.local", raise_error_if_not_found=True),
    override=True,
)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
print(TELEGRAM_TOKEN, CHAT_ID)
base_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/"


def send_message(msg: str):
    url = f"{base_url}sendMessage?chat_id={CHAT_ID}&text={msg}"
    response = requests.get(url)
    print(response)
    if response.status_code != 200:
        raise Exception("Telegram API Error")
