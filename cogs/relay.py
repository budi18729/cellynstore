import os
import asyncio
import discord
from discord.ext import commands
import aiohttp
from utils.config import ADMIN_ROLE_ID
from utils.db import get_conn

RELAY_SOURCE_CHANNEL_ID = int(os.getenv("RELAY_SOURCE_CHANNEL_ID", "0"))
RELAY_WEBHOOK_URL = os.getenv("RELAY_WEBHOOK_URL", "")
RELAY_INCLUDE_BOT = os.getenv("RELAY_INCLUDE_BOT", "1") == "1"
RELAY_ALLOW_MENTIONS = os.getenv("RELAY_ALLOW_MENTIONS", "0") == "1"


def _get_setting(key):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT value FROM bot_state WHERE key=?", (key,))
    row = c.fetchone()
    conn.close()
    return row["value"] if row else None


def _set_setting(key, value):
    conn = get_conn()
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO bot_state (key, value) VALUES (?,?)", (key, str(value)))
    conn.commit()
    conn.close()


def _relay_enabled():
    val = _get_setting("relay_enabled")
    if val is None:
        return True
    return str(val).lower() in ("1", "true", "yes", "y", "on")


def _can_run():
    return _relay_enabled() and RELAY_SOURCE_CHANNEL_ID and RELAY_WEBHOOK_URL


def _embed_dict(embed: discord.Embed):
    try:
        return embed.to_dict()
    except Exception:
        return None


def _allowed_mentions():
    if RELAY_ALLOW_MENTIONS:
        return {"parse": ["users", "roles", "everyone"]}
    return {"parse": []}


class RelayCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._session = None

    async def cog_load(self):
        if not _can_run():
            print("[Relay] Disabled (missing RELAY_SOURCE_CHANNEL_ID or RELAY_WEBHOOK_URL)")
            return
        self._session = aiohttp.ClientSession()
        print(f"[Relay] Enabled for channel {RELAY_SOURCE_CHANNEL_ID}")

    def _is_admin(self, member: discord.Member) -> bool:
        return any(r.id == ADMIN_ROLE_ID for r in member.roles)

    @commands.command(name="relay")
    async def relay_cmd(self, ctx: commands.Context, action: str = ""):
        if not isinstance(ctx.author, discord.Member) or not self._is_admin(ctx.author):
            return await ctx.reply("❌ Admin only.")

        action = action.lower().strip()
        if action in ("on", "enable"):
            if not (RELAY_SOURCE_CHANNEL_ID and RELAY_WEBHOOK_URL):
                return await ctx.reply("⚠️ Relay belum bisa diaktifkan. Cek `RELAY_SOURCE_CHANNEL_ID` dan `RELAY_WEBHOOK_URL` di .env.")
            _set_setting("relay_enabled", "1")
            if self._session is None:
                self._session = aiohttp.ClientSession()
            return await ctx.reply("✅ Relay diaktifkan.")
        if action in ("off", "disable"):
            _set_setting("relay_enabled", "0")
            if self._session:
                await self._session.close()
                self._session = None
            return await ctx.reply("✅ Relay dimatikan.")
        if action in ("status", ""):
            status = "ON" if _relay_enabled() else "OFF"
            return await ctx.reply(f"ℹ️ Relay status: **{status}**")
        return await ctx.reply("Gunakan: `!relay on`, `!relay off`, atau `!relay status`.")

    async def cog_unload(self):
        if self._session:
            await self._session.close()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not _can_run():
            return
        if message.channel.id != RELAY_SOURCE_CHANNEL_ID:
            return
        if not RELAY_INCLUDE_BOT and message.author.bot:
            return

        # Build payload
        embeds = [e for e in ([_embed_dict(e) for e in message.embeds] if message.embeds else []) if e]
        content = message.content or ""

        # Forward attachment URLs if present
        if message.attachments:
            urls = "\n".join(a.url for a in message.attachments)
            content = f"{content}\n{urls}".strip()

        payload = {
            "content": content,
            "embeds": embeds[:10],
            "allowed_mentions": _allowed_mentions(),
            "username": message.author.display_name,
            "avatar_url": message.author.display_avatar.url,
        }

        try:
            async with self._session.post(RELAY_WEBHOOK_URL, json=payload, timeout=10) as resp:
                if resp.status >= 400:
                    text = await resp.text()
                    print(f"[Relay] Webhook error {resp.status}: {text[:200]}")
        except Exception as e:
            print(f"[Relay] Failed: {e}")


async def setup(bot: commands.Bot):
    await bot.add_cog(RelayCog(bot))
    print("Cog Relay siap.")
