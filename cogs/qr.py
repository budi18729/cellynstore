import discord
from discord.ext import commands
from utils.db import get_conn
from utils.config import ADMIN_ROLE_ID

def _migrate():
    conn = get_conn()
    conn.execute("""CREATE TABLE IF NOT EXISTS qr_slots (
        slot    INTEGER PRIMARY KEY,
        label   TEXT NOT NULL DEFAULT '',
        detail  TEXT NOT NULL DEFAULT '',
        url     TEXT NOT NULL DEFAULT '',
        active  INTEGER NOT NULL DEFAULT 1
    )""")
    # Pastikan kolom "detail" ada untuk DB lama
    cols = [r[1] for r in conn.execute("PRAGMA table_info(qr_slots)").fetchall()]
    if "detail" not in cols:
        conn.execute("ALTER TABLE qr_slots ADD COLUMN detail TEXT NOT NULL DEFAULT ''")
    # Seed 10 slot kosong kalau belum ada
    for i in range(1, 11):
        conn.execute(
            "INSERT OR IGNORE INTO qr_slots (slot, label, detail, url) VALUES (?,?,?,?)",
            (i, f"QRIS {i}", "", "")
        )
    conn.commit()
    conn.close()

def _get_slot(slot: int):
    conn = get_conn()
    row = conn.execute(
        "SELECT slot, label, detail, url, active FROM qr_slots WHERE slot=?", (slot,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


class QRCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        _migrate()
        print("Cog QR siap.")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        content = message.content.strip().lower()
        if not content.startswith("!qr"):
            return
        # Ambil nomor slot — !qr1 s/d !qr99
        suffix = content[3:]
        if not suffix.isdigit():
            return
        slot = int(suffix)
        await message.delete()

        data = _get_slot(slot)
        if not data or not data["active"] or not data["url"]:
            await message.channel.send(
                f"Slot QRIS **{slot}** belum diset atau tidak aktif.",
                delete_after=5
            )
            return

        embed = discord.Embed(
            title=f"💳 {data['label']}",
            color=0x2ECC71
        )
        if data.get("detail"):
            embed.description = data["detail"]
        embed.set_image(url=data["url"])
        embed.set_footer(text="Scan QR Code di atas untuk melakukan pembayaran")
        await message.channel.send(embed=embed)


async def setup(bot):
    await bot.add_cog(QRCog(bot))
