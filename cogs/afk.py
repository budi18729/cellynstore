"""
cogs/afk.py — AFK System
!afk [alasan] — set AFK
Kirim pesan = hapus AFK otomatis
Mention user AFK = bot kasih notif
AFK state persistent di SQLite (table: afk_users)
"""
import discord
import datetime
from discord.ext import commands
from utils.db import get_conn

def init_afk_table():
    conn = get_conn()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS afk_users (
            user_id       INTEGER PRIMARY KEY,
            reason        TEXT DEFAULT 'AFK',
            original_nick TEXT,
            afk_since     TEXT
        )
    ''')
    try:
        c.execute('ALTER TABLE afk_users ADD COLUMN afk_since TEXT')
    except Exception as e:
        if 'duplicate column' not in str(e).lower():
            print(f'[AFK] Migration: {e}')
    conn.commit()
    conn.close()

def save_afk(user_id: int, reason: str, original_nick: str, afk_since: str = None):
    if afk_since is None:
        afk_since = datetime.datetime.utcnow().isoformat()
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "INSERT OR REPLACE INTO afk_users (user_id, reason, original_nick, afk_since) VALUES (?, ?, ?, ?)",
        (user_id, reason, original_nick, afk_since)
    )
    conn.commit()
    conn.close()

def delete_afk(user_id: int):
    conn = get_conn()
    c = conn.cursor()
    c.execute("DELETE FROM afk_users WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def load_all_afk() -> dict:
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT user_id, reason, original_nick, afk_since FROM afk_users")
    rows = c.fetchall()
    conn.close()
    return {row["user_id"]: {"reason": row["reason"], "original_nick": row["original_nick"], "afk_since": row["afk_since"]} for row in rows}


class AFK(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        init_afk_table()
        self.afk_users = load_all_afk()
        self._notify_cooldown = {}  # (channel_id, user_id) -> last_ts
        print(f"[AFK] Loaded {len(self.afk_users)} AFK user(s) dari DB.")

    @commands.command(name="afk")
    async def afk_cmd(self, ctx, *, reason: str = "AFK"):
        user = ctx.author
        if user.id in self.afk_users:
            await ctx.send(f"{user.mention} kamu sudah AFK.", delete_after=5)
            return

        original_nick = user.display_name
        afk_since = datetime.datetime.utcnow().isoformat()
        self.afk_users[user.id] = {"reason": reason, "original_nick": original_nick, "afk_since": afk_since}
        save_afk(user.id, reason, original_nick, afk_since)

        await ctx.message.delete()
        await ctx.send(f"{user.mention} sekarang AFK: **{reason}**", delete_after=5)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        if not message.guild:
            return

        # Cek apakah user yang kirim pesan lagi AFK → hapus AFK
        if message.author.id in self.afk_users:
            # Skip kalau pesannya adalah command !afk
            if message.content.strip().startswith("!afk"):
                return

            data = self.afk_users.pop(message.author.id)
            delete_afk(message.author.id)

            await message.channel.send(
                f"Selamat datang kembali {message.author.mention}, kamu sudah tidak AFK."
            )

        # Cek mention ke user yang AFK
        if message.mentions:
            notified = set()
            for mentioned in message.mentions:
                if mentioned.bot:
                    continue
                if mentioned.id in self.afk_users and mentioned.id not in notified:
                    # Cooldown per channel+user untuk mencegah spam
                    key = (message.channel.id, mentioned.id)
                    now_ts = datetime.datetime.utcnow().timestamp()
                    last_ts = self._notify_cooldown.get(key, 0)
                    if now_ts - last_ts < 60:
                        continue
                    self._notify_cooldown[key] = now_ts

                    data = self.afk_users[mentioned.id]
                    afk_since = data.get("afk_since")
                    durasi = "baru saja"
                    if afk_since:
                        try:
                            delta = datetime.datetime.utcnow() - datetime.datetime.fromisoformat(afk_since)
                            total = int(delta.total_seconds())
                            hari = total // 86400
                            jam = (total % 86400) // 3600
                            menit = (total % 3600) // 60
                            if total < 60:
                                durasi = "baru saja"
                            elif total < 3600:
                                durasi = f"{menit} menit lalu"
                            elif total < 86400:
                                durasi = f"{jam} jam {menit} menit lalu"
                            else:
                                durasi = f"{hari} hari {jam} jam lalu"
                        except Exception:
                            pass
                    await message.channel.send(
                        f"**{mentioned.display_name}** sedang AFK: {data['reason']} • {durasi}"
                    )
                    notified.add(mentioned.id)


async def setup(bot):
    await bot.add_cog(AFK(bot))
    print("Cog AFK siap.")
