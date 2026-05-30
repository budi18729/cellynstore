import asyncio
import datetime
import discord
from discord.ext import commands
from utils.config import ADMIN_ROLE_ID, LOG_CHANNEL_ID, STORE_NAME, TRANSCRIPT_CHANNEL_ID
from utils.db import get_conn
from utils.counter import next_ticket_number
from utils.transcript import generate as generate_transcript

THUMBNAIL = "https://i.imgur.com/CWtUCzj.png"


class OrdersAdmin(commands.Cog):
    """Shared !done dan !cancel untuk semua tiket order (lainnya + scaset)"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def _get_ticket(self, channel_id):
        """Cari tiket di semua cog order, return (cog_name, ticket) atau (None, None)"""
        for cog_name in ["LainnyaStore", "ScasetStore"]:
            cog = self.bot.cogs.get(cog_name)
            if cog and channel_id in cog.active_tickets:
                return cog_name, cog, cog.active_tickets[channel_id]
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
        nomor = next_ticket_number()
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

        # Log embed
        log_ch = ctx.guild.get_channel(LOG_CHANNEL_ID)
        if log_ch:
            if cog_name == "ScasetStore":
                # Format scaset: per item
                items = ticket.get("items", [])
                subtotal = sum(i.get("harga", 0) for i in items)
                log_embed = discord.Embed(
                    title=f"SC/ASET GAME SUKSES — #{nomor:04d}",
                    color=0xF0A500,
                    timestamp=closed_at
                )
                log_embed.add_field(name="Admin", value=f"{ctx.author.mention}\n`{ctx.author.id}`", inline=False)
                log_embed.add_field(name="Member", value=f"{member.mention if member else ticket['user_id']}\n`{ticket['user_id']}`", inline=False)
                for i, item in enumerate(items, 1):
                    log_embed.add_field(
                        name=f"Item {i}",
                        value=f"{item['nama']} | Qty: {item['qty']} | Rp {item['harga']:,}",
                        inline=False
                    )
                log_embed.add_field(name="Harga", value=f"Rp {subtotal:,}", inline=True)
                log_embed.add_field(name="Metode", value=ticket.get("payment_method", "-"), inline=True)
                log_embed.set_footer(text=STORE_NAME)
                await log_ch.send(embed=log_embed)
                nominal = subtotal
                layanan = "scaset"
                item_str = ", ".join(i["nama"] for i in items) or "-"
            else:
                # Format lainnya: single item
                kategori = ticket.get("category", "")
                layanan = "nitro" if "NITRO" in kategori.upper() else "cloudphone"
                nominal = ticket.get("harga", 0)
                item_str = ticket.get("item_name", "-")
                log_embed = discord.Embed(
                    title=f"ORDER SUKSES — #{nomor:04d}",
                    color=0x5865F2,
                    timestamp=closed_at
                )
                log_embed.add_field(name="Admin", value=f"{ctx.author.mention}\n`{ctx.author.id}`", inline=False)
                log_embed.add_field(name="Member", value=f"{member.mention if member else ticket['user_id']}\n`{ticket['user_id']}`", inline=False)
                log_embed.add_field(name="Kategori", value=kategori, inline=True)
                log_embed.add_field(name="Item", value=item_str, inline=True)
                log_embed.add_field(name="Harga", value=f"Rp {nominal:,}", inline=True)
                log_embed.add_field(name="Metode", value=ticket.get("payment_method", "-"), inline=True)
                log_embed.set_footer(text=STORE_NAME)
                await log_ch.send(embed=log_embed)

        # Transaction log
        try:
            from utils.db import log_transaction
            log_transaction(
                layanan=layanan,
                nominal=nominal,
                item=item_str,
                admin_id=ctx.author.id,
                user_id=ticket.get("user_id"),
                closed_at=closed_at,
                durasi_detik=durasi_secs
            )
        except Exception as e:
            print(f"[Orders] Log error: {e}")

        # Royal Customer
        try:
            royal_role = discord.utils.get(ctx.guild.roles, name="Royal Customer")
            if royal_role and member and royal_role not in member.roles:
                await member.add_roles(royal_role)
        except Exception as e:
            print(f"[Orders] Role error: {e}")

        # Cleanup
        if cog_name == "ScasetStore":
            from cogs.scaset import delete_scaset_ticket
            delete_scaset_ticket(ch_id)
        else:
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

        if cog_name == "ScasetStore":
            from cogs.scaset import delete_scaset_ticket
            delete_scaset_ticket(ch_id)
        else:
            from cogs.lainnya import delete_lainnya_ticket
            delete_lainnya_ticket(ch_id)
        del cog.active_tickets[ch_id]
        await ctx.channel.delete()


async def setup(bot: commands.Bot):
    await bot.add_cog(OrdersAdmin(bot))
