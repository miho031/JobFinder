import os
import requests
from dotenv import load_dotenv

load_dotenv()

token = os.getenv("TELEGRAM_BOT_TOKEN")

url = f"https://api.telegram.org/bot{token}/getUpdates"

response = requests.get(url, timeout=10)
response.raise_for_status()

print(response.json())
