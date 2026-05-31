"""Laporan harian otomatis (#7).

Tiap hari bot memposting ringkasan transaksi hari sebelumnya ke channel laporan:
omzet total, jumlah transaksi, rincian per layanan, dan ringkasan rating.

Sumber data: transaction_log + reviews (lihat utils.reviews.get_daily_report).
Admin juga bisa memanggil manual via `!laporan [YYYY-MM-DD]`.
"""
import datetime

import discord
from discord.ext import commands, tasks

from utils.config import ADMIN_ROLE_ID, STORE_NAME, DAILY_REPORT_CHANNEL_ID
from utils import reviews as rv
from utils.db import get_conn

COLOR_REPORT = 0x00B894

# Jam UTC saat laporan harian dikirim (07:00 UTC = 14:00 WIB).
REPORT_HOUR_UTC = 0
REPORT_MINUTE_UTC = 1
# Kunci bot_state agar laporan tidak terkirim ganda dalam satu hari.
LAST_REPORT_KEY = "daily_report_last_date"

LAYANAN_LABEL = {
    "robux": "Robux",
    "vilog": "Vilog (Via Login)",
    "gp_topup": "Robux Gamepass",
    "jualbeli": "Jual Beli",
    "midman": "Middleman",
    "ml": "Mobile Legends",
    "ff": "Free Fire",
    "lainnya": "Layanan Lainnya",
    "cloudphone": "Cloud Phone",
    "nitro": "Discord Nitro",
}


def _pretty(layanan: str | None) -> str:
    if not layanan:
        return "Lainnya"
    base = layanan.split(":", 1)[0]
    label = LAYANAN_LABEL.get(base, base.replace("_", " ").title())
    if ":" in layanan:
        sub = layanan.split(":", 1)[1]
        if sub:
            label += f" · {sub.title()}"
    return label


def _get_state(key: str):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT value FROM bot_state WHERE key=?", (key,))
    row = c.fetchone()
    conn.close()
    return row["value"] if row else None


def _set_state(key: str, value: str):
    conn = get_conn()
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO bot_state (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()


def build_report_embed(report: dict) -> discord.Embed:
    """Bangun embed laporan harian dari data get_daily_report."""
    embed = discord.Embed(
        title=f"📊 Laporan Harian — {report['date']}",
        description=(
            f"**Total Transaksi:** {report['total_tx']}\n"
            f"**Total Omzet:** Rp {report['total_omzet']:,}".replace(",", ".")
        ),
        color=COLOR_REPORT,
        timestamp=discord.utils.utcnow(),
    )

    if report["per_layanan"]:
        lines = []
        for p in report["per_layanan"]:
            omzet = f"Rp {p['omzet']:,}".replace(",", ".")
            lines.append(f"• **{_pretty(p['layanan'])}** — {p['count']}x · {omzet}")
        embed.add_field(name="Per Layanan", value="\n".join(lines)[:1024], inline=False)
    else:
        embed.add_field(name="Per Layanan", value="_Tidak ada transaksi._", inline=False)

    if report["rating_count"]:
        full = int(round(report["rating_avg"]))
        stars = "⭐" * max(0, min(5, full))
        embed.add_field(
            name="Rating Hari Ini",
            value=f"{stars} {report['rating_avg']:.2f}/5 · {report['rating_count']} ulasan",
            inline=False,
        )

    embed.set_footer(text=STORE_NAME)
    return embed


class DailyReport(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self):
        self.daily_loop.start()

    def cog_unload(self):
        self.daily_loop.cancel()

    @tasks.loop(minutes=15)
    async def daily_loop(self):
        """Cek tiap 15 menit; posting laporan hari KEMARIN sekali per hari."""
        try:
            now = datetime.datetime.now(datetime.timezone.utc)
            # Hanya proses setelah jam target tercapai.
            if (now.hour, now.minute) < (REPORT_HOUR_UTC, REPORT_MINUTE_UTC):
                return
            today_str = now.strftime("%Y-%m-%d")
            if _get_state(LAST_REPORT_KEY) == today_str:
                return  # sudah kirim hari ini
            yesterday = (now - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
            await self._post_report(yesterday)
            _set_state(LAST_REPORT_KEY, today_str)
        except Exception as e:
            print(f"[DailyReport] loop error: {e}")

    @daily_loop.before_loop
    async def _before(self):
        await self.bot.wait_until_ready()

    async def _post_report(self, date_str: str):
        if not DAILY_REPORT_CHANNEL_ID:
            return
        channel = self.bot.get_channel(DAILY_REPORT_CHANNEL_ID)
        if channel is None:
            return
        report = rv.get_daily_report(date_str)
        try:
            await channel.send(embed=build_report_embed(report))
        except Exception as e:
            print(f"[DailyReport] post error: {e}")

    @commands.command(name="laporan")
    async def laporan_cmd(self, ctx: commands.Context, tanggal: str = None):
        """Admin: kirim laporan manual. Default tanggal = kemarin."""
        if not any(r.id == ADMIN_ROLE_ID for r in ctx.author.roles):
            return
        if tanggal is None:
            tanggal = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
        report = rv.get_daily_report(tanggal)
        await ctx.send(embed=build_report_embed(report))


async def setup(bot: commands.Bot):
    await bot.add_cog(DailyReport(bot))
    print("Cog DailyReport siap.")
