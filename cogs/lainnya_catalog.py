"""
cogs/lainnya_catalog.py
Data katalog produk "lainnya". MURNI DATA - tidak ada efek samping saat di-import.
Harga di sini hanya nilai AWAL; admin bisa ubah via admin panel.
"""

GROUP_ORDER = [
    "AI", "STREAMING", "MUSIK", "EDITING", "AKUN & STORAGE",
    "GAMING", "DISCORD", "SOCIAL MEDIA", "LAINNYA",
]

GROUP_EMOJI = {
    "AI": "<:emojigg_ai:1510724403627954256>",
    "STREAMING": "<:I_love_movies:1510722677051097239>",
    "MUSIK": "<:Music:1510720973656031232>",
    "EDITING": "<:SCM_canva:1485497715637883013>",
    "AKUN & STORAGE": "<:Dropbox:1510722076804124793>",
    "GAMING": "\U0001F3AE",
    "DISCORD": "<:Discord:1510719862396293390>",
    "SOCIAL MEDIA": "<:IconDribbble:1510721665284177940>",
    "LAINNYA": "\U0001F5C2",
}

CATEGORY_GROUP = {
    "CHATGPT": "AI", "GROK AI": "AI", "GEMINI AI": "AI",
    "BSTATION": "STREAMING", "YOUTUBE PREMIUM": "STREAMING", "VIU": "STREAMING",
    "AMAZON PRIME VIDEO": "STREAMING", "WETV": "STREAMING", "IQIYI": "STREAMING",
    "HBO MAX": "STREAMING", "VIDIO": "STREAMING",
    "SPOTIFY": "MUSIK", "APPLE MUSIC": "MUSIK",
    "ALIGHT MOTION": "EDITING", "REMINI": "EDITING", "CANVA": "EDITING", "CAPCUT": "EDITING",
    "GOOGLE DRIVE": "AKUN & STORAGE", "OUTLOOK": "AKUN & STORAGE",
    "GMAIL": "AKUN & STORAGE", "CLOUD PHONE": "AKUN & STORAGE",
    "RANDOM STEAM KEY": "GAMING", "XBOX GAMEPASS": "GAMING", "AKUN STEAM FRESH": "GAMING",
    "AKUN STEAM PREMIUM GAMES": "GAMING", "AKUN EPIC GAMES": "GAMING",
    "AKUN ROBLOX": "GAMING", "ROBUX GIFT CARD": "GAMING",
    "DISCORD NITRO": "DISCORD", "NITRO BOOST": "DISCORD", "NITRO BASIC": "DISCORD",
    "NITRO CODE": "DISCORD", "JASA BOOST SERVER": "DISCORD", "SUNTIK MEMBER": "DISCORD",
    "TOKEN DISCORD": "DISCORD", "QUEST ORBS": "DISCORD",
    "YOUTUBE SUBSCRIBER": "SOCIAL MEDIA", "YOUTUBE LIKES": "SOCIAL MEDIA",
    "YOUTUBE VIEWS": "SOCIAL MEDIA", "YOUTUBE SHORT": "SOCIAL MEDIA",
    "YOUTUBE LIVE VIEWERS": "SOCIAL MEDIA", "YOUTUBE JAM TAYANG": "SOCIAL MEDIA",
    "INSTAGRAM FOLLOWERS": "SOCIAL MEDIA", "INSTAGRAM LIKE": "SOCIAL MEDIA",
    "INSTAGRAM VIEWS": "SOCIAL MEDIA", "INSTAGRAM LIVE VIEWERS": "SOCIAL MEDIA",
    "TIKTOK FOLLOWERS": "SOCIAL MEDIA", "TIKTOK LIKE": "SOCIAL MEDIA",
    "TIKTOK VIEWS": "SOCIAL MEDIA", "TIKTOK SHARE": "SOCIAL MEDIA",
    "TIKTOK LIVE VIEWERS": "SOCIAL MEDIA",
}

def group_of(category: str) -> str:
    return CATEGORY_GROUP.get(category, "LAINNYA")

