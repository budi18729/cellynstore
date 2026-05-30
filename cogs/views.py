import discord
import datetime
from utils.fee import format_nominal
from utils.tickets import save_tickets
from utils.store_hours import is_store_open

def build_embed_awal(store_name, p1_mention, item_p1, item_p2):
    embed = discord.Embed(
        title=f"MIDMAN TRADE — {store_name}",
        color=0xFFD700,
        timestamp=datetime.datetime.now(datetime.timezone.utc)
    )
    embed.add_field(
        name="​",
        value=(
            f"Pihak 1 : {p1_mention}  (item : {item_p1})\n"
            f"Pihak 2 : -      (item : {item_p2})\n"
            f"Admin   : -\n\n"
            f"Status  : Menunggu konfirmasi admin\n"
            f"──────────────────────────────\n"
            f"Tiket yang tidak aktif selama 2 jam akan otomatis ditutup dan transaksi dianggap batal."
        ),
        inline=False
    )
    embed.set_footer(text=store_name)
    return embed

def build_embed_setup(store_name, ticket, user2, fee_str):
    sep = "─" * 30
    embed = discord.Embed(
        title=f"MIDMAN TRADE — {store_name}",
        color=0xFFA500,
        timestamp=datetime.datetime.now(datetime.timezone.utc)
    )
    embed.add_field(
        name="​",
        value=(
            f"Pihak 1 : {ticket['pihak1'].mention}  (item : {ticket['item_p1']})\n"
            f"Pihak 2 : {user2.mention}  (item : {ticket['item_p2']})\n"
            f"Admin   : {ticket['admin'].mention}\n"
            f"Fee     : {fee_str}\n\n"
            f"Status  : Menunggu pembayaran fee\n"
            f"{sep}\n"
            f"Bayar fee terlebih dahulu untuk memulai sesi trade.\n"
            f"Konfirmasi dari admin akan muncul setelah fee diterima."
        ),
        inline=False
    )
    embed.set_footer(text=store_name)
    return embed

def build_embed_berlangsung(store_name, ticket, confirmed_by):
    sep = "─" * 30
    p1 = ticket["pihak1"]
    p2 = ticket["pihak2"]
    fee_str = format_nominal(ticket["fee_final"]) if ticket.get("fee_final") else "-"
    embed = discord.Embed(
        title=f"MIDMAN TRADE — {store_name}",
        color=0x57F287,
        timestamp=datetime.datetime.now(datetime.timezone.utc)
    )
    embed.add_field(
        name="​",
        value=(
            f"Pihak 1 : {p1.mention}  (item : {ticket['item_p1']})\n"
            f"Pihak 2 : {p2.mention if p2 else '-'}  (item : {ticket['item_p2']})\n"
            f"Admin   : {ticket['admin'].mention}\n"
            f"Fee     : {fee_str}\n"
            f"Link    : {ticket['link_server']}\n\n"
            f"Status  : Transaksi berlangsung\n"
            f"Notif   : Pembayaran dikonfirmasi oleh {confirmed_by}\n"
            f"{sep}\n"
            f"Ikuti instruksi admin untuk proses trade.\n"
            f"Jangan tukar item sebelum admin memberi tanda aman!"
        ),
        inline=False
    )
    embed.set_footer(text=store_name)
    return embed

class MidmanMainView(discord.ui.View):
    def __init__(self, store_open: bool | None = None):
        super().__init__(timeout=None)
        store_open = is_store_open() if store_open is None else store_open
        if not store_open:
            for child in self.children:
                child.disabled = True

    @discord.ui.button(label="⚔️ Midman Trade", style=discord.ButtonStyle.primary, custom_id="open_midman_trade")
    async def open_ticket(self, interaction, button):
        from utils.service_info import get_service_info, build_info_embed
        info = get_service_info("midman_trade")
        has_info = any([info["description"], info["terms"], info["payment_info"]])
        if has_info:
            embed = build_info_embed("Midman Trade", info, 0xFFD700)
            await interaction.response.send_message(embed=embed, view=MidmanTradeInfoView(), ephemeral=True)
        else:
            from cogs.modals import MidmanTradeModal
            await interaction.response.send_modal(MidmanTradeModal())

    @discord.ui.button(label="🛒 Midman Jual Beli", style=discord.ButtonStyle.secondary, custom_id="open_midman_jualbeli")
    async def open_jualbeli(self, interaction, button):
        from utils.service_info import get_service_info, build_info_embed
        info = get_service_info("midman_jb")
        has_info = any([info["description"], info["terms"], info["payment_info"]])
        if has_info:
            embed = build_info_embed("Midman Jual Beli", info, 0x2ECC71)
            await interaction.response.send_message(embed=embed, view=MidmanJBInfoView(), ephemeral=True)
        else:
            from cogs.jualbeli import JBTradeModal
            await interaction.response.send_modal(JBTradeModal())


