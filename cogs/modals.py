import discord
import datetime
from utils.fee import format_nominal
from utils.tickets import save_tickets
from utils.counter import next_ticket_number
from utils.config import TICKET_CATEGORY_ID, ADMIN_ROLE_ID, STORE_NAME
from cogs.views import AdminSetupView, TradeFinishView, build_embed_setup
from utils import ticket_ui

class MidmanTradeModal(discord.ui.Modal, title="Buka Tiket Midman Trade"):
    item_p1 = discord.ui.TextInput(label="Item kamu (Pihak 1)", placeholder="contoh: ruby gemstone")
    item_p2 = discord.ui.TextInput(label="Item yang kamu minta (Pihak 2)", placeholder="contoh: maja")

    async def on_submit(self, interaction):
        cog = interaction.client.cogs.get("Midman")
        guild = interaction.guild

        from utils.config import MAX_TICKETS_PER_SERVICE
        _user_active = sum(
            1 for _cid, _t in cog.active_tickets.items()
            if _t.get("pihak1") and _t["pihak1"].id == interaction.user.id and guild.get_channel(_cid)
        )
        if _user_active >= MAX_TICKETS_PER_SERVICE:
            await interaction.response.send_message(
                f"Kamu sudah punya {_user_active} tiket aktif di layanan ini (maks {MAX_TICKETS_PER_SERVICE}). Selesaikan salah satunya sebelum membuka yang baru.",
                ephemeral=True
            )
            return

        category = guild.get_channel(TICKET_CATEGORY_ID)
        admin_role = guild.get_role(ADMIN_ROLE_ID)

        if category is None:
            await interaction.response.send_message("Konfigurasi kategori tiket tidak ditemukan. Hubungi admin.", ephemeral=True)
            return
        if admin_role is None:
            await interaction.response.send_message("Konfigurasi role admin tidak ditemukan. Hubungi admin.", ephemeral=True)
            return

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            admin_role: discord.PermissionOverwrite(view_channel=True, send_messages=True),
        }
        ticket_num = next_ticket_number()
        channel = await guild.create_text_channel(
            name=ticket_ui.channel_name("midman", ticket_num, interaction.user.name),
            category=category,
            overwrites=overwrites
        )
        cog.active_tickets[channel.id] = {
            "pihak1": interaction.user,
            "pihak2": None,
            "item_p1": self.item_p1.value,
            "item_p2": self.item_p2.value,
            "fee_final": None,
            "fee_paid": False,
            "link_server": None,
            "admin": None,
            "embed_message_id": None,
            "ticket_number": ticket_num,
            "opened_at": datetime.datetime.now(datetime.timezone.utc),
        }
        await interaction.response.send_message(f"Tiket dibuat: {channel.mention}", ephemeral=True)
        embed = ticket_ui.open_ticket_embed(
            "midman", ticket_num, interaction.user,
            item=f"{self.item_p1.value} ↔ {self.item_p2.value}",
            payment="QRIS",
            extra_fields=[
                ("Pihak 1", f"{interaction.user.mention} (item: {self.item_p1.value})", False),
                ("Pihak 2", f"- (item: {self.item_p2.value})", False),
                ("Admin", "-", True),
                ("Status", "Menunggu konfirmasi admin", True),
                ("Estimasi Proses", "Admin akan segera mengatur detail trade. Harap tunggu.", False),
                ("Peringatan", "Tiket yang tidak aktif selama 2 jam akan otomatis ditutup dan transaksi dianggap batal.", False),
            ])
        msg = await channel.send(
            content=f"{admin_role.mention} — Tiket midman trade baru dari {interaction.user.mention}.",
            embed=embed,
            view=AdminSetupView()
        )
        cog.active_tickets[channel.id]["embed_message_id"] = msg.id
        save_tickets(cog.active_tickets)

        from utils.customer_insight import send_insight
        await send_insight(interaction.client, channel, interaction.user)

class AdminSetupModal(discord.ui.Modal, title="Setup Data Trade"):
    pihak2_id = discord.ui.TextInput(label="ID Pihak 2", placeholder="Paste user ID pihak 2")

    async def on_submit(self, interaction):
        cog = interaction.client.cogs.get("Midman")
        ticket = cog.active_tickets.get(interaction.channel.id)
        guild = interaction.guild
        try:
            user2 = await guild.fetch_member(int(self.pihak2_id.value.strip()))
        except Exception:
            await interaction.response.send_message("User tidak ditemukan. Pastikan ID benar. Tekan Setup Trade lagi.", ephemeral=True)
            return
        fee_int = 2500
        fee_str = format_nominal(fee_int)
        ticket["pihak2"] = user2
        ticket["fee_final"] = fee_int
        ticket["link_server"] = "-"
        save_tickets(cog.active_tickets)
        await interaction.channel.set_permissions(user2, view_channel=True, send_messages=True)
        try:
            orig_msg = await interaction.channel.fetch_message(ticket["embed_message_id"])
            await orig_msg.delete()
        except Exception as e:
            print(f"Gagal hapus embed: {e}")
        embed = build_embed_setup(STORE_NAME, ticket, user2, fee_str)
        await interaction.response.send_message(
            content=f"{user2.mention} — kamu ditambahkan ke tiket ini sebagai Pihak 2.",
            embed=embed,
            view=TradeFinishView()
        )
        fee_warning = discord.Embed(
            title="⚠️ PERHATIAN",
            description=(
                f"Harap segera bayar fee sebesar **{fee_str}** ke {ticket['admin'].mention}\n"
                f"sebelum trade dapat dimulai.\n\n"
                f"Admin tidak akan memproses trade sebelum fee diterima."
            ),
            color=0xFF0000
        )
        warning_msg = await interaction.channel.send(embed=fee_warning)
        ticket["fee_warning_id"] = warning_msg.id
        save_tickets(cog.active_tickets)
