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
# Channel auto-reply layanan "lainnya": member ketik kata kunci -> bot balas item + harga + S&K
LAINNYA_AUTOREPLY_CHANNEL_ID = int(os.getenv('LAINNYA_AUTOREPLY_CHANNEL_ID', '1508564472141447389'))
# Channel publikasi ulasan/rating member (dipakai sistem reviews)
TESTIMONI_CHANNEL_ID = int(os.getenv('TESTIMONI_CHANNEL_ID', 0))
# Role badge untuk reviewer aktif (opsional; 0 = nonaktif). Diberikan otomatis
# saat member mencapai ambang jumlah rating tertentu.
REVIEWER_BADGE_ROLE_ID = int(os.getenv('REVIEWER_BADGE_ROLE_ID', 0))
REVIEWER_BADGE_THRESHOLD = int(os.getenv('REVIEWER_BADGE_THRESHOLD', 3))
# Channel tempat panel klaim garansi (tombol). 0 = nonaktif.
WARRANTY_CHANNEL_ID = int(os.getenv('WARRANTY_CHANNEL_ID', 0))
# Channel laporan harian otomatis (omzet & rating). 0 = nonaktif.
DAILY_REPORT_CHANNEL_ID = int(os.getenv('DAILY_REPORT_CHANNEL_ID', '1476351037412610048'))

INVITE_REWARD_CHANNEL_ID = int(os.getenv('INVITE_REWARD_CHANNEL_ID', '1482464579085799435'))
AUTOPOSTER_TOKEN = os.getenv('AUTOPOSTER_TOKEN', '')


# Batas maksimal tiket AKTIF per member untuk SETIAP layanan
# (Midman, ML, Robux, GP, Lainnya, JualBeli, Vilog). Hitungannya per-layanan.
MAX_TICKETS_PER_SERVICE = int(os.getenv('MAX_TICKETS_PER_SERVICE', 5))



# Masa garansi default (hari) untuk produk TANPA durasi langganan di namanya
# (mis. Robux, diamond). Produk langganan ("... 1 Bulan") garansinya mengikuti
# durasi langganan. Dipakai fitur garansi pintar.
WARRANTY_DEFAULT_DAYS = int(os.getenv('WARRANTY_DEFAULT_DAYS', 7))

# Berapa hari SEBELUM langganan habis bot mengirim DM follow-up perpanjangan.
SUB_FOLLOWUP_LEAD_DAYS = int(os.getenv('SUB_FOLLOWUP_LEAD_DAYS', 3))



# Channel ADMIN untuk insight pelanggan saat tiket dibuka (0 = pakai LOG_CHANNEL_ID).
# Data belanja member sengaja dikirim ke channel admin, bukan ke channel tiket.
CUSTOMER_INSIGHT_CHANNEL_ID = int(os.getenv('CUSTOMER_INSIGHT_CHANNEL_ID', 0))
