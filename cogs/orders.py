import asyncio
import datetime
import discord
from discord.ext import commands
from utils.config import ADMIN_ROLE_ID, LOG_CHANNEL_ID, STORE_NAME, TRANSCRIPT_CHANNEL_ID
from utils.transcript import generate as generate_transcript
from utils import ticket_ui

THUMBNAIL = "https://i.imgur.com/CWtUCzj.png"


def _layanan_label(kategori: str) -> str:
    """Tentukan label `layanan` untuk transaction_log dari kategori tiket.

    Tiket cog `lainnya` bisa berisi:
      - 1 kategori produk (mis. "REMINI")        -> "lainnya:editing"
      - "Custom Order"                            -> "lainnya:custom"
      - beberapa kategori dari cart ("A, B")      -> grup gabungan, atau
                                                     "lainnya:mixed" bila beda grup
    Label di-prefix "lainnya:" + nama grup (lowercase) supaya laporan omzet
    per-layanan di admin panel akurat dan tidak tertukar layanan lain.
    """
    from cogs.lainnya_catalog import group_of

    kategori = (kategori or "").strip()
    if not kategori:
        return "lainnya"
    if kategori.lower() == "custom order":
        return "lainnya:custom"

    # Pisah multi-kategori hasil cart ("REMINI, CAPCUT").
    cats = [c.strip() for c in kategori.split(",") if c.strip()]
    groups = {group_of(c) for c in cats}
    if len(groups) == 1:
        grup = next(iter(groups))
        return f"lainnya:{grup.lower()}"
    return "lainnya:mixed"


class OrdersAdmin(commands.Cog):
    """Shared !done dan !cancel untuk tiket order (lainnya / Cloud Phone & Nitro)"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def _get_ticket(self, channel_id):
        """Cari tiket order, return (cog_name, cog, ticket) atau (None, None, None)"""
        cog = self.bot.cogs.get("LainnyaStore")
        if cog and channel_id in cog.active_tickets:
            return "LainnyaStore", cog, cog.active_tickets[channel_id]
        return None, None, None

    @commands.command(name="done")
    async def done(self, ctx):
        if not any(r.id == ADMIN_ROLE_ID for r in ctx.author.roles):
            return
        ch_id = ctx.channel.id
        cog_name, cog, ticket = self._get_ticket(ch_id)
        if not ticket:
            return

        member = ctx.guild.get_member(ticket["user_id"])
        closed_at = datetime.datetime.now(datetime.timezone.utc)
        opened_at_dt = datetime.datetime.fromisoformat(ticket["opened_at"])
        if opened_at_dt.tzinfo is None:
            opened_at_dt = opened_at_dt.replace(tzinfo=datetime.timezone.utc)
        durasi_secs = int((closed_at - opened_at_dt).total_seconds())

        await ctx.send(
            f"{member.mention if member else ''}\n"
            f"Pesanan berhasil diproses. Terima kasih telah berbelanja di {STORE_NAME}! "
            f"Tiket ditutup dalam 5 detik."
        )
        await asyncio.sleep(5)

        # Transcript
        try:
            transcript_ch = ctx.guild.get_channel(TRANSCRIPT_CHANNEL_ID)
            if transcript_ch:
                transcript_file = await generate_transcript(ctx.channel, STORE_NAME)
                await transcript_ch.send(
                    content=f"Transcript Order — {ctx.channel.name}",
                    file=transcript_file
                )
        except Exception as e:
            print(f"[Orders] Transcript error: {e}")

        # Data transaksi (single item, custom order, atau multi-kategori dari cart)
        kategori = ticket.get("category", "")
        layanan = _layanan_label(kategori)
        nominal = ticket.get("harga", 0)
        item_str = ticket.get("item_name", "-")

        # Log embed
        # Log transaksi (flat text + status garansi auto-update setelah rating)
        from utils.db import log_transaction, set_transaction_log_message
        from utils.config import TESTIMONI_CHANNEL_ID
        tx_id = None
        try:
            tx_id = log_transaction(
                layanan=layanan,
                nominal=nominal,
                item=item_str,
                admin_id=ctx.author.id,
                user_id=ticket.get("user_id"),
                closed_at=closed_at,
                durasi_detik=durasi_secs,
                qty=1,
            )
        except Exception as e:
            print(f"[Orders] Log error: {e}")

        log_ch = ctx.guild.get_channel(LOG_CHANNEL_ID)
        if log_ch:
            text = ticket_ui.success_log_text(
                seller=ctx.author.mention,
                buyer=member.mention if member else f"<@{ticket['user_id']}>",
                product=item_str,
                qty=1,
                harga=nominal,
                rating=None,
                rating_channel_id=TESTIMONI_CHANNEL_ID,
            )
            try:
                msg = await log_ch.send(text)
                if tx_id:
                    set_transaction_log_message(tx_id, log_ch.id, msg.id)
            except Exception as e:
                print(f"[Orders] Log send error: {e}")

        # Royal Customer
        try:
            royal_role = discord.utils.get(ctx.guild.roles, name="Royal Customer")
            if royal_role and member and royal_role not in member.roles:
                await member.add_roles(royal_role)
        except Exception as e:
            print(f"[Orders] Role error: {e}")

        # Cleanup
        from cogs.lainnya import delete_lainnya_ticket
        delete_lainnya_ticket(ch_id)
        del cog.active_tickets[ch_id]
        await ctx.channel.delete()

    @commands.command(name="cancel")
    async def cancel(self, ctx, *, alasan: str = "Tidak ada alasan diberikan."):
        if not any(r.id == ADMIN_ROLE_ID for r in ctx.author.roles):
            return
        ch_id = ctx.channel.id
        cog_name, cog, ticket = self._get_ticket(ch_id)
        if not ticket:
            return

        await ctx.send(f"❌ Pesanan dibatalkan.\nAlasan: {alasan}\nTiket ditutup dalam 5 detik.")
        await asyncio.sleep(5)

        from cogs.lainnya import delete_lainnya_ticket
        delete_lainnya_ticket(ch_id)
        del cog.active_tickets[ch_id]
        await ctx.channel.delete()


async def setup(bot: commands.Bot):
    await bot.add_cog(OrdersAdmin(bot))
