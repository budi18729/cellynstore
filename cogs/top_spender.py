"""
Cellyn Store - Top Spender Monthly Leaderboard
- Auto update & edit embed tiap 30 menit
- Top 20 ditampilkan
- Role ID 1508950886251106517 diberikan ke top 1-10
- Reset & announce tiap awal bulan
"""

import datetime
import discord
from discord import app_commands
from discord.ext import commands, tasks
from utils.config import ADMIN_ROLE_ID, STORE_NAME
from utils.db import get_conn

TOP_SPENDER_ROLE_ID = 1508950886251106517
TOP_SPENDER_TOP_N   = 10
LEADERBOARD_LIMIT   = 20

MEDAL = {1: "🥇", 2: "🥈", 3: "🥉", 4: "4️⃣", 5: "5️⃣", 6: "6️⃣", 7: "7️⃣", 8: "8️⃣", 9: "9️⃣", 10: "🔟"}


# ─────────────────────────────────────────────
# DB helpers
# ─────────────────────────────────────────────
def _init_tables():
    conn = get_conn()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS manual_spending (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER NOT NULL,
            nominal    INTEGER NOT NULL,
            note       TEXT,
            added_by   INTEGER,
            added_at   TEXT NOT NULL
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS bot_state (
            key   TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    conn.commit()
    conn.close()


def _get_setting(key):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT value FROM bot_state WHERE key=?", (key,))
    row = c.fetchone()
    conn.close()
    return row['value'] if row else None


def _set_setting(key, value):
    conn = get_conn()
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO bot_state (key, value) VALUES (?,?)", (key, value))
    conn.commit()
    conn.close()


def get_top_spenders(year: int, month: int, limit: int = 20) -> list[dict]:
    conn = get_conn()
    c = conn.cursor()

    start = f"{year:04d}-{month:02d}-01"
    end   = f"{year+1:04d}-01-01" if month == 12 else f"{year:04d}-{month+1:02d}-01"

    c.execute('''
        SELECT user_id, SUM(nominal) as total
        FROM transaction_log
        WHERE user_id IS NOT NULL
          AND closed_at >= ? AND closed_at < ?
        GROUP BY user_id
    ''', (start, end))
    combined = {row['user_id']: row['total'] for row in c.fetchall()}

    c.execute('''
        SELECT user_id, SUM(nominal) as total
        FROM manual_spending
        WHERE added_at >= ? AND added_at < ?
        GROUP BY user_id
    ''', (start, end))
    for row in c.fetchall():
        combined[row['user_id']] = combined.get(row['user_id'], 0) + row['total']

    conn.close()

    sorted_list = sorted(combined.items(), key=lambda x: x[1], reverse=True)
    return [{"user_id": uid, "total": total} for uid, total in sorted_list[:limit]]


# ─────────────────────────────────────────────
# COG
# ─────────────────────────────────────────────
class TopSpender(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        _init_tables()
        self._channel_id = int(_get_setting("topspender_channel_id") or 0) or None
        self._message_id = int(_get_setting("topspender_message_id") or 0) or None
        self.update_loop.start()

    def cog_unload(self):
        self.update_loop.cancel()

    # ── Loop tiap 30 menit ────────────────────
    @tasks.loop(minutes=30)
    async def update_loop(self):
        if not self._channel_id:
            return

        now = datetime.datetime.now(datetime.timezone.utc)
        month_key = f"{now.year}-{now.month:02d}"

        # Cek bulan baru — announce pemenang bulan lalu
        last_reset = _get_setting("topspender_last_reset")
        if last_reset != month_key and now.day == 1:
            if now.month == 1:
                prev_year, prev_month = now.year - 1, 12
            else:
                prev_year, prev_month = now.year, now.month - 1
            await self._announce_winner(prev_year, prev_month)
            _set_setting("topspender_last_reset", month_key)
            self._message_id = None
            _set_setting("topspender_message_id", "")

        await self._update_leaderboard(now.year, now.month)

    @update_loop.before_loop
    async def before_loop(self):
        await self.bot.wait_until_ready()

    # ── Update/edit embed ─────────────────────
    async def _update_leaderboard(self, year: int, month: int):
        channel = self.bot.get_channel(self._channel_id)
        if not channel:
            return

        spenders = get_top_spenders(year, month, LEADERBOARD_LIMIT)
        month_name = datetime.date(year, month, 1).strftime("%B %Y")
        embed = self._build_embed(spenders, month_name, channel.guild)

        try:
            if self._message_id:
                try:
                    msg = await channel.fetch_message(self._message_id)
                    await msg.edit(embed=embed)
                    await self._update_roles(spenders, channel.guild)
                    return
                except discord.NotFound:
                    self._message_id = None

            msg = await channel.send(embed=embed)
            self._message_id = msg.id
            _set_setting("topspender_message_id", str(msg.id))
            await self._update_roles(spenders, channel.guild)

        except Exception as e:
            print(f"[TopSpender] Update error: {e}")

    # ── Announce pemenang bulan lalu ──────────
    async def _announce_winner(self, year: int, month: int):
        channel = self.bot.get_channel(self._channel_id)
        if not channel:
            return

        spenders = get_top_spenders(year, month, TOP_SPENDER_TOP_N)
        month_name = datetime.date(year, month, 1).strftime("%B %Y")
        if not spenders:
            return

        mentions = []
        for s in spenders:
            m = channel.guild.get_member(s['user_id'])
            if m:
                mentions.append(m.mention)

        if mentions:
            await channel.send(
                f"🎉 **Top Spender {month_name} telah ditentukan!**\n"
                f"Selamat untuk: {', '.join(mentions)}\n"
                f"Role <@&{TOP_SPENDER_ROLE_ID}> telah diberikan!"
            )

    # ── Update role top 1-10 ──────────────────
    async def _update_roles(self, spenders: list[dict], guild: discord.Guild):
        top_role = guild.get_role(TOP_SPENDER_ROLE_ID)
        if not top_role:
            return

        entitled_ids = {s['user_id'] for s in spenders[:TOP_SPENDER_TOP_N]}

        for member in guild.members:
            has_role    = top_role in member.roles
            should_have = member.id in entitled_ids
            try:
                if should_have and not has_role:
                    await member.add_roles(top_role, reason="Top Spender update")
                elif not should_have and has_role:
                    await member.remove_roles(top_role, reason="Top Spender update")
            except Exception as e:
                print(f"[TopSpender] Role error {member.id}: {e}")

    # ── Build embed ───────────────────────────
    def _build_embed(self, spenders: list[dict], month_name: str,
                     guild: discord.Guild) -> discord.Embed:
        embed = discord.Embed(
            title=f"🏆 Top Spender — {month_name}",
            description=f"Pelanggan terbaik {STORE_NAME} bulan ini!\n*(diperbarui tiap 30 menit)*",
            color=0xF0A500,
            timestamp=datetime.datetime.now(datetime.timezone.utc),
        )

        if not spenders:
            embed.add_field(name="\u200b", value="Belum ada data transaksi bulan ini.", inline=False)
        else:
            text = ""
            for i, s in enumerate(spenders, 1):
                medal  = MEDAL.get(i, f"`#{i:02d}`")
                member = guild.get_member(s['user_id'])
                name   = member.display_name if member else f"User {s['user_id']}"
                crown  = " 👑" if i <= TOP_SPENDER_TOP_N else ""
                text  += f"{medal} **{name}**{crown} — Rp {s['total']:,}\n"
            embed.add_field(name="\u200b", value=text, inline=False)

        embed.set_footer(text=f"{STORE_NAME} • Reset tiap awal bulan")
        return embed

    # ── Slash commands ────────────────────────

    @app_commands.command(name="topspender", description="Lihat leaderboard top spender bulan ini")
    async def topspender(self, interaction: discord.Interaction):
        await interaction.response.defer()
        now = datetime.datetime.now(datetime.timezone.utc)
        spenders = get_top_spenders(now.year, now.month, LEADERBOARD_LIMIT)
        month_name = datetime.date(now.year, now.month, 1).strftime("%B %Y")
        embed = self._build_embed(spenders, month_name, interaction.guild)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="addspending", description="[ADMIN] Tambah manual spending untuk member")
    @app_commands.describe(member="Member yang ditambah spendingnya", nominal="Jumlah nominal (Rupiah)", note="Catatan (opsional)")
    async def addspending(self, interaction: discord.Interaction,
                          member: discord.Member, nominal: int, note: str = ""):
        if not any(r.id == ADMIN_ROLE_ID for r in interaction.user.roles):
            await interaction.response.send_message("❌ Admin only!", ephemeral=True)
            return
        conn = get_conn()
        c = conn.cursor()
        c.execute(
            "INSERT INTO manual_spending (user_id, nominal, note, added_by, added_at) VALUES (?,?,?,?,?)",
            (member.id, nominal, note, interaction.user.id,
             datetime.datetime.now(datetime.timezone.utc).isoformat())
        )
        conn.commit()
        conn.close()
        await interaction.response.send_message(
            f"✅ Ditambahkan spending **Rp {nominal:,}** untuk {member.mention}"
            + (f" — `{note}`" if note else ""),
            ephemeral=True
        )
        now = datetime.datetime.now(datetime.timezone.utc)
        await self._update_leaderboard(now.year, now.month)

    @app_commands.command(name="subspend", description="[ADMIN] Kurangi spending manual member")
    @app_commands.describe(member="Member yang dikurangi spendingnya", nominal="Jumlah nominal untuk dikurangi (Rupiah)", note="Catatan (opsional)")
    async def subspend(self, interaction: discord.Interaction,
                       member: discord.Member, nominal: int, note: str = ""):
        if not any(r.id == ADMIN_ROLE_ID for r in interaction.user.roles):
            await interaction.response.send_message("❌ Admin only!", ephemeral=True)
            return
        conn = get_conn()
        c = conn.cursor()
        c.execute(
            "INSERT INTO manual_spending (user_id, nominal, note, added_by, added_at) VALUES (?,?,?,?,?)",
            (member.id, -nominal, note, interaction.user.id,
             datetime.datetime.now(datetime.timezone.utc).isoformat())
        )
        conn.commit()
        conn.close()
        await interaction.response.send_message(
            f"✅ Berhasil mengurangi spending **Rp {nominal:,}** dari {member.mention}"
            + (f" — `{note}`" if note else ""),
            ephemeral=True
        )
        now = datetime.datetime.now(datetime.timezone.utc)
        await self._update_leaderboard(now.year, now.month)

    @app_commands.command(name="refreshspender", description="[ADMIN] Force update leaderboard sekarang")
    async def refreshspender(self, interaction: discord.Interaction):
        if not any(r.id == ADMIN_ROLE_ID for r in interaction.user.roles):
            await interaction.response.send_message("❌ Admin only!", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        now = datetime.datetime.now(datetime.timezone.utc)
        await self._update_leaderboard(now.year, now.month)
        await interaction.followup.send("✅ Leaderboard diperbarui.", ephemeral=True)

    @app_commands.command(name="settopspenderchannel", description="[ADMIN] Set channel untuk leaderboard top spender")
    @app_commands.describe(channel="Channel tujuan leaderboard")
    async def set_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        if not any(r.id == ADMIN_ROLE_ID for r in interaction.user.roles):
            await interaction.response.send_message("❌ Admin only!", ephemeral=True)
            return
        self._channel_id = channel.id
        self._message_id = None
        _set_setting("topspender_channel_id", str(channel.id))
        _set_setting("topspender_message_id", "")
        await interaction.response.send_message(
            f"✅ Channel leaderboard diset ke {channel.mention}", ephemeral=True
        )

    @app_commands.command(name="forcereset", description="[ADMIN] Force post leaderboard bulan tertentu")
    @app_commands.describe(year="Tahun (misal: 2026)", month="Bulan (1-12)")
    async def forcereset(self, interaction: discord.Interaction, year: int, month: int):
        if not any(r.id == ADMIN_ROLE_ID for r in interaction.user.roles):
            await interaction.response.send_message("❌ Admin only!", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        await self._post_leaderboard(year, month, auto=True)
        await interaction.followup.send(
            f"✅ Leaderboard {month:02d}/{year} berhasil dipost.", ephemeral=True
        )

    # Tetap ada untuk backward compat dengan forcereset
    async def _post_leaderboard(self, year: int, month: int, auto: bool = False,
                                 channel: discord.TextChannel = None):
        ch = channel or (self.bot.get_channel(self._channel_id) if self._channel_id else None)
        if not ch:
            return
        spenders = get_top_spenders(year, month, LEADERBOARD_LIMIT)
        month_name = datetime.date(year, month, 1).strftime("%B %Y")
        embed = self._build_embed(spenders, month_name, ch.guild)
        await ch.send(embed=embed)
        if auto:
            await self._announce_winner(year, month)
            await self._update_roles(spenders, ch.guild)


async def setup(bot: commands.Bot):
    await bot.add_cog(TopSpender(bot))