class MidmanTradeInfoView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=120)

    @discord.ui.button(label="✅ Lanjutkan", style=discord.ButtonStyle.success, custom_id="midman_trade_info_lanjut")
    async def lanjutkan(self, interaction, button):
        from cogs.modals import MidmanTradeModal
        await interaction.response.send_modal(MidmanTradeModal())

    @discord.ui.button(label="❌ Batal", style=discord.ButtonStyle.danger, custom_id="midman_trade_info_batal")
    async def batal(self, interaction, button):
        await interaction.response.edit_message(content="Dibatalkan.", embed=None, view=None)


class MidmanJBInfoView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=120)

    @discord.ui.button(label="✅ Lanjutkan", style=discord.ButtonStyle.success, custom_id="midman_jb_info_lanjut")
    async def lanjutkan(self, interaction, button):
        from cogs.jualbeli import JBTradeModal
        await interaction.response.send_modal(JBTradeModal())

    @discord.ui.button(label="❌ Batal", style=discord.ButtonStyle.danger, custom_id="midman_jb_info_batal")
    async def batal(self, interaction, button):
        await interaction.response.edit_message(content="Dibatalkan.", embed=None, view=None)

class AdminSetupView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Setup Trade (Admin)", style=discord.ButtonStyle.primary, custom_id="admin_setup_trade")
    async def setup_trade(self, interaction, button):
        from cogs.modals import AdminSetupModal
        from utils.config import ADMIN_ROLE_ID
        if interaction.guild.get_role(ADMIN_ROLE_ID) not in interaction.user.roles:
            await interaction.response.send_message("Hanya admin.", ephemeral=True)
            return
        cog = interaction.client.cogs.get("Midman")
        ticket = cog.active_tickets.get(interaction.channel.id)
        if not ticket:
            await interaction.response.send_message("Data tiket tidak ditemukan.", ephemeral=True)
            return
        ticket["admin"] = interaction.user
        await interaction.response.send_modal(AdminSetupModal())

class TradeFinishView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Fee Diterima (Admin)", style=discord.ButtonStyle.primary, custom_id="fee_diterima_v2")
    async def fee_diterima(self, interaction, button):
        from utils.config import ADMIN_ROLE_ID, STORE_NAME
        if interaction.guild.get_role(ADMIN_ROLE_ID) not in interaction.user.roles:
            await interaction.response.send_message("Hanya admin.", ephemeral=True)
            return
        cog = interaction.client.cogs.get("Midman")
        ticket = cog.active_tickets.get(interaction.channel.id)
        if not ticket:
            await interaction.response.send_message("Data tiket tidak ditemukan.", ephemeral=True)
            return
        ticket["fee_paid"] = True
        ticket["verified_by"] = interaction.user
        save_tickets(cog.active_tickets)
        button.disabled = True

        # Hapus embed peringatan fee
        warning_id = ticket.get("fee_warning_id")
        if warning_id:
            try:
                warning_msg = await interaction.channel.fetch_message(warning_id)
                await warning_msg.delete()
            except Exception as e:
                print(f"[WARNING] cogs/views.py: {e}")
                pass
        embed = build_embed_berlangsung(STORE_NAME, ticket, interaction.user.mention)
        await interaction.message.edit(embed=embed, view=self)
        await interaction.response.send_message(
            content=f"Pembayaran dikonfirmasi oleh {interaction.user.mention}."
        )