PRODUCTS = [
    ("ALIGHT MOTION", "ALIGHT MOTION PRO PRIVATE 1 Bulan", 11000),
    ("ALIGHT MOTION", "ALIGHT MOTION PRO PRIVATE 6 Bulan", 25000),
    ("ALIGHT MOTION", "ALIGHT MOTION PRO PRIVATE 1 Tahun", 35000),
    ("REMINI", "REMINI PRO SHARING 1 Bulan", 17000),
    ("REMINI", "REMINI PRO SHARING 6 Bulan", 75000),
    ("REMINI", "REMINI PRO SHARING 1 Tahun", 140000),
    ("REMINI", "REMINI PRO PRIVATE 1 Bulan", 24000),
    ("REMINI", "REMINI PRO PRIVATE 6 Bulan", 115000),
    ("REMINI", "REMINI PRO PRIVATE 1 Tahun", 220000),
    ("REMINI", "REMINI PRO+ PRIVATE 1 Bulan", 45000),
    ("REMINI", "REMINI PRO+ PRIVATE 6 Bulan", 245000),
    ("REMINI", "REMINI PRO+ PRIVATE 1 Tahun", 465000),
    ("CANVA", "CANVA PRO 1 Bulan", 10000),
    ("CANVA", "CANVA PRO 2 Bulan", 14000),
    ("CANVA", "CANVA PRO 3 Bulan", 17000),
    ("CANVA", "CANVA PRO 6 Bulan", 20000),
    ("CANVA", "CANVA PRO 1 Tahun", 26000),
    ("CANVA", "CANVA STUDENT 1 Tahun", 24000),
    ("CANVA", "CANVA PRO OWNER 1 Bulan", 15000),
    ("CANVA", "CANVA PRO OWNER 1 Tahun", 100000),
    ("CAPCUT", "CAPCUT PRO SHARING 1 Bulan", 40000),
    ("CAPCUT", "CAPCUT PRO SHARING 3 Bulan", 110000),
    ("CAPCUT", "CAPCUT PRO SHARING 6 Bulan", 215000),
    ("CAPCUT", "CAPCUT PRO SHARING 1 Tahun", 425000),
    ("CAPCUT", "CAPCUT PRO PRIVATE 1 Bulan", 70000),
    ("CAPCUT", "CAPCUT PRO PRIVATE 3 Bulan", 200000),
    ("CAPCUT", "CAPCUT PRO PRIVATE 6 Bulan", 395000),
    ("CAPCUT", "CAPCUT PRO PRIVATE 1 Tahun", 785000),
    ("CHATGPT", "CHATGPT GO 1 Bulan", 40000),
    ("CHATGPT", "CHATGPT GO 2 Bulan", 70000),
    ("CHATGPT", "CHATGPT GO 3 Bulan", 100000),
    ("CHATGPT", "CHATGPT PLUS 1 Bulan", 80000),
    ("CHATGPT", "CHATGPT PLUS 2 Bulan", 155000),
    ("CHATGPT", "CHATGPT PLUS 3 Bulan", 220000),
    ("CHATGPT", "CHATGPT BUSINESS 1 Bulan", 100000),
    ("CHATGPT", "CHATGPT BUSINESS 2 Bulan", 190000),
    ("CHATGPT", "CHATGPT BUSINESS 3 Bulan", 285000),
    ("GROK AI", "GROK AI PRO 1 Bulan", 30000),
    ("GEMINI AI", "GEMINI AI PRO 1 Bulan", 41000),
    ("GEMINI AI", "GEMINI AI PRO PRIVATE 4 Bulan", 70500),
    ("GEMINI AI", "GEMINI AI PRO PRIVATE 1 Tahun", 140000),
    ("BSTATION", "BSTATION PREMIUM SHARING 1 Bulan", 10000),
    ("BSTATION", "BSTATION PREMIUM SHARING 3 Bulan", 20000),
    ("BSTATION", "BSTATION PREMIUM SHARING 1 Tahun", 45000),
    ("BSTATION", "BSTATION PREMIUM PRIVATE 1 Bulan", 28000),
    ("BSTATION", "BSTATION PREMIUM PRIVATE 3 Bulan", 75000),
    ("BSTATION", "BSTATION PREMIUM PRIVATE 1 Tahun", 280000),
    ("YOUTUBE PREMIUM", "YOUTUBE PREMIUM ADMIN 1 Bulan", 20000),
    ("YOUTUBE PREMIUM", "YOUTUBE PREMIUM INVITE 1 Bulan", 10000),
    ("YOUTUBE PREMIUM", "YOUTUBE PREMIUM INVITE 6 Bulan", 35000),
    ("YOUTUBE PREMIUM", "YOUTUBE PREMIUM INVITE 1 Tahun", 62000),
    ("YOUTUBE PREMIUM", "YOUTUBE PREMIUM INDIVIDUAL 1 Bulan", 15000),
    ("YOUTUBE PREMIUM", "YOUTUBE PREMIUM INDIVIDUAL 6 Bulan", 63000),
    ("YOUTUBE PREMIUM", "YOUTUBE PREMIUM INDIVIDUAL 1 Tahun", 120000),
    ("VIU", "VIU PREMIUM SHARING 1 Bulan", 10000),
    ("VIU", "VIU PREMIUM SHARING 1 Tahun", 18000),
    ("VIU", "VIU PREMIUM PRIVATE 1 Bulan", 14000),
    ("VIU", "VIU PREMIUM PRIVATE 1 Tahun", 33000),
    ("VIU", "VIU PREMIUM+ 1 Bulan", 18000),
    ("VIU", "VIU PREMIUM+ 6 Bulan", 50000),
    ("VIU", "VIU PREMIUM+ 1 Tahun", 80000),
    ("AMAZON PRIME VIDEO", "AMAZON PRIME VIDEO SHARING 1 Bulan", 19000),
    ("AMAZON PRIME VIDEO", "AMAZON PRIME VIDEO SHARING 6 Bulan", 50000),
    ("AMAZON PRIME VIDEO", "AMAZON PRIME VIDEO SHARING 1 Tahun", 90000),
    ("AMAZON PRIME VIDEO", "AMAZON PRIME VIDEO PRIVATE 1 Bulan", 29000),
    ("AMAZON PRIME VIDEO", "AMAZON PRIME VIDEO PRIVATE 6 Bulan", 145000),
    ("AMAZON PRIME VIDEO", "AMAZON PRIME VIDEO PRIVATE 1 Tahun", 220000),
    ("WETV", "WETV VIP 1 DEVICE 1 Bulan", 18000),
    ("WETV", "WETV VIP 1 DEVICE 6 Bulan", 80000),
    ("WETV", "WETV VIP 1 DEVICE 1 Tahun", 125000),
    ("WETV", "WETV VIP 2 DEVICE 1 Bulan", 38000),
    ("WETV", "WETV VIP 2 DEVICE 6 Bulan", 200000),
    ("WETV", "WETV VIP 2 DEVICE 1 Tahun", 395000),
    ("WETV", "WETV COIN 25", 13000),
    ("IQIYI", "IQIYI VIP STANDARD 1 Bulan", 14000),
    ("IQIYI", "IQIYI VIP STANDARD 6 Bulan", 40000),
    ("IQIYI", "IQIYI VIP STANDARD 1 Tahun", 50000),
    ("IQIYI", "IQIYI VIP PREMIUM SHARING 1 Bulan", 19000),
    ("IQIYI", "IQIYI VIP PREMIUM SHARING 6 Bulan", 50000),
    ("IQIYI", "IQIYI VIP PREMIUM SHARING 1 Tahun", 60000),
    ("IQIYI", "IQIYI VIP PREMIUM PRIVATE 1 Bulan", 32000),
    ("IQIYI", "IQIYI VIP PREMIUM PRIVATE 6 Bulan", 165000),
    ("IQIYI", "IQIYI VIP PREMIUM PRIVATE 1 Tahun", 325000),
    ("HBO MAX", "HBO MAX STANDARD SHARING (per Bulan)", 23000),
    ("HBO MAX", "HBO MAX STANDARD PRIVATE (per Bulan)", 43000),
    ("HBO MAX", "HBO MAX ULTIMATE SHARING (per Bulan)", 28000),
    ("HBO MAX", "HBO MAX ULTIMATE PRIVATE (per Bulan)", 78000),
    ("VIDIO", "VIDIO PLATINUM PRIVATE TV ONLY 1 Tahun", 20000),
    ("VIDIO", "VIDIO PLATINUM SHARING MOBILE (per Bulan)", 25000),
    ("VIDIO", "VIDIO PLATINUM PRIVATE MOBILE (per Bulan)", 33000),
    ("VIDIO", "VIDIO PLATINUM SHARING ALL DEVICE (per Bulan)", 30000),
    ("VIDIO", "VIDIO PLATINUM PRIVATE ALL DEVICE (per Bulan)", 43000),
    ("SPOTIFY", "SPOTIFY PREMIUM INDIVIDUAL 1 Bulan", 28000),
    ("SPOTIFY", "SPOTIFY PREMIUM INDIVIDUAL 2 Bulan", 50000),
    ("SPOTIFY", "SPOTIFY PREMIUM INDIVIDUAL 3 Bulan", 60000),
    ("SPOTIFY", "SPOTIFY PREMIUM FAMILY 1 Bulan", 28000),
    ("SPOTIFY", "SPOTIFY PREMIUM FAMILY 2 Bulan", 53000),
    ("SPOTIFY", "SPOTIFY PREMIUM FAMILY 3 Bulan", 70000),
    ("SPOTIFY", "SPOTIFY PREMIUM PLATINUM 1 Bulan", 90000),
    ("SPOTIFY", "SPOTIFY PREMIUM PLATINUM 2 Bulan", 170000),
    ("SPOTIFY", "SPOTIFY PREMIUM PLATINUM 3 Bulan", 250000),
    ("APPLE MUSIC", "APPLE MUSIC AKUN BARU", 17000),
    ("APPLE MUSIC", "APPLE MUSIC PERPANJANG", 17500),
    ("GOOGLE DRIVE", "G-DRIVE AKUN BARU 100GB", 22000),
    ("GOOGLE DRIVE", "G-DRIVE AKUN BARU 300GB", 30000),
    ("GOOGLE DRIVE", "G-DRIVE AKUN BARU UNLIMITED", 45000),
    ("GOOGLE DRIVE", "G-DRIVE AKUN PRIBADI 100GB", 37000),
    ("GOOGLE DRIVE", "G-DRIVE AKUN PRIBADI UNLIMITED", 60000),
    ("OUTLOOK", "OUTLOOK (per pcs)", 2500),
    ("GMAIL", "GMAIL FRESH (per pcs)", 6000),
    ("RANDOM STEAM KEY", "RANDOM STEAM KEY BASIC", 15000),
    ("RANDOM STEAM KEY", "RANDOM STEAM KEY ELITE", 30000),
    ("RANDOM STEAM KEY", "RANDOM STEAM KEY LUXURY", 60000),
    ("XBOX GAMEPASS", "XBOX GAMEPASS CODE 2 Minggu", 40000),
    ("XBOX GAMEPASS", "XBOX GAMEPASS CODE 1 Bulan", 90000),
    ("XBOX GAMEPASS", "XBOX GAMEPASS CODE 3 Bulan", 220000),
    ("AKUN STEAM FRESH", "AKUN STEAM FRESH (Full Access)", 20000),
    ("AKUN STEAM PREMIUM GAMES", "STEAM PREMIUM - GTA V", 60000),
    ("AKUN STEAM PREMIUM GAMES", "STEAM PREMIUM - Outlast", 60000),
    ("AKUN STEAM PREMIUM GAMES", "STEAM PREMIUM - The Witcher 3", 60000),
    ("AKUN STEAM PREMIUM GAMES", "STEAM PREMIUM - Outlast 2", 60000),
    ("AKUN STEAM PREMIUM GAMES", "STEAM PREMIUM - Schedule 1", 60000),
    ("AKUN STEAM PREMIUM GAMES", "STEAM PREMIUM - Assetto Corsa", 60000),
    ("AKUN STEAM PREMIUM GAMES", "STEAM PREMIUM - FC 25", 60000),
    ("AKUN STEAM PREMIUM GAMES", "STEAM PREMIUM - Resident Evil 5", 60000),
    ("AKUN STEAM PREMIUM GAMES", "STEAM PREMIUM - Wallpaper Engine", 60000),
    ("AKUN STEAM PREMIUM GAMES", "STEAM PREMIUM - Cyberpunk", 60000),
    ("AKUN STEAM PREMIUM GAMES", "STEAM PREMIUM - Raft", 60000),
    ("AKUN STEAM PREMIUM GAMES", "STEAM PREMIUM - Hogwarts Legacy", 60000),
    ("AKUN STEAM PREMIUM GAMES", "STEAM PREMIUM - Dead By Daylight", 60000),
    ("AKUN EPIC GAMES", "AKUN EPIC GAMES 50-100 Games", 40000),
    ("AKUN EPIC GAMES", "AKUN EPIC GAMES 100-200 Games", 80000),
    ("AKUN EPIC GAMES", "AKUN EPIC GAMES 200-300 Games", 140000),
    ("AKUN EPIC GAMES", "AKUN EPIC GAMES 300+ Games", 230000),
    ("AKUN ROBLOX", "AKUN ROBLOX FRESH 13+", 16000),
    ("AKUN ROBLOX", "AKUN ROBLOX FRESH 21+", 25000),
    ("ROBUX GIFT CARD", "ROBUX GIFT CARD 50.000", 50000),
    ("ROBUX GIFT CARD", "ROBUX GIFT CARD 65.000", 60000),
    ("ROBUX GIFT CARD", "ROBUX GIFT CARD 100.000", 90000),
    ("NITRO BOOST", "NITRO BOOST VIA LOGIN 1 Bulan", 80000),
    ("NITRO BOOST", "NITRO BOOST VIA LOGIN 1 Tahun", 755000),
    ("NITRO BOOST", "NITRO BOOST VIA GIFT 1 Bulan", 90000),
    ("NITRO BOOST", "NITRO BOOST VIA GIFT 1 Tahun", 855000),
    ("NITRO BOOST", "NITRO BOOST PROMO 1 Bulan (Akun Customer)", 25000),
    ("NITRO BOOST", "NITRO BOOST PROMO 1 Bulan (Akun Seller)", 29000),
    ("NITRO BOOST", "NITRO BOOST PROMO 3 Bulan (Akun Customer)", 45000),
    ("NITRO BOOST", "NITRO BOOST PROMO 3 Bulan (Akun Seller)", 45000),
    ("NITRO BASIC", "NITRO BASIC VIA LOGIN 1 Bulan", 35000),
    ("NITRO BASIC", "NITRO BASIC VIA LOGIN 1 Tahun", 305000),
    ("NITRO BASIC", "NITRO BASIC VIA GIFT 1 Bulan", 40000),
    ("NITRO BASIC", "NITRO BASIC VIA GIFT 1 Tahun", 355000),
    ("NITRO CODE", "NITRO CODE UNCHECKED 500 Codes", 6000),
    ("NITRO CODE", "NITRO CODE UNCHECKED 1000 Codes", 7000),
    ("NITRO CODE", "NITRO CODE UNCHECKED 2000 Codes", 9000),
    ("NITRO CODE", "NITRO CODE UNCHECKED 3000 Codes", 11000),
    ("NITRO CODE", "NITRO CODE UNCHECKED 4000 Codes", 13000),
    ("NITRO CODE", "NITRO CODE UNCHECKED 5000 Codes", 15000),
    ("JASA BOOST SERVER", "BOOST SERVER 1 BULAN - 1 BOOST", 15000),
    ("JASA BOOST SERVER", "BOOST SERVER 1 BULAN - LEVEL 1 (2 BOOST)", 25000),
    ("JASA BOOST SERVER", "BOOST SERVER 1 BULAN - LEVEL 2 (8 BOOST)", 70000),
    ("JASA BOOST SERVER", "BOOST SERVER 1 BULAN - LEVEL 3 (14 BOOST)", 30000),
    ("JASA BOOST SERVER", "BOOST SERVER 3 BULAN - 1 BOOST", 30000),
    ("JASA BOOST SERVER", "BOOST SERVER 3 BULAN - LEVEL 1 (2 BOOST)", 40000),
    ("JASA BOOST SERVER", "BOOST SERVER 3 BULAN - LEVEL 2 (8 BOOST)", 150000),
    ("JASA BOOST SERVER", "BOOST SERVER 3 BULAN - LEVEL 3 (14 BOOST)", 220000),
    ("SUNTIK MEMBER", "MEMBER OFFLINE 250", 25000),
    ("SUNTIK MEMBER", "MEMBER OFFLINE 500", 45000),
    ("SUNTIK MEMBER", "MEMBER OFFLINE 1000", 70000),
    ("SUNTIK MEMBER", "MEMBER ONLINE 250", 35000),
    ("SUNTIK MEMBER", "MEMBER ONLINE 500", 65000),
    ("SUNTIK MEMBER", "MEMBER ONLINE 1000", 90000),
    ("SUNTIK MEMBER", "MEMBER AKTIF 250", 70000),
    ("SUNTIK MEMBER", "MEMBER AKTIF 500", 135000),
    ("SUNTIK MEMBER", "MEMBER AKTIF 1000", 255000),
    ("SUNTIK MEMBER", "MEMBER REACTION 125", 25000),
    ("SUNTIK MEMBER", "MEMBER REACTION 250", 45000),
    ("SUNTIK MEMBER", "MEMBER REACTION 500", 70000),
    ("SUNTIK MEMBER", "MEMBER VOICE 2", 18000),
    ("SUNTIK MEMBER", "MEMBER VOICE 5", 30000),
    ("SUNTIK MEMBER", "MEMBER VOICE 10", 55000),
    ("SUNTIK MEMBER", "MEMBER CHAT 5", 85000),
    ("SUNTIK MEMBER", "MEMBER CHAT 10", 165000),
    ("SUNTIK MEMBER", "MEMBER CHAT 15", 325000),
    ("SUNTIK MEMBER", "MEMBER NFT 80", 70000),
    ("SUNTIK MEMBER", "MEMBER NFT 160", 135000),
    ("SUNTIK MEMBER", "MEMBER NFT 320", 255000),
    ("TOKEN DISCORD", "TOKEN DISCORD FRESH 1pcs", 2000),
    ("TOKEN DISCORD", "TOKEN DISCORD FRESH 100pcs", 75000),
    ("TOKEN DISCORD", "TOKEN DISCORD 1BULAN+ 1pcs", 4000),
    ("TOKEN DISCORD", "TOKEN DISCORD 1BULAN+ 100pcs", 135000),
    ("TOKEN DISCORD", "TOKEN DISCORD 4BULAN+ 1pcs", 6000),
    ("TOKEN DISCORD", "TOKEN DISCORD 4BULAN+ 100pcs", 195000),
    ("TOKEN DISCORD", "TOKEN DISCORD NITRO 3 Bulan", 35000),
    ("TOKEN DISCORD", "TOKEN DISCORD NITRO 100pcs", 2050000),
    ("QUEST ORBS", "QUEST ORBS VIA LOGIN/TOKEN", 15000),
    ("YOUTUBE SUBSCRIBER", "YT SUBSCRIBER BASIC 100", 10000),
    ("YOUTUBE SUBSCRIBER", "YT SUBSCRIBER BASIC 200", 13000),
    ("YOUTUBE SUBSCRIBER", "YT SUBSCRIBER BASIC 300", 16000),
    ("YOUTUBE SUBSCRIBER", "YT SUBSCRIBER BASIC 400", 19000),
    ("YOUTUBE SUBSCRIBER", "YT SUBSCRIBER BASIC 500", 20000),
    ("YOUTUBE SUBSCRIBER", "YT SUBSCRIBER BASIC 1000", 30000),
    ("YOUTUBE SUBSCRIBER", "YT SUBSCRIBER ELITE 100", 13000),
    ("YOUTUBE SUBSCRIBER", "YT SUBSCRIBER ELITE 200", 20000),
    ("YOUTUBE SUBSCRIBER", "YT SUBSCRIBER ELITE 300", 27000),
    ("YOUTUBE SUBSCRIBER", "YT SUBSCRIBER ELITE 400", 33000),
    ("YOUTUBE SUBSCRIBER", "YT SUBSCRIBER ELITE 500", 40000),
    ("YOUTUBE SUBSCRIBER", "YT SUBSCRIBER ELITE 1000", 65000),
    ("YOUTUBE SUBSCRIBER", "YT SUBSCRIBER LUXURY 100", 20000),
    ("YOUTUBE SUBSCRIBER", "YT SUBSCRIBER LUXURY 200", 35000),
    ("YOUTUBE SUBSCRIBER", "YT SUBSCRIBER LUXURY 300", 50000),
    ("YOUTUBE SUBSCRIBER", "YT SUBSCRIBER LUXURY 400", 60000),
    ("YOUTUBE SUBSCRIBER", "YT SUBSCRIBER LUXURY 500", 65000),
    ("YOUTUBE SUBSCRIBER", "YT SUBSCRIBER LUXURY 1000", 115000),
    ("YOUTUBE LIKES", "YT LIKE BASIC 1000", 9000),
    ("YOUTUBE LIKES", "YT LIKE BASIC 2000", 13000),
    ("YOUTUBE LIKES", "YT LIKE BASIC 3000", 17000),
    ("YOUTUBE LIKES", "YT LIKE BASIC 4000", 21000),
    ("YOUTUBE LIKES", "YT LIKE BASIC 5000", 25000),
    ("YOUTUBE LIKES", "YT LIKE BASIC 10000", 40000),
    ("YOUTUBE LIKES", "YT LIKE ELITE 1000", 12000),
    ("YOUTUBE LIKES", "YT LIKE ELITE 2000", 18000),
    ("YOUTUBE LIKES", "YT LIKE ELITE 3000", 25000),
    ("YOUTUBE LIKES", "YT LIKE ELITE 4000", 31000),
    ("YOUTUBE LIKES", "YT LIKE ELITE 5000", 43000),
    ("YOUTUBE LIKES", "YT LIKE ELITE 10000", 65000),
    ("YOUTUBE LIKES", "YT LIKE LUXURY 1000", 14000),
    ("YOUTUBE LIKES", "YT LIKE LUXURY 2000", 23000),
    ("YOUTUBE LIKES", "YT LIKE LUXURY 3000", 32000),
    ("YOUTUBE LIKES", "YT LIKE LUXURY 4000", 41000),
    ("YOUTUBE LIKES", "YT LIKE LUXURY 5000", 50000),
    ("YOUTUBE LIKES", "YT LIKE LUXURY 10000", 90000),
    ("YOUTUBE VIEWS", "YT VIEWS BASIC 100", 8000),
    ("YOUTUBE VIEWS", "YT VIEWS BASIC 200", 11000),
    ("YOUTUBE VIEWS", "YT VIEWS BASIC 300", 14000),
    ("YOUTUBE VIEWS", "YT VIEWS BASIC 400", 17000),
    ("YOUTUBE VIEWS", "YT VIEWS BASIC 500", 20000),
    ("YOUTUBE VIEWS", "YT VIEWS BASIC 1000", 35000),
    ("YOUTUBE VIEWS", "YT VIEWS ELITE 100", 10000),
    ("YOUTUBE VIEWS", "YT VIEWS ELITE 200", 15000),
    ("YOUTUBE VIEWS", "YT VIEWS ELITE 300", 20000),
    ("YOUTUBE VIEWS", "YT VIEWS ELITE 400", 25000),
    ("YOUTUBE VIEWS", "YT VIEWS ELITE 500", 30000),
    ("YOUTUBE VIEWS", "YT VIEWS ELITE 1000", 45000),
    ("YOUTUBE VIEWS", "YT VIEWS LUXURY 100", 12000),
    ("YOUTUBE VIEWS", "YT VIEWS LUXURY 200", 19000),
    ("YOUTUBE VIEWS", "YT VIEWS LUXURY 300", 26000),
    ("YOUTUBE VIEWS", "YT VIEWS LUXURY 400", 33000),
    ("YOUTUBE VIEWS", "YT VIEWS LUXURY 500", 40000),
    ("YOUTUBE VIEWS", "YT VIEWS LUXURY 1000", 65000),
    ("YOUTUBE SHORT", "YT SHORT BASIC 100", 8000),
    ("YOUTUBE SHORT", "YT SHORT BASIC 200", 11000),
    ("YOUTUBE SHORT", "YT SHORT BASIC 300", 14000),
    ("YOUTUBE SHORT", "YT SHORT BASIC 400", 17000),
    ("YOUTUBE SHORT", "YT SHORT BASIC 500", 20000),
    ("YOUTUBE SHORT", "YT SHORT BASIC 1000", 35000),
    ("YOUTUBE SHORT", "YT SHORT ELITE 100", 10000),
    ("YOUTUBE SHORT", "YT SHORT ELITE 200", 15000),
    ("YOUTUBE SHORT", "YT SHORT ELITE 300", 20000),
    ("YOUTUBE SHORT", "YT SHORT ELITE 400", 25000),
    ("YOUTUBE SHORT", "YT SHORT ELITE 500", 30000),
    ("YOUTUBE SHORT", "YT SHORT ELITE 1000", 45000),
    ("YOUTUBE SHORT", "YT SHORT LUXURY 100", 12000),
    ("YOUTUBE SHORT", "YT SHORT LUXURY 200", 19000),
    ("YOUTUBE SHORT", "YT SHORT LUXURY 300", 26000),
    ("YOUTUBE SHORT", "YT SHORT LUXURY 400", 33000),
    ("YOUTUBE SHORT", "YT SHORT LUXURY 500", 40000),
    ("YOUTUBE SHORT", "YT SHORT LUXURY 1000", 65000),
    ("YOUTUBE LIVE VIEWERS", "YT LIVE VIEWERS BASIC 1000", 14000),
    ("YOUTUBE LIVE VIEWERS", "YT LIVE VIEWERS BASIC 5000", 45000),
    ("YOUTUBE LIVE VIEWERS", "YT LIVE VIEWERS BASIC 10000", 75000),
    ("YOUTUBE LIVE VIEWERS", "YT LIVE VIEWERS ELITE 1000", 32000),
    ("YOUTUBE LIVE VIEWERS", "YT LIVE VIEWERS ELITE 5000", 135000),
    ("YOUTUBE LIVE VIEWERS", "YT LIVE VIEWERS ELITE 10000", 255000),
    ("YOUTUBE LIVE VIEWERS", "YT LIVE VIEWERS LUXURY 1000", 70000),
    ("YOUTUBE LIVE VIEWERS", "YT LIVE VIEWERS LUXURY 5000", 250000),
    ("YOUTUBE LIVE VIEWERS", "YT LIVE VIEWERS LUXURY 10000", 480000),
    ("YOUTUBE JAM TAYANG", "YT JAM TAYANG BASIC 1000", 135000),
    ("YOUTUBE JAM TAYANG", "YT JAM TAYANG BASIC 2000", 265000),
    ("YOUTUBE JAM TAYANG", "YT JAM TAYANG BASIC 3000", 395000),
    ("YOUTUBE JAM TAYANG", "YT JAM TAYANG BASIC 4000", 525000),
    ("YOUTUBE JAM TAYANG", "YT JAM TAYANG ELITE 1000", 175000),
    ("YOUTUBE JAM TAYANG", "YT JAM TAYANG ELITE 2000", 345000),
    ("YOUTUBE JAM TAYANG", "YT JAM TAYANG ELITE 3000", 515000),
    ("YOUTUBE JAM TAYANG", "YT JAM TAYANG ELITE 4000", 685000),
    ("YOUTUBE JAM TAYANG", "YT JAM TAYANG LUXURY 1000", 305000),
    ("YOUTUBE JAM TAYANG", "YT JAM TAYANG LUXURY 2000", 605000),
    ("YOUTUBE JAM TAYANG", "YT JAM TAYANG LUXURY 3000", 905000),
    ("YOUTUBE JAM TAYANG", "YT JAM TAYANG LUXURY 4000", 1205000),
    ("INSTAGRAM FOLLOWERS", "IG FOLLOWERS INDONESIA 100", 12000),
    ("INSTAGRAM FOLLOWERS", "IG FOLLOWERS INDONESIA 500", 35000),
    ("INSTAGRAM FOLLOWERS", "IG FOLLOWERS INDONESIA 1000", 60000),
    ("INSTAGRAM FOLLOWERS", "IG FOLLOWERS BASIC 1000", 11000),
    ("INSTAGRAM FOLLOWERS", "IG FOLLOWERS BASIC 5000", 30000),
    ("INSTAGRAM FOLLOWERS", "IG FOLLOWERS BASIC 10000", 50000),
    ("INSTAGRAM FOLLOWERS", "IG FOLLOWERS ELITE 1000", 20000),
    ("INSTAGRAM FOLLOWERS", "IG FOLLOWERS ELITE 5000", 80000),
    ("INSTAGRAM FOLLOWERS", "IG FOLLOWERS ELITE 10000", 155000),
    ("INSTAGRAM FOLLOWERS", "IG FOLLOWERS LUXURY 1000", 32000),
    ("INSTAGRAM FOLLOWERS", "IG FOLLOWERS LUXURY 5000", 140000),
    ("INSTAGRAM FOLLOWERS", "IG FOLLOWERS LUXURY 10000", 275000),
    ("INSTAGRAM LIKE", "IG LIKE INDONESIA 100", 8000),
    ("INSTAGRAM LIKE", "IG LIKE INDONESIA 500", 17000),
    ("INSTAGRAM LIKE", "IG LIKE BASIC 1000", 8000),
    ("INSTAGRAM LIKE", "IG LIKE BASIC 5000", 15000),
    ("INSTAGRAM LIKE", "IG LIKE BASIC 10000", 20000),
    ("INSTAGRAM LIKE", "IG LIKE ELITE 1000", 12000),
    ("INSTAGRAM LIKE", "IG LIKE ELITE 5000", 25000),
    ("INSTAGRAM LIKE", "IG LIKE ELITE 10000", 40000),
    ("INSTAGRAM LIKE", "IG LIKE LUXURY 1000", 15000),
    ("INSTAGRAM LIKE", "IG LIKE LUXURY 5000", 40000),
    ("INSTAGRAM LIKE", "IG LIKE LUXURY 10000", 70000),
    ("INSTAGRAM VIEWS", "IG VIEWS BASIC 10000", 8000),
    ("INSTAGRAM VIEWS", "IG VIEWS BASIC 20000", 11000),
    ("INSTAGRAM VIEWS", "IG VIEWS BASIC 30000", 14000),
    ("INSTAGRAM VIEWS", "IG VIEWS BASIC 40000", 17000),
    ("INSTAGRAM VIEWS", "IG VIEWS BASIC 50000", 20000),
    ("INSTAGRAM VIEWS", "IG VIEWS BASIC 100000", 35000),
    ("INSTAGRAM VIEWS", "IG VIEWS ELITE 10000", 10000),
    ("INSTAGRAM VIEWS", "IG VIEWS ELITE 20000", 13000),
    ("INSTAGRAM VIEWS", "IG VIEWS ELITE 30000", 16000),
    ("INSTAGRAM VIEWS", "IG VIEWS ELITE 40000", 19000),
    ("INSTAGRAM VIEWS", "IG VIEWS ELITE 50000", 22000),
    ("INSTAGRAM VIEWS", "IG VIEWS ELITE 100000", 37000),
    ("INSTAGRAM VIEWS", "IG VIEWS LUXURY 10000", 12000),
    ("INSTAGRAM VIEWS", "IG VIEWS LUXURY 20000", 14000),
    ("INSTAGRAM VIEWS", "IG VIEWS LUXURY 30000", 17000),
    ("INSTAGRAM VIEWS", "IG VIEWS LUXURY 40000", 20000),
    ("INSTAGRAM VIEWS", "IG VIEWS LUXURY 50000", 33000),
    ("INSTAGRAM VIEWS", "IG VIEWS LUXURY 100000", 38000),
    ("INSTAGRAM LIVE VIEWERS", "IG LIVE VIEWERS BASIC 100", 12000),
    ("INSTAGRAM LIVE VIEWERS", "IG LIVE VIEWERS BASIC 500", 35000),
    ("INSTAGRAM LIVE VIEWERS", "IG LIVE VIEWERS BASIC 1000", 55000),
    ("INSTAGRAM LIVE VIEWERS", "IG LIVE VIEWERS ELITE 100", 13000),
    ("INSTAGRAM LIVE VIEWERS", "IG LIVE VIEWERS ELITE 500", 45000),
    ("INSTAGRAM LIVE VIEWERS", "IG LIVE VIEWERS ELITE 1000", 75000),
    ("INSTAGRAM LIVE VIEWERS", "IG LIVE VIEWERS LUXURY 100", 16000),
    ("INSTAGRAM LIVE VIEWERS", "IG LIVE VIEWERS LUXURY 500", 55000),
    ("INSTAGRAM LIVE VIEWERS", "IG LIVE VIEWERS LUXURY 1000", 95000),
    ("TIKTOK FOLLOWERS", "TIKTOK FOLLOWERS BASIC 100", 12000),
    ("TIKTOK FOLLOWERS", "TIKTOK FOLLOWERS BASIC 500", 20000),
    ("TIKTOK FOLLOWERS", "TIKTOK FOLLOWERS BASIC 1000", 30000),
    ("TIKTOK FOLLOWERS", "TIKTOK FOLLOWERS ELITE 100", 14000),
    ("TIKTOK FOLLOWERS", "TIKTOK FOLLOWERS ELITE 500", 30000),
    ("TIKTOK FOLLOWERS", "TIKTOK FOLLOWERS ELITE 1000", 45000),
    ("TIKTOK FOLLOWERS", "TIKTOK FOLLOWERS LUXURY 100", 16000),
    ("TIKTOK FOLLOWERS", "TIKTOK FOLLOWERS LUXURY 500", 50000),
    ("TIKTOK FOLLOWERS", "TIKTOK FOLLOWERS LUXURY 1000", 75000),
    ("TIKTOK LIKE", "TIKTOK LIKE BASIC 1000", 8000),
    ("TIKTOK LIKE", "TIKTOK LIKE BASIC 5000", 13000),
    ("TIKTOK LIKE", "TIKTOK LIKE BASIC 10000", 20000),
    ("TIKTOK LIKE", "TIKTOK LIKE ELITE 1000", 10000),
    ("TIKTOK LIKE", "TIKTOK LIKE ELITE 5000", 25000),
    ("TIKTOK LIKE", "TIKTOK LIKE ELITE 10000", 40000),
    ("TIKTOK LIKE", "TIKTOK LIKE LUXURY 1000", 13000),
    ("TIKTOK LIKE", "TIKTOK LIKE LUXURY 5000", 35000),
    ("TIKTOK LIKE", "TIKTOK LIKE LUXURY 10000", 60000),
    ("TIKTOK VIEWS", "TIKTOK VIEWS BASIC 10000", 9000),
    ("TIKTOK VIEWS", "TIKTOK VIEWS BASIC 50000", 20000),
    ("TIKTOK VIEWS", "TIKTOK VIEWS BASIC 100000", 31000),
    ("TIKTOK VIEWS", "TIKTOK VIEWS ELITE 10000", 12000),
    ("TIKTOK VIEWS", "TIKTOK VIEWS ELITE 50000", 25000),
    ("TIKTOK VIEWS", "TIKTOK VIEWS ELITE 100000", 40000),
    ("TIKTOK VIEWS", "TIKTOK VIEWS LUXURY 10000", 16000),
    ("TIKTOK VIEWS", "TIKTOK VIEWS LUXURY 50000", 40000),
    ("TIKTOK VIEWS", "TIKTOK VIEWS LUXURY 100000", 65000),
    ("TIKTOK SHARE", "TIKTOK SHARE BASIC 100", 5000),
    ("TIKTOK SHARE", "TIKTOK SHARE BASIC 500", 12000),
    ("TIKTOK SHARE", "TIKTOK SHARE BASIC 1000", 16000),
    ("TIKTOK SHARE", "TIKTOK SHARE ELITE 100", 9000),
    ("TIKTOK SHARE", "TIKTOK SHARE ELITE 500", 16000),
    ("TIKTOK SHARE", "TIKTOK SHARE ELITE 1000", 20000),
    ("TIKTOK SHARE", "TIKTOK SHARE LUXURY 100", 11000),
    ("TIKTOK SHARE", "TIKTOK SHARE LUXURY 500", 20000),
    ("TIKTOK SHARE", "TIKTOK SHARE LUXURY 1000", 28000),
    ("TIKTOK LIVE VIEWERS", "TIKTOK LIVE VIEWERS BASIC 100", 9000),
    ("TIKTOK LIVE VIEWERS", "TIKTOK LIVE VIEWERS BASIC 500", 18000),
    ("TIKTOK LIVE VIEWERS", "TIKTOK LIVE VIEWERS BASIC 1000", 27000),
    ("TIKTOK LIVE VIEWERS", "TIKTOK LIVE VIEWERS ELITE 100", 12000),
    ("TIKTOK LIVE VIEWERS", "TIKTOK LIVE VIEWERS ELITE 500", 28000),
    ("TIKTOK LIVE VIEWERS", "TIKTOK LIVE VIEWERS ELITE 1000", 39000),
    ("TIKTOK LIVE VIEWERS", "TIKTOK LIVE VIEWERS LUXURY 100", 16000),
    ("TIKTOK LIVE VIEWERS", "TIKTOK LIVE VIEWERS LUXURY 500", 45000),
    ("TIKTOK LIVE VIEWERS", "TIKTOK LIVE VIEWERS LUXURY 1000", 65000),
]


