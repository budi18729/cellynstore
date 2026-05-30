"""
Cellyn Store - Free Game Notifier Cog
Memantau game gratis dari Epic Games, Steam, GOG, dan Ubisoft
setiap 15 menit dan auto-post ke channel yang ditentukan.
"""

import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

import aiohttp
import discord
from discord.ext import commands, tasks

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# KONFIGURASI — sesuaikan di sini atau via .env
# ─────────────────────────────────────────────
FREE_GAME_CHANNEL_ID = int(os.getenv("FREE_GAME_CHANNEL_ID", "0"))  # ID channel Discord
SEEN_GAMES_FILE = Path("data/seen_games.json")  # file penyimpanan game yang sudah dipost

# Warna embed per store
STORE_COLORS = {
    "epic":    0x2ECC71,   # hijau Epic
    "steam":   0x1B2838,   # biru gelap Steam
    "gog":     0x8A2BE2,   # ungu GOG
    "ubisoft": 0x0070D1,   # biru Ubisoft
}

STORE_ICONS = {
    "epic":    "https://store.epicgames.com/favicon.ico",
    "steam":   "https://store.steampowered.com/favicon.ico",
    "gog":     "https://www.gog.com/favicon.ico",
    "ubisoft": "https://store.ubisoft.com/favicon.ico",
}

STORE_LABELS = {
    "epic":    "Epic Games Store",
    "steam":   "Steam",
    "gog":     "GOG",
    "ubisoft": "Ubisoft Connect",
}


# ─────────────────────────────────────────────
# HELPER: load/save seen games
# ─────────────────────────────────────────────
def load_seen_games() -> set:
    SEEN_GAMES_FILE.parent.mkdir(parents=True, exist_ok=True)
    if SEEN_GAMES_FILE.exists():
        try:
            return set(json.loads(SEEN_GAMES_FILE.read_text()))
        except Exception:
            return set()
    return set()


def save_seen_games(seen: set) -> None:
    SEEN_GAMES_FILE.write_text(json.dumps(list(seen)))


def game_id(game: dict) -> str:
    """Buat unique ID dari nama + store."""
    raw = f"{game.get('store', '')}:{game.get('title', '')}".lower()
    return hashlib.md5(raw.encode()).hexdigest()


# ─────────────────────────────────────────────
# FETCHERS — satu fungsi per store
# ─────────────────────────────────────────────
async def fetch_epic(session: aiohttp.ClientSession) -> list[dict]:
    """Ambil game gratis dari Epic Games Store."""
    url = (
        "https://store-site-backend-static.ak.epicgames.com/freeGamesPromotions"
        "?locale=en-US&country=ID&allowCountries=ID"
    )
    games = []
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            if resp.status != 200:
                return []
            data = await resp.json()
            elements = (
                data.get("data", {})
                .get("Catalog", {})
                .get("searchStore", {})
                .get("elements", [])
            )
            for el in elements:
                promotions = el.get("promotions") or {}
                current = promotions.get("promotionalOffers", [])
                if not current:
                    continue
                # Pastikan benar-benar gratis (harga 0)
                price_info = el.get("price", {}).get("totalPrice", {})
                if price_info.get("discountPrice", 1) != 0:
                    continue

                slug = el.get("productSlug") or el.get("urlSlug") or ""
                url_game = f"https://store.epicgames.com/en-US/p/{slug}" if slug else "https://store.epicgames.com/en-US/free-games"

                # Ambil gambar thumbnail
                image_url = ""
                for img in el.get("keyImages", []):
                    if img.get("type") in ("DieselStoreFrontWide", "OfferImageWide", "Thumbnail"):
                        image_url = img.get("url", "")
                        break

                # Ambil tanggal berakhir promo
                end_date = ""
                try:
                    offers = current[0].get("promotionalOffers", [])
                    if offers:
                        end_date = offers[0].get("endDate", "")
                except Exception:
                    pass

                games.append({
                    "store": "epic",
                    "title": el.get("title", "Unknown"),
                    "url": url_game,
                    "image": image_url,
                    "description": el.get("description", ""),
                    "end_date": end_date,
                })
    except Exception as e:
        logger.warning(f"[Epic] Gagal fetch: {e}")
    return games


async def fetch_steam(session: aiohttp.ClientSession) -> list[dict]:
    """Ambil game gratis dari Steam (pakai endpoint featured)."""
    url = "https://store.steampowered.com/api/featuredcategories?cc=id&l=en"
    games = []
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            if resp.status != 200:
                return []
            data = await resp.json(content_type=None)
            specials = data.get("specials", {}).get("items", [])
            for item in specials:
                if item.get("final_price", 1) != 0:
                    continue
                appid = item.get("id")
                games.append({
                    "store": "steam",
                    "title": item.get("name", "Unknown"),
                    "url": f"https://store.steampowered.com/app/{appid}",
                    "image": item.get("large_capsule_image") or item.get("header_image", ""),
                    "description": "",
                    "end_date": "",
                })
    except Exception as e:
        logger.warning(f"[Steam] Gagal fetch: {e}")
    return games


