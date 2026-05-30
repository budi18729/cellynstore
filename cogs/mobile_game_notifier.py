"""
Cellyn Store - Mobile Free Game Notifier Cog
Memantau game gratis Android & iOS via GamerPower API
setiap 15 menit dan auto-post ke channel yang ditentukan.

Attribution: Data powered by GamerPower.com
"""

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
# KONFIGURASI
# ─────────────────────────────────────────────
MOBILE_GAME_CHANNEL_ID = int(os.getenv("MOBILE_GAME_CHANNEL_ID", "0"))
SEEN_MOBILE_FILE = Path("data/seen_mobile_games.json")

GAMERPOWER_API = "https://www.gamerpower.com/api/filter?platform=android.ios&type=game"

PLATFORM_COLORS = {
    "android": 0x3DDC84,   # hijau Android
    "ios":     0x007AFF,   # biru iOS
    "both":    0xF89406,   # oranye GamerPower (Android + iOS)
}

PLATFORM_EMOJI = {
    "android": "<:android:0> 🤖",
    "ios":     " 🍎",
    "both":    "🤖🍎",
}


# ─────────────────────────────────────────────
# HELPER
# ─────────────────────────────────────────────
def load_seen() -> set:
    SEEN_MOBILE_FILE.parent.mkdir(parents=True, exist_ok=True)
    if SEEN_MOBILE_FILE.exists():
        try:
            return set(json.loads(SEEN_MOBILE_FILE.read_text()))
        except Exception:
            return set()
    return set()


def save_seen(seen: set) -> None:
    SEEN_MOBILE_FILE.write_text(json.dumps(list(seen)))


def detect_platform(game: dict) -> str:
    """Deteksi platform dari field 'platforms'."""
    platforms = game.get("platforms", "").lower()
    has_android = "android" in platforms
    has_ios = "ios" in platforms or "iphone" in platforms or "ipad" in platforms
    if has_android and has_ios:
        return "both"
    if has_android:
        return "android"
    if has_ios:
        return "ios"
    return "both"  # default kalau tidak jelas


# ─────────────────────────────────────────────
# COG UTAMA
# ─────────────────────────────────────────────
class MobileGameNotifier(commands.Cog):
    """Cog notifikasi game gratis Android & iOS untuk Cellyn Store."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.seen: set = load_seen()
        self.check_mobile_games.start()
        logger.info("[MobileGameNotifier] Cog loaded, loop dimulai.")

    def cog_unload(self):
        self.check_mobile_games.cancel()

    # ── Loop utama ────────────────────────────
    @tasks.loop(minutes=15)
    async def check_mobile_games(self):
        channel = self.bot.get_channel(MOBILE_GAME_CHANNEL_ID)
        if not channel:
            logger.warning(f"[MobileGameNotifier] Channel ID {MOBILE_GAME_CHANNEL_ID} tidak ditemukan.")
            return

        games = await self._fetch_games()
        if not games:
            return

        new_games = [g for g in games if str(g.get("id")) not in self.seen]

        for game in new_games:
            try:
                embed = self._build_embed(game)
                await channel.send(embed=embed)
                self.seen.add(str(game.get("id")))
                logger.info(f"[MobileGameNotifier] Posted: {game.get('title')} (id={game.get('id')})")
            except Exception as e:
                logger.error(f"[MobileGameNotifier] Gagal kirim embed: {e}")

        if new_games:
            save_seen(self.seen)

    @check_mobile_games.before_loop
    async def before_check(self):
        await self.bot.wait_until_ready()

    # ── Fetch dari GamerPower API ─────────────
    async def _fetch_games(self) -> list[dict]:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    GAMERPOWER_API,
                    timeout=aiohttp.ClientTimeout(total=10),
                    headers={"User-Agent": "CellynStoreBot/1.0"}
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json(content_type=None)
                        # API return list atau dict dengan status 201 kalau kosong
                        if isinstance(data, list):
                            return data
                    elif resp.status == 201:
                        logger.info("[MobileGameNotifier] Tidak ada giveaway aktif saat ini.")
                    else:
                        logger.warning(f"[MobileGameNotifier] API status: {resp.status}")
        except Exception as e:
            logger.warning(f"[MobileGameNotifier] Fetch error: {e}")
        return []

    # ── Builder embed ─────────────────────────
    def _build_embed(self, game: dict) -> discord.Embed:
        platform = detect_platform(game)
        color = PLATFORM_COLORS.get(platform, 0xF89406)

        # Label platform
        platform_labels = {
            "android": "Android",
            "ios": "iOS",
            "both": "Android & iOS",
        }
        platform_label = platform_labels.get(platform, "Mobile")

        # Judul
        title = game.get("title", "Unknown Game")
        giveaway_url = game.get("open_giveaway_url") or game.get("giveaway_url") or "https://www.gamerpower.com"

        embed = discord.Embed(
            title=f"📱 {title}",
            url=giveaway_url,
            description=game.get("description") or "Game mobile ini sedang gratis! Klaim sekarang.",
            color=color,
            timestamp=datetime.now(timezone.utc),
        )

        embed.set_author(
            name=f"Game Gratis — {platform_label}",
            icon_url="https://www.gamerpower.com/assets/images/logo-100.png",
        )

        # Thumbnail
        if game.get("thumbnail"):
            embed.set_image(url=game["thumbnail"])

        # Worth (nilai game)
        worth = game.get("worth", "N/A")
        if worth and worth != "N/A":
            embed.add_field(name="💰 Nilai", value=worth, inline=True)

        # Platform detail
        platforms_raw = game.get("platforms", platform_label)
        embed.add_field(name="📱 Platform", value=platforms_raw, inline=True)

        # Tanggal berakhir
        end_date = game.get("end_date", "").strip()
        if end_date and end_date.upper() != "N/A":
            try:
                dt = datetime.strptime(end_date, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
                embed.add_field(
                    name="⏳ Gratis sampai",
                    value=discord.utils.format_dt(dt, style="F"),
                    inline=False,
                )
            except Exception:
                embed.add_field(name="⏳ Gratis sampai", value=end_date, inline=False)

        embed.add_field(
            name="🔗 Klaim Sekarang",
            value=f"[Klik di sini]({giveaway_url})",
            inline=False,
        )

        embed.set_footer(text="Cellyn Store • Mobile Free Games | Data by GamerPower.com")

        return embed

    # ── Command manual ────────────────────────
    @commands.command(name="mobilegames", aliases=["mg", "androidios"])
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def mobile_games_command(self, ctx: commands.Context):
        """Cek game gratis Android & iOS sekarang."""
        msg = await ctx.send("🔍 Mengecek game gratis mobile...")

        games = await self._fetch_games()

        if not games:
            await msg.edit(content="😔 Tidak ada game gratis mobile ditemukan saat ini.")
            return

        await msg.edit(content=f"✅ Ditemukan **{len(games)}** game gratis mobile:")
        for game in games[:5]:
            embed = self._build_embed(game)
            await ctx.send(embed=embed)


# ─────────────────────────────────────────────
# SETUP
# ─────────────────────────────────────────────
async def setup(bot: commands.Bot):
    await bot.add_cog(MobileGameNotifier(bot))