# -- Catatan tier bersama untuk layanan sosial media (SMM) --------------------
SMM_TIER_NOTE = (
    "Basic: tanpa garansi.\n"
    "Elite: garansi refill 30 hari (jika turun diisi ulang gratis).\n"
    "Luxury: permanent, garansi refill seumur hidup."
)

# -- Deskripsi & S&K per kategori (untuk embed tiket & auto-reply) ------------
CATEGORY_INFO = {
    "ALIGHT MOTION": {
        "description": (
            "- Akun Private, login di mana saja (iOS/Android/PC)\n"
            "- Semua fitur Pro: keyframe animation, efek visual, color correction\n"
            "- Tanpa watermark, export kualitas tinggi\n"
            "- Full garansi selama masa aktif"
        ),
        "terms": "Akun bisa dari kami ataupun akunmu sendiri, tergantung stok.",
    },
    "REMINI": {
        "description": (
            "- Akun dari kami, tinggal login\n"
            "- Unlimited download, pemulihan detail tertinggi\n"
            "- Sharing = 1 device · Private = bebas device · Pro+ = akses iOS/Android/Web"
        ),
        "terms": (
            "Akun bisa dari kami ataupun akunmu sendiri (tergantung stok).\n"
            "Sharing hanya boleh 1 device. Private bebas device (disarankan 1)."
        ),
    },
    "CANVA": {
        "description": (
            "- Pakai akun kamu, cukup kirim email\n"
            "- Jutaan template premium, brand kit, font, custom template\n"
            "- PRO OWNER bisa invite hingga 500 member\n"
            "- Full garansi selama masa aktif"
        ),
        "terms": "Kirimkan email setelah melakukan pembayaran.",
    },
    "CAPCUT": {
        "description": (
            "- Akses semua fitur Pro CapCut\n"
            "- Sharing = 1 akun dipakai bersama · Private = 1 akun 1 user"
        ),
        "terms": "Sharing hanya boleh 1 device. Private bebas device (disarankan 1).",
    },
    "CHATGPT": {
        "description": (
            "- Pakai akun kamu/kami, cukup kirim email (Garansi 28 Hari)\n"
            "- GO: akses GPT-5.3 · PLUS: GPT-5.3 Advanced, render lebih cepat\n"
            "- BUSINESS: GPT-5.4 Pro, untuk analisis bisnis / buat aplikasi"
        ),
        "terms": "Garansi 28 hari. Bisa digunakan di semua device (HP/PC/Tablet).",
    },
    "GROK AI": {
        "description": (
            "- Akses informasi realtime via X\n"
            "- Model AI terbaru Grok 3\n"
            "- Pembuatan gambar tingkat tinggi"
        ),
        "terms": "",
    },
    "GEMINI AI": {
        "description": "- Akses Gemini 3.1 Pro\n- Integrasi Gmail, Docs, dll",
        "terms": "Akun buyer/seller tergantung stok.",
    },
    "BSTATION": {
        "description": (
            "- Akun dari kami, tinggal login. Bebas iklan\n"
            "- Semua anime premium, kualitas 1080p-4K\n"
            "- Android, iOS, Web · Sharing = 1 device · Private = 1 user"
        ),
        "terms": "Garansi selama masa aktif. Sharing hanya 1 device, Private full akses.",
    },
    "YOUTUBE PREMIUM": {
        "description": (
            "- Tanpa iklan, download video 720p, play di background, YouTube Music\n"
            "- ADMIN: bisa invite 5 orang · INVITE: pakai akunmu · INDIVIDUAL: akun kami/kamu"
        ),
        "terms": (
            "Admin pakai akun kami. Individual akun kami/kamu (tergantung stok).\n"
            "Invite: akunmu wajib belum pernah gabung Family sebelumnya."
        ),
    },
    "VIU": {
        "description": (
            "- Akun legal, fresh dibuat saat order. Kualitas HD/Ultra HD, tanpa iklan\n"
            "- Bisa download & nonton offline (Android/iOS/Web/Smart TV)\n"
            "- Premium+ : Ultra HD + gratis HBO MAX selama masa aktif"
        ),
        "terms": (
            "Akun dari kami tinggal login. Untuk sharing, logout device lama dulu "
            "sebelum pindah device, kalau tidak garansi hangus."
        ),
    },
    "AMAZON PRIME VIDEO": {
        "description": (
            "- Akun legal, region Indonesia (tanpa VPN)\n"
            "- Kualitas Ultra HD, tanpa iklan (Android/iOS/Web/Smart TV)\n"
            "- Sharing = 1 device · Private = hingga 3 device"
        ),
        "terms": (
            "Akun dari kami tinggal login. Untuk sharing, logout device lama dulu "
            "sebelum pindah device, kalau tidak garansi hangus."
        ),
    },
    "WETV": {
        "description": (
            "- Akun VIP original & legal, garansi kendala login\n"
            "- Bebas nonton episode VIP, maraton drama\n"
            "- COIN: untuk unlock episode/konten premium"
        ),
        "terms": (
            "Akun dari kami tinggal login. Dilarang mengubah isi akun, "
            "dilarang login-logout, dilarang ganti-ganti device."
        ),
    },
    "IQIYI": {
        "description": (
            "- Film VIP lengkap, bebas iklan, bisa download VIP\n"
            "- STANDARD: Bluray 1080p · PREMIUM: 4K Ultra HD + Dolby Atmos\n"
            "- Premium Sharing = akun sharing · Premium Private = 1 user"
        ),
        "terms": "Akun dari kami tinggal login. Sharing 1 device, Private bebas device.",
    },
    "HBO MAX": {
        "description": (
            "- STANDARD: Full HD 1080p, 2 perangkat, 30 unduhan\n"
            "- ULTIMATE: 4K Ultra HD, Dolby Atmos, 4 perangkat, 100 unduhan\n"
            "- Harga tertera per bulan (tersedia opsi Sharing & Private)"
        ),
        "terms": "Akun dari seller. Untuk login TV minimal beli 2.",
    },
    "VIDIO": {
        "description": (
            "- Vidio Platinum: bebas iklan & unduh konten\n"
            "- Tayangan olahraga (Liga Champions, BRI Liga 1, dll)\n"
            "- Tier: TV Only / Mobile / All Device (Sharing atau Private)"
        ),
        "terms": "Masa aktif sesuai pembelian. Sharing 1 device, Private bebas device.",
    },
    "SPOTIFY": {
        "description": (
            "- Musik tanpa iklan, download & mode offline, play bebas (no shuffle)\n"
            "- Kualitas audio tinggi, semua device (HP/PC/Tablet)\n"
            "- Individual / Family / Platinum (full fitur + full garansi)"
        ),
        "terms": "Disarankan 1 device aktif untuk menghindari risiko akun.",
    },
    "APPLE MUSIC": {
        "description": (
            "- Kualitas audio Lossless, bebas iklan, 100+ juta lagu\n"
            "- Via invite email, tanpa login"
        ),
        "terms": "Tersedia harga akun baru & perpanjang.",
    },
    "GOOGLE DRIVE": {
        "description": (
            "- Pilihan 100GB / 300GB / Unlimited\n"
            "- Akun Baru (dari kami, tinggal login) atau Akun Pribadi (kirim Gmail)"
        ),
        "terms": (
            "Garansi 1 bulan & berlaku seumur hidup selama tidak melanggar TOS Google. "
            "Garansi hangus bila melanggar TOS Google."
        ),
    },
    "OUTLOOK": {
        "description": (
            "- Akun fresh dibuat saat order, tinggal login, bebas ganti password\n"
            "- Bisa @outlook.com / @hotmail.com"
        ),
        "terms": "Garansi login 1 hari setelah pembelian.",
    },
    "GMAIL": {
        "description": "- Akun Gmail fresh dibuat saat order, tinggal login, bebas ganti password",
        "terms": "Garansi login 1 hari setelah pembelian.",
    },
    "RANDOM STEAM KEY": {
        "description": (
            "- Semua key dijamin berfungsi & mendapatkan games\n"
            "- Game yang didapat RANDOM (tidak bisa pilih)\n"
            "- Tier: Basic / Elite / Luxury"
        ),
        "terms": "Setiap pembelian key Luxury mendapat bonus key Basic.",
    },
    "XBOX GAMEPASS": {
        "description": "- Legal 100%, berupa redeem code\n- Akses ratusan game Xbox PC / Console",
        "terms": "",
    },
    "AKUN STEAM FRESH": {
        "description": "- Akun baru dibuat, Full Access (bebas ganti email & password)",
        "terms": "",
    },
    "AKUN STEAM PREMIUM GAMES": {
        "description": (
            "- Garansi login, mendapat game utama sesuai pilihan\n"
            "- BONUS: isi game random tambahan (bervariasi hingga 30+ game per akun)"
        ),
        "terms": "",
    },
    "AKUN EPIC GAMES": {
        "description": (
            "- Full Access (bebas ganti email & password)\n"
            "- Berisi puluhan hingga ratusan game premium siap main"
        ),
        "terms": "",
    },
    "AKUN ROBLOX": {
        "description": (
            "- Akun Roblox fresh\n"
            "- 13+ standar · 21+ bisa Voice Chat & masuk server dewasa"
        ),
        "terms": "",
    },
    "ROBUX GIFT CARD": {
        "description": "- Robux via Gift Card. Pilih nominal sesuai kebutuhan.",
        "terms": "",
    },
    "NITRO BOOST": {
        "description": (
            "- 500MB upload, custom emoji, HD streaming, 2 server boost, dll\n"
            "- Via Login / Via Gift / Promotion (khusus akun belum pernah Nitro)"
        ),
        "terms": (
            "PROMOTION: khusus akun yang belum pernah Nitro sama sekali.\n"
            "GIFT: untuk semua akun, tanpa login, dikirim link gift.\n"
            "VIA LOGIN: untuk semua akun, perlu login."
        ),
    },
    "NITRO BASIC": {
        "description": (
            "- 50MB upload, custom emoji, unlimited super reactions, badge Nitro\n"
            "- Via Login / Via Gift"
        ),
        "terms": "GIFT tanpa login (dikirim link), Via Login perlu login.",
    },
    "NITRO CODE": {
        "description": "- Nitro code unchecked (belum dicek), dijual per jumlah codes.",
        "terms": "Status code belum dicek (unchecked).",
    },
    "JASA BOOST SERVER": {
        "description": (
            "- Boost server pakai akun dari kami\n"
            "- Paket 1 Bulan / 3 Bulan, pilihan jumlah boost / level server\n"
            "- Cukup share link server"
        ),
        "terms": (
            "Lama proses tergantung antrian. Dilarang kick akun kami setelah boost; "
            "jika di-kick boost dianggap hangus. Jika server kena wave, garansi hangus."
        ),
    },
    "SUNTIK MEMBER": {
        "description": (
            "- Full otomatis (tinggal add bot, member masuk sendiri), jumlah bisa custom\n"
            "- Offline / Online (garansi 1 bln) / Aktif (orang asli) / Reaction (seumur hidup)\n"
            "- Voice (24/7, 1 bln) / Chat (random, 1 bln) / NFT (online + profil NFT)"
        ),
        "terms": "Profil realistic (username, avatar, HypeSquad, bio).",
    },
    "TOKEN DISCORD": {
        "description": (
            "- Token akun Discord: Fresh / 1 Bulan+ / 4 Bulan+ / Nitro\n"
            "- Dijual satuan atau paket 100"
        ),
        "terms": "Akun di atas belum pernah Nitro, bisa untuk Nitro Promotion.",
    },
    "QUEST ORBS": {
        "description": "- Selesaikan semua mission Quest (watch/play on desktop) via login/token.",
        "terms": "Cukup kirim token; dibantu admin jika tidak tahu cara ambil token.",
    },
    "YOUTUBE SUBSCRIBER": {
        "description": (
            "- Tanpa login, hanya butuh link channel\n"
            "- Subscriber tidak boleh di-hide\n"
            "- Luxury terbaik untuk monetize YouTube"
        ),
        "terms": "Tidak ada refund kecuali pesanan gagal.\n" + SMM_TIER_NOTE,
    },
    "YOUTUBE LIKES": {
        "description": "- Tanpa login, hanya butuh link video.",
        "terms": SMM_TIER_NOTE,
    },
    "YOUTUBE VIEWS": {
        "description": "- Tanpa login, hanya butuh link video.",
        "terms": SMM_TIER_NOTE,
    },
    "YOUTUBE SHORT": {
        "description": "- Views untuk YouTube Short. Tanpa login, hanya butuh link video.",
        "terms": SMM_TIER_NOTE,
    },
    "YOUTUBE LIVE VIEWERS": {
        "description": (
            "- Instant proses 1-3 menit\n"
            "- Basic nonton 15 menit · Elite 60 menit · Luxury 120 menit"
        ),
        "terms": SMM_TIER_NOTE,
    },
    "YOUTUBE JAM TAYANG": {
        "description": (
            "- Sangat direkomendasikan untuk monetize YouTube\n"
            "- Basic: video min durasi 8 jam · Elite: min 3 jam · Luxury: min 1 jam"
        ),
        "terms": SMM_TIER_NOTE,
    },
    "INSTAGRAM FOLLOWERS": {
        "description": (
            "- Tanpa login, butuh link profil/username\n"
            "- Tersedia followers Region Indonesia & Global (Basic/Elite/Luxury)"
        ),
        "terms": (
            "Akun tidak boleh di-private atau ganti username setelah pengisian.\n"
            + SMM_TIER_NOTE
        ),
    },
    "INSTAGRAM LIKE": {
        "description": (
            "- Tanpa login, butuh link postingan\n"
            "- Tersedia like Region Indonesia & Global"
        ),
        "terms": (
            "Akun tidak boleh di-private sebelum maupun sesudah pengisian.\n"
            + SMM_TIER_NOTE
        ),
    },
    "INSTAGRAM VIEWS": {
        "description": (
            "- Tanpa login, butuh link video\n"
            "- Semua paket full garansi, makin tinggi paket makin besar bonus"
        ),
        "terms": SMM_TIER_NOTE,
    },
    "INSTAGRAM LIVE VIEWERS": {
        "description": (
            "- Instant proses 1-3 menit\n"
            "- Basic nonton 30 menit · Elite 60 menit · Luxury 120 menit"
        ),
        "terms": SMM_TIER_NOTE,
    },
    "TIKTOK FOLLOWERS": {
        "description": "- Tanpa login, butuh link profil/username.",
        "terms": "Akun tidak boleh di-private.\n" + SMM_TIER_NOTE,
    },
    "TIKTOK LIKE": {
        "description": "- Tanpa login, butuh link postingan.",
        "terms": "Akun dilarang di-private sebelum maupun sesudah pengisian.\n" + SMM_TIER_NOTE,
    },
    "TIKTOK VIEWS": {
        "description": (
            "- Tanpa login, butuh link postingan\n"
            "- Elite: + reach + bonus · Luxury: peluang FYP + like/followers asli (algoritma khusus)"
        ),
        "terms": SMM_TIER_NOTE,
    },
    "TIKTOK SHARE": {
        "description": "- Menambah jumlah share pada postingan TikTok.",
        "terms": "Akun dilarang di-private.\n" + SMM_TIER_NOTE,
    },
    "TIKTOK LIVE VIEWERS": {
        "description": (
            "- Instant proses 1-3 menit\n"
            "- Basic nonton 30 menit · Elite 60 menit · Luxury 180 menit"
        ),
        "terms": SMM_TIER_NOTE,
    },
}

def get_category_info(category: str) -> dict:
    """Kembalikan {'description','terms'} untuk kategori (kosong bila tidak ada)."""
    info = CATEGORY_INFO.get(category)
    if not info:
        return {"description": "", "terms": ""}
    return {"description": info.get("description", ""), "terms": info.get("terms", "")}
