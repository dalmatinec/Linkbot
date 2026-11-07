import os

from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
OWNER_IDS = {int(x) for x in os.getenv("OWNER_IDS", "").replace(" ", "").split(",") if x}

API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")

DATA_DIR = os.getenv("DATA_DIR", "data")
DB_PATH = os.path.join(DATA_DIR, "linkbot.db")
SESSION = os.path.join(DATA_DIR, "userbot")

TZ_OFFSET = int(os.getenv("TZ_OFFSET", "5"))  # часовой пояс для отображения и тихих часов
