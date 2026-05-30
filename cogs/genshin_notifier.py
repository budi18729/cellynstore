"""
Cellyn Store - Genshin Impact Event Notifier Cog
Auto-post event, banner, dan redeem code Genshin Impact
ke channel komunitas setiap 1 jam.

Data source: api.ennead.cc (torikushiii/hoyoverse-api)
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
GENSHIN_CHANNEL_ID = int(os.getenv("GENSHIN_CHANNEL_ID", "0"))
SEEN_GENSHIN_FILE  = Path("data/seen_genshin.json")

BASE_URL = "https://api.ennead.cc/mihoyo/genshin"

# Warna embed per tipe konten
COLOR_EVENT   = 0xE8C84A   # emas Genshin
COLOR_BANNER  = 0x7B68EE   # ungu wish
COLOR_CODE    = 0x4CAF50   # hijau redeem
COLOR_NEWS    = 0x29B6F6   # biru info

GENSHIN_ICON = "https://upload-os-bbs.hoyolab.com/upload/2021/11/08/d3ea9e5b672bdf8e4c05bf4f2ffc9e23_4115070455905292085.png"

ELEMENT_EMOJI = {
    "Pyro":     "🔥",
    "Hydro":    "💧",
    "Anemo":    "🌪️",
    "Electro":  "⚡",
    "Dendro":   "🌿",
    "Cryo":     "❄️",
    "Geo":      "🪨",
}


# ─────────────────────────────────────────────
# HELPER
# ─────────────────────────────────────────────
def load_seen() -> dict:
    SEEN_GENSHIN_FILE.parent.mkdir(parents=True, exist_ok=True)
    if SEEN_GENSHIN_FILE.exists():
        try:
            return json.loads(SEEN_GENSHIN_FILE.read_text())
        except Exception:
            pass
    return {"events": [], "banners": [], "codes": [], "news": []}


def save_seen(seen: dict) -> None:
    SEEN_GENSHIN_FILE.write_text(json.dumps(seen))


def fmt_time(ts: int) -> str:
    """Unix timestamp → Discord relative time."""
    try:
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        return discord.utils.format_dt(dt, style="F")
    except Exception:
        return "N/A"


# ─────────────────────────────────────────────
# COG UTAMA
# ─────────────────────────────────────────────
class GenshinNotifier(commands.Cog):
    """Cog notifikasi event Genshin Impact untuk Cellyn Store."""

    def __init__(self, bot: commands.Bot):
        self.bot  = bot
        self.seen = load_seen()
        self.check_genshin.start()
        logger.info("[GenshinNotifier] Cog loaded, loop dimulai.")

    def cog_unload(self):
        self.check_genshin.cancel()

    # ── Loop utama — cek tiap 1 jam ──────────
    @tasks.loop(hours=1)
    async def check_genshin(self):
        channel = self.bot.get_channel(GENSHIN_CHANNEL_ID)
        if not channel:
            logger.warning(f"[GenshinNotifier] Channel ID {GENSHIN_CHANNEL_ID} tidak ditemukan.")
            return

        async with aiohttp.ClientSession() as session:
            await self._check_calendar(session, channel)
            await self._check_codes(session, channel)
            await self._check_news(session, channel)

        save_seen(self.seen)

    @check_genshin.before_loop
    async def before_check(self):
        await self.bot.wait_until_ready()

    # ── Fetch helper ──────────────────────────
    async def _get(self, session: aiohttp.ClientSession, endpoint: str, params: dict = None):
        try:
            url = f"{BASE_URL}/{endpoint}"
            async with session.get(
                url,
                params=params,
                timeout=aiohttp.ClientTimeout(total=10),
                headers={"User-Agent": "CellynStoreBot/1.0"},
            ) as resp:
                if resp.status == 200:
                    return await resp.json(content_type=None)
        except Exception as e:
            logger.warning(f"[GenshinNotifier] Fetch /{endpoint} error: {e}")
        return None

    # ── Cek calendar (events + banners) ──────
    async def _check_calendar(self, session, channel):
        data = await self._get(session, "calendar")
        if not data:
            return

        # Events baru
        for event in data.get("events", []):
            eid = str(event.get("id"))
            if eid in self.seen["events"]:
                continue
            embed = self._build_event_embed(event)
            await channel.send(embed=embed)
            self.seen["events"].append(eid)
            logger.info(f"[GenshinNotifier] Event posted: {event.get('name')}")

        # Banner baru
        for banner in data.get("banners", []):
            bid = str(banner.get("id"))
            if bid in self.seen["banners"]:
                continue
            embed = self._build_banner_embed(banner)
            await channel.send(embed=embed)
            self.seen["banners"].append(bid)
            logger.info(f"[GenshinNotifier] Banner posted: {banner.get('name')}")

    # ── Cek redeem codes ─────────────────────
    async def _check_codes(self, session, channel):
        data = await self._get(session, "codes")
        if not data:
            return

        active_codes = data.get("active", [])
        new_codes = [c for c in active_codes if c.get("code") not in self.seen["codes"]]

        if not new_codes:
            return

        embed = self._build_codes_embed(new_codes)
        await channel.send(embed=embed)

        for c in new_codes:
            self.seen["codes"].append(c.get("code"))
        logger.info(f"[GenshinNotifier] {len(new_codes)} kode baru dipost.")

    # ── Cek news/events dari HoYoLAB ─────────
    async def _check_news(self, session, channel):
        data = await self._get(session, "news/events", params={"lang": "id-id"})
        if not data or not isinstance(data, list):
            return

        # Ambil 3 berita terbaru aja
        for article in data[:3]:
            nid = str(article.get("id"))
            if nid in self.seen["news"]:
                continue
            embed = self._build_news_embed(article)
            await channel.send(embed=embed)
            self.seen["news"].append(nid)
            logger.info(f"[GenshinNotifier] News posted: {article.get('title')}")

    # ── Embed builders ────────────────────────

    def _build_event_embed(self, event: dict) -> discord.Embed:
        embed = discord.Embed(
            title=f"🎉 {event.get('name', 'Event Baru')}",
            description=event.get("description", ""),
            color=COLOR_EVENT,
        )
        embed.set_author(name="Genshin Impact — Event", icon_url=GENSHIN_ICON)

        if event.get("image_url"):
            embed.set_image(url=event["image_url"])

        start = event.get("start_time")
        end   = event.get("end_time")
        if start:
            embed.add_field(name="🕐 Mulai", value=fmt_time(start), inline=True)
        if end:
            embed.add_field(name="⏳ Berakhir", value=fmt_time(end), inline=True)

        # Rewards
        rewards = event.get("rewards", [])
        if rewards:
            reward_text = " • ".join(
                f"{r.get('name')} x{r.get('amount', '?')}" for r in rewards[:5]
            )
            embed.add_field(name="🎁 Reward", value=reward_text, inline=False)

        embed.set_footer(text="Cellyn Store • Genshin Impact Events")
        return embed

    def _build_banner_embed(self, banner: dict) -> discord.Embed:
        embed = discord.Embed(
            title=f"✨ Banner: {banner.get('name', 'Banner Baru')}",
            color=COLOR_BANNER,
        )
        embed.set_author(name="Genshin Impact — Wish Banner", icon_url=GENSHIN_ICON)

        version = banner.get("version", "")
        if version:
            embed.description = f"Versi **{version}**"

        # Characters
        chars = banner.get("characters", [])
        if chars:
            char_list = []
            for c in chars:
                elem  = c.get("element", "")
                emoji = ELEMENT_EMOJI.get(elem, "")
                stars = "⭐" * c.get("rarity", 4)
                char_list.append(f"{emoji} **{c.get('name')}** {stars}")
            embed.add_field(name="👤 Karakter", value="\n".join(char_list), inline=True)

        # Weapons
        weapons = banner.get("weapons", [])
        if weapons:
            wpn_list = [
                f"🗡️ **{w.get('name')}** {'⭐' * w.get('rarity', 4)}"
                for w in weapons
            ]
            embed.add_field(name="⚔️ Senjata", value="\n".join(wpn_list), inline=True)

        start = banner.get("start_time")
        end   = banner.get("end_time")
        if start:
            embed.add_field(name="🕐 Mulai", value=fmt_time(start), inline=False)
        if end:
            embed.add_field(name="⏳ Berakhir", value=fmt_time(end), inline=True)

        # Thumbnail karakter utama
        if chars and chars[0].get("icon"):
            embed.set_thumbnail(url=chars[0]["icon"])

        embed.set_footer(text="Cellyn Store • Genshin Impact Banner")
        return embed

    def _build_codes_embed(self, codes: list) -> discord.Embed:
        embed = discord.Embed(
            title="🎁 Redeem Code Genshin Impact Baru!",
            color=COLOR_CODE,
        )
        embed.set_author(name="Genshin Impact — Redeem Codes", icon_url=GENSHIN_ICON)

        for c in codes:
            code    = c.get("code", "???")
            rewards = ", ".join(c.get("rewards", []))
            embed.add_field(
                name=f"`{code}`",
                value=f"🎁 {rewards}\n[Redeem di sini](https://genshin.hoyoverse.com/en/gift?code={code})",
                inline=False,
            )

        embed.set_footer(text="Cellyn Store • Genshin Impact | Kode bisa expired kapan saja!")
        return embed

    def _build_news_embed(self, article: dict) -> discord.Embed:
        embed = discord.Embed(
            title=article.get("title", "Berita Genshin"),
            url=article.get("url", ""),
            description=article.get("description", "")[:300] + "..." if article.get("description") else "",
            color=COLOR_NEWS,
            timestamp=datetime.fromtimestamp(article.get("created_at", 0), tz=timezone.utc),
        )
        embed.set_author(name="Genshin Impact — HoYoLAB News", icon_url=GENSHIN_ICON)

        if article.get("banner"):
            embed.set_image(url=article["banner"])

        embed.add_field(
            name="🔗 Baca Selengkapnya",
            value=f"[Klik di sini]({article.get('url', '#')})",
            inline=False,
        )
        embed.set_footer(text="Cellyn Store • Genshin Impact")
        return embed

    # ── Command manual ────────────────────────
    @commands.group(name="genshin", aliases=["gi"], invoke_without_command=True)
    async def genshin_group(self, ctx: commands.Context):
        """Perintah Genshin Impact. Gunakan subcommand: events, banners, codes."""
        await ctx.send(
            "📖 **Subcommand tersedia:**\n"
            "`!genshin events` — lihat event aktif\n"
            "`!genshin banners` — lihat banner aktif\n"
            "`!genshin codes` — lihat redeem code aktif"
        )

    @genshin_group.command(name="events")
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def genshin_events(self, ctx: commands.Context):
        """Lihat event Genshin aktif."""
        async with aiohttp.ClientSession() as session:
            data = await self._get(session, "calendar")
        if not data or not data.get("events"):
            await ctx.send("😔 Tidak ada event aktif saat ini.")
            return
        for event in data["events"][:3]:
            await ctx.send(embed=self._build_event_embed(event))

    @genshin_group.command(name="banners")
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def genshin_banners(self, ctx: commands.Context):
        """Lihat banner wish Genshin aktif."""
        async with aiohttp.ClientSession() as session:
            data = await self._get(session, "calendar")
        if not data or not data.get("banners"):
            await ctx.send("😔 Tidak ada banner aktif saat ini.")
            return
        for banner in data["banners"][:3]:
            await ctx.send(embed=self._build_banner_embed(banner))

    @genshin_group.command(name="codes")
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def genshin_codes(self, ctx: commands.Context):
        """Lihat redeem code Genshin aktif."""
        async with aiohttp.ClientSession() as session:
            data = await self._get(session, "codes")
        if not data or not data.get("active"):
            await ctx.send("😔 Tidak ada kode aktif saat ini.")
            return
        await ctx.send(embed=self._build_codes_embed(data["active"]))


# ─────────────────────────────────────────────
# SETUP
# ─────────────────────────────────────────────
async def setup(bot: commands.Bot):
    await bot.add_cog(GenshinNotifier(bot))
