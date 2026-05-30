import os
from dotenv import load_dotenv
load_dotenv(override=True)
GUILD_ID = int(os.getenv("GUILD_ID"))
MIDMAN_CHANNEL_ID = int(os.getenv("MIDMAN_CHANNEL_ID"))
TICKET_CATEGORY_ID = int(os.getenv("TICKET_CATEGORY_ID"))
ADMIN_ROLE_ID = int(os.getenv("ADMIN_ROLE_ID"))
TRANSCRIPT_CHANNEL_ID = int(os.getenv("TRANSCRIPT_CHANNEL_ID"))
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID"))
STORE_NAME = os.getenv("STORE_NAME", "Cellyn Store")
BACKUP_CHANNEL_ID = int(os.getenv('BACKUP_CHANNEL_ID'))
ERROR_LOG_CHANNEL_ID = int(os.getenv('ERROR_LOG_CHANNEL_ID'))
# Log channel for Vilog (optional; historically documented but not always set)
VILOG_CHANNEL_ID = int(os.getenv('VILOG_CHANNEL_ID', 0))
# Catalog/service channel for Vilog orders
VILOG_CATALOG_CHANNEL_ID = int(os.getenv('VILOG_CATALOG_CHANNEL_ID', '1493576431718895677'))
SELFROLES_CHANNEL_ID = int(os.getenv('SELFROLES_CHANNEL_ID'))
ROBUX_CATALOG_CHANNEL_ID = int(os.getenv('ROBUX_CATALOG_CHANNEL_ID'))
DANA_NUMBER = os.getenv('DANA_NUMBER', '-')
BCA_NUMBER = os.getenv('BCA_NUMBER', '-')
ML_CATALOG_CHANNEL_ID = int(os.getenv('ML_CATALOG_CHANNEL_ID'))

INVITE_REWARD_CHANNEL_ID = int(os.getenv('INVITE_REWARD_CHANNEL_ID', '1482464579085799435'))
AUTOPOSTER_TOKEN = os.getenv('AUTOPOSTER_TOKEN', '')