async def fetch_gog(session: aiohttp.ClientSession) -> list[dict]:
    """Ambil game gratis dari GOG."""
    url = "https://www.gog.com/games/ajax/filtered?mediaType=game&price=free&sort=popularity"
    games = []
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            if resp.status != 200:
                return []
            data = await resp.json(content_type=None)
            for item in data.get("products", []):
                if item.get("price", {}).get("isFree") is not True:
                    continue
                slug = item.get("slug", "")
                games.append({
                    "store": "gog",
                    "title": item.get("title", "Unknown"),
                    "url": f"https://www.gog.com/game/{slug}",
                    "image": "https:" + item.get("image", "") + "_196.jpg" if item.get("image") else "",
                    "description": "",
                    "end_date": "",
                })
    except Exception as e:
        logger.warning(f"[GOG] Gagal fetch: {e}")
    return games


async def fetch_ubisoft(session: aiohttp.ClientSession) -> list[dict]:
    """Ambil game gratis dari Ubisoft Connect."""
    url = (
        "https://store.ubi.com/api/products/search"
        "?filters=priceCurrency%3AIDR%2CpriceMax%3A0&locale=id-ID&pageSize=10"
    )
    games = []
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            if resp.status != 200:
                return []
            data = await resp.json(content_type=None)
            for item in data.get("items", []):
                price = item.get("price", {}).get("value", 1)
                if price != 0:
                    continue
                slug = item.get("url") or item.get("id", "")
                games.append({
                    "store": "ubisoft",
                    "title": item.get("title", "Unknown"),
                    "url": f"https://store.ubisoft.com/id/{slug}.html" if slug else "https://store.ubisoft.com",
                    "image": item.get("image", {}).get("url", "") if isinstance(item.get("image"), dict) else "",
                    "description": "",
                    "end_date": "",
                })
    except Exception as e:
        logger.warning(f"[Ubisoft] Gagal fetch: {e}")
    return games


# ─────────────────────────────────────────────
# COG UTAMA
# ─────────────────────────────────────────────
class FreeGameNotifier(commands.Cog):
    """Cog notifikasi game gratis untuk Cellyn Store."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.seen_games: set = load_seen_games()
        self.check_free_games.start()
        logger.info("[FreeGameNotifier] Cog loaded, loop dimulai.")

    def cog_unload(self):
        self.check_free_games.cancel()

    # ── Loop utama ────────────────────────────
    @tasks.loop(minutes=15)
    async def check_free_games(self):
        channel = self.bot.get_channel(FREE_GAME_CHANNEL_ID)
        if not channel:
            logger.warning(f"[FreeGameNotifier] Channel ID {FREE_GAME_CHANNEL_ID} tidak ditemukan.")
            return

        async with aiohttp.ClientSession() as session:
            all_games: list[dict] = []
            all_games += await fetch_epic(session)
            all_games += await fetch_steam(session)
            all_games += await fetch_gog(session)
            all_games += await fetch_ubisoft(session)

        new_games = [g for g in all_games if game_id(g) not in self.seen_games]

        for game in new_games:
            try:
                embed = self._build_embed(game)
                await channel.send(embed=embed)
                self.seen_games.add(game_id(game))
                logger.info(f"[FreeGameNotifier] Posted: {game['title']} ({game['store']})")
            except Exception as e:
                logger.error(f"[FreeGameNotifier] Gagal kirim embed: {e}")

        if new_games:
            save_seen_games(self.seen_games)

    @check_free_games.before_loop
    async def before_check(self):
        await self.bot.wait_until_ready()

    # ── Builder embed ─────────────────────────
    def _build_embed(self, game: dict) -> discord.Embed:
        store = game["store"]
        color = STORE_COLORS.get(store, 0xFFFFFF)
        label = STORE_LABELS.get(store, store.capitalize())
        icon  = STORE_ICONS.get(store, "")

        embed = discord.Embed(
            title=f"🎮 {game['title']}",
            url=game.get("url", ""),
            description=game.get("description") or "Game ini sedang gratis! Klaim sekarang sebelum kehabisan.",
            color=color,
            timestamp=datetime.now(timezone.utc),
        )

        embed.set_author(name=f"Game Gratis — {label}", icon_url=icon)

        if game.get("image"):
            embed.set_image(url=game["image"])

        if game.get("end_date"):
            try:
                dt = datetime.fromisoformat(game["end_date"].replace("Z", "+00:00"))
                embed.add_field(
                    name="⏳ Gratis sampai",
                    value=discord.utils.format_dt(dt, style="F"),
                    inline=False,
                )
            except Exception:
                pass

        embed.add_field(name="🔗 Klaim Sekarang", value=f"[Klik di sini]({game.get('url', '#')})", inline=True)
        embed.set_footer(text="Cellyn Store • Free Game Notifier")

        return embed

    # ── Command manual (opsional) ─────────────
    @commands.command(name="freegames", aliases=["fg"])
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def free_games_command(self, ctx: commands.Context):
        """Cek game gratis sekarang (manual trigger)."""
        msg = await ctx.send("🔍 Mengecek game gratis...")

        async with aiohttp.ClientSession() as session:
            all_games: list[dict] = []
            all_games += await fetch_epic(session)
            all_games += await fetch_steam(session)
            all_games += await fetch_gog(session)
            all_games += await fetch_ubisoft(session)

        if not all_games:
            await msg.edit(content="😔 Tidak ada game gratis ditemukan saat ini.")
            return

        await msg.edit(content=f"✅ Ditemukan **{len(all_games)}** game gratis:")
        for game in all_games[:5]:  # max 5 sekaligus biar ga spam
            embed = self._build_embed(game)
            await ctx.send(embed=embed)


# ─────────────────────────────────────────────
# SETUP — dipanggil saat load_extension
# ─────────────────────────────────────────────
async def setup(bot: commands.Bot):
    await bot.add_cog(FreeGameNotifier(bot))
