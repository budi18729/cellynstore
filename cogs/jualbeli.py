import time
import discord
import datetime
import asyncio
from discord.ext import commands, tasks
from utils.config import (
    ADMIN_ROLE_ID, STORE_NAME, TICKET_CATEGORY_ID,
    LOG_CHANNEL_ID, TRANSCRIPT_CHANNEL_ID
)
from utils.db import get_conn
from utils.fee import hitung_fee, format_nominal
import utils.transcript as transcript_gen

THUMBNAIL = "https://i.imgur.com/CWtUCzj.png"
COLOR_WAIT   = 0xFFD700   # kuning — menunggu admin
COLOR_SETUP  = 0xFFA500   # oranye — setup oleh admin
COLOR_BAYAR  = 0x3498DB   # biru — menunggu bayar
COLOR_PROSES = 0xE67E22   # oranye tua — item sedang diserahkan
COLOR_DONE   = 0x2ECC71   # hijau — selesai
COLOR_BATAL  = 0xE74C3C   # merah — batal

# ─── DB HELPERS ────────────────────────────────────────────────────────────────

def save_jb_ticket(ticket: dict):
    conn = get_conn()
    c = conn.cursor()
    c.execute('''
        INSERT OR REPLACE INTO jb_tickets (
            channel_id, p1_id, p2_id, deskripsi, harga,
            fee_final, fee_penanggung, admin_id,
            opened_at, warned, status
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?)
    ''', (
        ticket["channel_id"],
        ticket.get("p1_id"),
        ticket.get("p2_id"),
        ticket.get("deskripsi"),
        ticket.get("harga"),
        ticket.get("fee_final"),
        ticket.get("fee_penanggung"),
        ticket.get("admin_id"),
        ticket.get("opened_at"),
        int(ticket.get("warned", 0)),
        ticket.get("status", "menunggu_admin"),
    ))
    conn.commit()
    conn.close()

def delete_jb_ticket(channel_id: int):
    conn = get_conn()
    c = conn.cursor()
    c.execute("DELETE FROM jb_tickets WHERE channel_id = ?", (channel_id,))
    conn.commit()
    conn.close()

def load_jb_tickets() -> dict:
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM jb_tickets")
    rows = c.fetchall()
    conn.close()
    tickets = {}
    for row in rows:
        tickets[row["channel_id"]] = dict(row)
    return tickets

# ─── EMBED BUILDERS ────────────────────────────────────────────────────────────

def _sep(): return "─" * 32

def embed_menunggu_admin(store_name, p1_mention, deskripsi, harga):
    e = discord.Embed(title=f"MIDMAN JUAL BELI — {store_name}", color=COLOR_WAIT,
                      timestamp=datetime.datetime.now(datetime.timezone.utc))
    e.add_field(name="\u200b", value=(
        f"Penjual  : {p1_mention}\n"
        f"Pembeli  : -\n"
        f"Admin    : -\n\n"
        f"Item     : {deskripsi}\n"
        f"Harga    : {format_nominal(harga)}\n\n"
        f"Status   : Menunggu admin bergabung\n"
        f"{_sep()}\n"
        f"Tiket tidak aktif 2 jam akan otomatis ditutup."
    ), inline=False)
    e.set_footer(text=store_name)
    return e

def embed_setup(store_name, ticket, p1, p2, admin):
    fee = ticket.get("fee_final")
    fee_str = format_nominal(fee) if fee else "-"
    penanggung = ticket.get("fee_penanggung", "-")
    total_p2 = format_nominal(ticket["harga"] + fee) if fee and penanggung == "pembeli" else format_nominal(ticket["harga"])
    e = discord.Embed(title=f"MIDMAN JUAL BELI — {store_name}", color=COLOR_SETUP,
                      timestamp=datetime.datetime.now(datetime.timezone.utc))
    e.add_field(name="\u200b", value=(
        f"Penjual  : {p1.mention}\n"
        f"Pembeli  : {p2.mention if p2 else '-'}\n"
        f"Admin    : {admin.mention}\n\n"
        f"Item     : {ticket['deskripsi']}\n"
        f"Harga    : {format_nominal(ticket['harga'])}\n"
        f"Fee      : {fee_str} (ditanggung {penanggung})\n"
        f"Total bayar (pembeli) : {total_p2}\n\n"
        f"Status   : Menunggu pembayaran dari pembeli\n"
        f"{_sep()}\n"
        f"Pembeli transfer ke admin sesuai nominal di atas.\n"
        f"Kirim bukti bayar di tiket ini."
    ), inline=False)
    e.set_footer(text=store_name)
    return e

def embed_uang_diterima(store_name, ticket, p1, p2, admin):
    fee = ticket.get("fee_final")
    fee_str = format_nominal(fee) if fee else "-"
    penanggung = ticket.get("fee_penanggung", "-")
    release = format_nominal(ticket["harga"] - fee) if fee and penanggung == "penjual" else format_nominal(ticket["harga"])
    e = discord.Embed(title=f"MIDMAN JUAL BELI — {store_name}", color=COLOR_PROSES,
                      timestamp=datetime.datetime.now(datetime.timezone.utc))
    e.add_field(name="\u200b", value=(
        f"Penjual  : {p1.mention}\n"
        f"Pembeli  : {p2.mention if p2 else '-'}\n"
        f"Admin    : {admin.mention}\n\n"
        f"Item     : {ticket['deskripsi']}\n"
        f"Harga    : {format_nominal(ticket['harga'])}\n"
        f"Fee      : {fee_str} (ditanggung {penanggung})\n"
        f"Dana release ke penjual : {release}\n\n"
        f"Status   : Uang diterima — item sedang diserahkan\n"
        f"{_sep()}\n"
        f"Admin sedang menyerahkan item/akun ke pembeli.\n"
        f"Pembeli konfirmasi item setelah diterima."
    ), inline=False)
    e.set_footer(text=store_name)
    return e

def embed_item_diterima(store_name, ticket, p1, p2, admin):
    fee = ticket.get("fee_final")
    fee_str = format_nominal(fee) if fee else "-"
    penanggung = ticket.get("fee_penanggung", "-")
    release = format_nominal(ticket["harga"] - fee) if fee and penanggung == "penjual" else format_nominal(ticket["harga"])
    e = discord.Embed(title=f"MIDMAN JUAL BELI — {store_name}", color=COLOR_BAYAR,
                      timestamp=datetime.datetime.now(datetime.timezone.utc))
    e.add_field(name="\u200b", value=(
        f"Penjual  : {p1.mention}\n"
        f"Pembeli  : {p2.mention if p2 else '-'}\n"
        f"Admin    : {admin.mention}\n\n"
        f"Item     : {ticket['deskripsi']}\n"
        f"Harga    : {format_nominal(ticket['harga'])}\n"
        f"Fee      : {fee_str} (ditanggung {penanggung})\n"
        f"Dana release ke penjual : {release}\n\n"
        f"Status   : Item diterima pembeli — menunggu admin release dana\n"
        f"{_sep()}\n"
        f"Admin akan release dana ke penjual setelah konfirmasi."
    ), inline=False)
    e.set_footer(text=store_name)
    return e

def embed_selesai(store_name, ticket, p1, p2, admin):
    fee = ticket.get("fee_final")
    fee_str = format_nominal(fee) if fee else "-"
    penanggung = ticket.get("fee_penanggung", "-")
    release = format_nominal(ticket["harga"] - fee) if fee and penanggung == "penjual" else format_nominal(ticket["harga"])
    e = discord.Embed(title=f"MIDMAN JUAL BELI — {store_name}", color=COLOR_DONE,
                      timestamp=datetime.datetime.now(datetime.timezone.utc))
    e.add_field(name="\u200b", value=(
        f"Penjual  : {p1.mention}\n"
        f"Pembeli  : {p2.mention if p2 else '-'}\n"
        f"Admin    : {admin.mention}\n\n"
        f"Item     : {ticket['deskripsi']}\n"
        f"Harga    : {format_nominal(ticket['harga'])}\n"
        f"Fee      : {fee_str} (ditanggung {penanggung})\n"
        f"Dana release ke penjual : {release}\n\n"
        f"Status   : ✅ Transaksi selesai\n"
        f"{_sep()}\n"
        f"Tiket akan ditutup dalam 5 detik."
    ), inline=False)
    e.set_footer(text=store_name)
    return e

# ─── VIEWS ─────────────────────────────────────────────────────────────────────

class JBItemDiterimaView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="✅ Item Diterima & Sesuai", style=discord.ButtonStyle.success,
                       custom_id="jb_item_diterima")
    async def item_diterima(self, interaction: discord.Interaction, button: discord.ui.Button):
        cog = interaction.client.cogs.get("JualBeli")
        ticket = cog.active_tickets.get(interaction.channel.id)
        if not ticket:
            await interaction.response.send_message("Data tiket tidak ditemukan.", ephemeral=True)
            return
        if interaction.user.id != ticket["p2_id"]:
            await interaction.response.send_message("Hanya pembeli yang bisa konfirmasi.", ephemeral=True)
            return
        if ticket.get("status") != "uang_diterima":
            await interaction.response.send_message("Status tiket tidak sesuai.", ephemeral=True)
            return

        ticket["status"] = "item_diterima"
        save_jb_ticket(ticket)
        button.disabled = True

        guild = interaction.guild
        p1 = guild.get_member(ticket["p1_id"])
        p2 = guild.get_member(ticket["p2_id"])
        admin = guild.get_member(ticket["admin_id"])

        e = embed_item_diterima(STORE_NAME, ticket, p1, p2, admin)
        try:
            msg = await interaction.channel.fetch_message(ticket.get("embed_message_id"))
            await msg.edit(embed=e, view=self)
        except Exception:
            await interaction.channel.send(embed=e)
        admin_role = guild.get_role(ADMIN_ROLE_ID)
        ping = admin_role.mention if admin_role else ""
        await interaction.response.send_message(
            f"{ping} Pembeli **{interaction.user.display_name}** mengkonfirmasi item sudah diterima dan sesuai.\n"
            f"Silakan release dana ke penjual dengan `!jbselesai`."
        )

# ─── MODALS ────────────────────────────────────────────────────────────────────

class JBTradeModal(discord.ui.Modal, title="Midman Jual Beli"):
    deskripsi = discord.ui.TextInput(
        label="Deskripsi Item / Akun yang Dijual",
        placeholder="Contoh: Akun Roblox level 50, item X...",
        required=True, min_length=5, max_length=200
    )
    harga = discord.ui.TextInput(
        label="Harga Jual (angka, contoh: 150000)",
        placeholder="150000",
        required=True, max_length=15
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            harga_int = int(self.harga.value.strip().replace(".", "").replace(",", ""))
        except ValueError:
            await interaction.response.send_message("Harga harus berupa angka.", ephemeral=True)
            return
        if harga_int < 1000:
            await interaction.response.send_message("Harga minimal Rp 1.000.", ephemeral=True)
            return

        guild = interaction.guild
        user = interaction.user
        cog = interaction.client.cogs.get("JualBeli")

        # Cek tiket aktif
        for ch_id, t in cog.active_tickets.items():
            if t["p1_id"] == user.id:
                existing = guild.get_channel(ch_id)
                if existing:
                    await interaction.response.send_message(
                        f"Kamu masih punya tiket aktif di {existing.mention}!", ephemeral=True
                    )
                    return

        category = guild.get_channel(TICKET_CATEGORY_ID)
        admin_role = guild.get_role(ADMIN_ROLE_ID)
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        }
        if admin_role:
            overwrites[admin_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        channel = await guild.create_text_channel(
            name=f"jb-{user.name}",
            category=category,
            overwrites=overwrites
        )

        ticket = {
            "channel_id": channel.id,
            "p1_id": user.id,
            "p2_id": None,
            "deskripsi": self.deskripsi.value.strip(),
            "harga": harga_int,
            "fee_final": None,
            "fee_penanggung": None,
            "admin_id": None,
            "opened_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "warned": 0,
            "status": "menunggu_admin",
            "last_activity": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
        cog.active_tickets[channel.id] = ticket
        save_jb_ticket(ticket)

        e = embed_menunggu_admin(STORE_NAME, user.mention, self.deskripsi.value.strip(), harga_int)
        view = JBAdminSetupView()
        if admin_role:
            msg = await channel.send(content=admin_role.mention, embed=e, view=view)
        else:
            msg = await channel.send(embed=e, view=view)

        ticket["embed_message_id"] = msg.id
        save_jb_ticket(ticket)

        await interaction.response.send_message(
            f"Tiket jual beli berhasil dibuat di {channel.mention}!", ephemeral=True
        )


class JBSetupModal(discord.ui.Modal, title="Setup Jual Beli"):
    p2_id_input = discord.ui.TextInput(
        label="User ID Pembeli",
        placeholder="Contoh: 123456789012345678",
        required=True, max_length=20
    )
    fee_input = discord.ui.TextInput(
        label="Nominal Fee (angka)",
        placeholder="Contoh: 5000",
        required=True, max_length=10
    )
    penanggung_input = discord.ui.TextInput(
        label="Fee Ditanggung (penjual / pembeli)",
        placeholder="penjual atau pembeli",
        required=True, max_length=10
    )

    async def on_submit(self, interaction: discord.Interaction):
        cog = interaction.client.cogs.get("JualBeli")
        ticket = cog.active_tickets.get(interaction.channel.id)
        if not ticket:
            await interaction.response.send_message("Data tiket tidak ditemukan.", ephemeral=True)
            return

        # Validasi user ID pembeli
        try:
            p2_id = int(self.p2_id_input.value.strip())
        except ValueError:
            await interaction.response.send_message("User ID tidak valid.", ephemeral=True)
            return

        try:
            p2 = await interaction.guild.fetch_member(p2_id)
        except Exception:
            await interaction.response.send_message("User tidak ditemukan di server.", ephemeral=True)
            return

        # Validasi fee
        try:
            fee = int(self.fee_input.value.strip().replace(".", "").replace(",", ""))
        except ValueError:
            await interaction.response.send_message("Fee harus berupa angka.", ephemeral=True)
            return

        # Validasi penanggung
        penanggung = self.penanggung_input.value.strip().lower()
        if penanggung not in ("penjual", "pembeli"):
            await interaction.response.send_message("Penanggung harus 'penjual' atau 'pembeli'.", ephemeral=True)
            return

        # Update channel permissions untuk pembeli
        await interaction.channel.set_permissions(p2, read_messages=True, send_messages=True)

        # Update ticket
        ticket["p2_id"] = p2.id
        ticket["fee_final"] = fee
        ticket["fee_penanggung"] = penanggung
        ticket["admin_id"] = interaction.user.id
        ticket["status"] = "menunggu_bayar"
        ticket["last_activity"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        save_jb_ticket(ticket)

        guild = interaction.guild
        p1 = guild.get_member(ticket["p1_id"])
        admin = interaction.user

        e = embed_setup(STORE_NAME, ticket, p1, p2, admin)
        # Edit embed awal
        try:
            msg = await interaction.channel.fetch_message(ticket.get("embed_message_id"))
            await msg.edit(embed=e, view=None)
        except Exception:
            await interaction.channel.send(embed=e)

        await interaction.response.send_message(
            f"{p2.mention} kamu telah ditambahkan ke tiket ini sebagai pembeli.", ephemeral=False
        )

# ─── BUTTON SETUP ADMIN ───────────────────────────────────────────────────────

class JBAdminSetupView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Setup (Admin)", style=discord.ButtonStyle.primary,
                       custom_id="jb_admin_setup")
    async def setup(self, interaction: discord.Interaction, button: discord.ui.Button):
        admin_role = interaction.guild.get_role(ADMIN_ROLE_ID)
        if admin_role not in interaction.user.roles:
            await interaction.response.send_message("Hanya admin.", ephemeral=True)
            return
        await interaction.response.send_modal(JBSetupModal())

# ─── COG ───────────────────────────────────────────────────────────────────────

class JualBeli(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_tickets: dict = load_jb_tickets()
        self.auto_close_loop.start()
        print(f"Cog JualBeli siap. ({len(self.active_tickets)} tiket dimuat)")

    def cog_unload(self):
        self.auto_close_loop.cancel()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        if message.channel.id in self.active_tickets:
            self.active_tickets[message.channel.id]["last_activity"] = datetime.datetime.now(
                datetime.timezone.utc).isoformat()
            save_jb_ticket(self.active_tickets[message.channel.id])

    # ─── AUTO CLOSE ──────────────────────────────────────────────────────────

    @tasks.loop(minutes=10)
    async def auto_close_loop(self):
        now = datetime.datetime.now(datetime.timezone.utc)
        to_close = []
        for ch_id, ticket in list(self.active_tickets.items()):
            last = ticket.get("last_activity") or ticket.get("opened_at")
            if not last:
                continue
            try:
                last_dt = datetime.datetime.fromisoformat(last)
                if last_dt.tzinfo is None:
                    last_dt = last_dt.replace(tzinfo=datetime.timezone.utc)
            except Exception:
                continue
            diff = (now - last_dt).total_seconds() / 60
            channel = self.bot.get_channel(ch_id)
            if not channel:
                delete_jb_ticket(ch_id)
                to_close.append(ch_id)
                continue
            if diff >= 120:
                to_close.append(ch_id)
                await self._force_close(channel, ticket, "Tiket otomatis ditutup karena tidak aktif selama 2 jam.")
            elif diff >= 60 and not ticket.get("warned"):
                ticket["warned"] = 1
                save_jb_ticket(ticket)
                # Hapus pesan peringatan lama kalau ada
                old_warn_id = ticket.get("warn_message_id")
                if old_warn_id:
                    try:
                        old_msg = await channel.fetch_message(old_warn_id)
                        await old_msg.delete()
                    except Exception:
                        pass
                warn = discord.Embed(title="PERINGATAN TIKET", color=0xFFA500)
                warn.add_field(name="\u200b", value=(
                    "Tiket ini tidak ada aktivitas selama **1 jam**.\n\n"
                    "Jika tidak ada aktivitas dalam 1 jam ke depan, tiket akan **otomatis ditutup** (<t:" + str(int(time.time()) + 3600) + ":R>)."
                ), inline=False)
                warn.set_footer(text=STORE_NAME)
                guild = channel.guild
                p1 = guild.get_member(ticket["p1_id"])
                p2 = guild.get_member(ticket["p2_id"]) if ticket.get("p2_id") else None
                mentions = " ".join(filter(None, [p1.mention if p1 else None, p2.mention if p2 else None]))
                warn_msg = await channel.send(content=mentions or None, embed=warn)
                ticket["warn_message_id"] = warn_msg.id
                save_jb_ticket(ticket)
        for ch_id in to_close:
            self.active_tickets.pop(ch_id, None)

    @auto_close_loop.before_loop
    async def before_loop(self):
        await self.bot.wait_until_ready()

    async def _force_close(self, channel, ticket, alasan: str):
        delete_jb_ticket(ticket["channel_id"])
        try:
            e = discord.Embed(title="Tiket Ditutup Otomatis", color=COLOR_BATAL)
            e.add_field(name="Alasan", value=alasan, inline=False)
            e.set_footer(text=STORE_NAME)
            await channel.send(embed=e)
            await asyncio.sleep(3)
            await channel.delete()
        except Exception as ex:
            print(f"[WARNING] JualBeli auto-close: {ex}")

    # ─── COMMANDS ────────────────────────────────────────────────────────────

    @commands.command(name="jbselesai")
    async def jbselesai(self, ctx):
        if not any(r.id == ADMIN_ROLE_ID for r in ctx.author.roles):
            return
        ch_id = ctx.channel.id
        if ch_id not in self.active_tickets:
            await ctx.send("Channel ini bukan tiket jual beli aktif.", delete_after=5)
            return
        ticket = self.active_tickets[ch_id]
        if ticket.get("status") != "item_diterima":
            await ctx.send(
                "Tiket belum sampai tahap konfirmasi item dari pembeli.\n"
                "Tunggu pembeli klik tombol **Item Diterima & Sesuai** terlebih dahulu.",
                delete_after=8
            )
            return

        guild = ctx.guild
        p1 = guild.get_member(ticket["p1_id"])
        p2 = guild.get_member(ticket["p2_id"]) if ticket.get("p2_id") else None
        admin = ctx.author

        ticket["status"] = "selesai"
        save_jb_ticket(ticket)

        e = embed_selesai(STORE_NAME, ticket, p1, p2, admin)
        try:
            msg = await ctx.channel.fetch_message(ticket.get("embed_message_id"))
            await msg.edit(embed=e, view=None)
        except Exception:
            await ctx.send(embed=e)
        try:
            await ctx.message.delete()
        except Exception:
            pass

        # Log
        log_ch = guild.get_channel(LOG_CHANNEL_ID)
        if log_ch:
            fee = ticket.get("fee_final")
            penanggung = ticket.get("fee_penanggung", "-")
            release = format_nominal(ticket["harga"] - fee) if fee and penanggung == "penjual" else format_nominal(ticket["harga"])
            log_e = discord.Embed(title=f"MIDMAN JUAL BELI SELESAI — {STORE_NAME}",
                                  color=COLOR_DONE,
                                  timestamp=datetime.datetime.now(datetime.timezone.utc))
            log_e.add_field(name="Admin", value=f"{admin.mention}\n`{admin.id}`", inline=False)
            log_e.add_field(name="Penjual", value=f"{p1.mention if p1 else '-'}\n`{ticket['p1_id']}`", inline=False)
            log_e.add_field(name="Pembeli", value=f"{p2.mention if p2 else '-'}\n`{ticket.get('p2_id', '-')}`", inline=False)
            log_e.add_field(name="Item", value=ticket["deskripsi"], inline=False)
            log_e.add_field(name="Harga", value=format_nominal(ticket["harga"]), inline=False)
            log_e.add_field(name="Fee", value=f"{format_nominal(fee)} (ditanggung {penanggung})" if fee else "-", inline=False)
            log_e.add_field(name="Dana ke Penjual", value=release, inline=False)
            log_e.set_footer(text=STORE_NAME)
            await log_ch.send(embed=log_e)

        # Transcript
        transcript_ch = guild.get_channel(TRANSCRIPT_CHANNEL_ID)
        if transcript_ch:
            try:
                f = await transcript_gen.generate(ctx.channel, STORE_NAME)
                await transcript_ch.send(
                    content=f"📄 Transcript `{ctx.channel.name}`",
                    file=f
                )
            except Exception as ex:
                print(f"[WARNING] JualBeli transcript: {ex}")

        # Log transaksi
        try:
            from utils.db import log_transaction
            import datetime as _dt
            opened_at_dt = _dt.datetime.fromisoformat(ticket["opened_at"]) if ticket.get("opened_at") else None
            now_dt = _dt.datetime.now(_dt.timezone.utc)
            durasi = int((now_dt - opened_at_dt).total_seconds()) if opened_at_dt else 0
            log_transaction(
                layanan="jualbeli",
                nominal=ticket.get("harga", 0) or 0,
                item=ticket.get("deskripsi", "-"),
                admin_id=ctx.author.id,
                user_id=ticket.get("p1_id"),
                closed_at=now_dt,
                durasi_detik=durasi
            )
        except Exception as e:
            print(f"[LOG] Gagal log transaksi jualbeli: {e}")
        # Assign Royal Customer
        try:
            royal_role = discord.utils.get(ctx.guild.roles, name="Royal Customer")
            if royal_role:
                for uid in [ticket.get("p1_id"), ticket.get("p2_id")]:
                    if uid:
                        member = ctx.guild.get_member(uid)
                        if member and royal_role not in member.roles:
                            await member.add_roles(royal_role)
        except Exception as e:
            print(f"[ROLE] Gagal assign Royal Customer: {e}")
        delete_jb_ticket(ch_id)
        del self.active_tickets[ch_id]
        await asyncio.sleep(5)
        await ctx.channel.delete()

    @commands.command(name="jbuang")
    async def jbuang(self, ctx):
        """Admin konfirmasi uang dari pembeli sudah diterima."""
        if not any(r.id == ADMIN_ROLE_ID for r in ctx.author.roles):
            return
        ch_id = ctx.channel.id
        if ch_id not in self.active_tickets:
            await ctx.send("Channel ini bukan tiket jual beli aktif.", delete_after=5)
            return
        ticket = self.active_tickets[ch_id]
        if ticket.get("status") != "menunggu_bayar":
            await ctx.send("Status tiket tidak sesuai. Pastikan admin sudah setup dan pembeli belum konfirmasi item.", delete_after=8)
            return
        if not ticket.get("p2_id"):
            await ctx.send("Pembeli belum di-setup. Gunakan tombol Setup (Admin) terlebih dahulu.", delete_after=8)
            return

        ticket["status"] = "uang_diterima"
        ticket["last_activity"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        save_jb_ticket(ticket)

        guild = ctx.guild
        p1 = guild.get_member(ticket["p1_id"])
        p2 = guild.get_member(ticket["p2_id"])
        admin = ctx.author

        e = embed_uang_diterima(STORE_NAME, ticket, p1, p2, admin)
        view = JBItemDiterimaView()
        try:
            msg = await ctx.channel.fetch_message(ticket.get("embed_message_id"))
            await msg.edit(embed=e, view=view)
        except Exception:
            msg = await ctx.channel.send(embed=e, view=view)
            ticket["embed_message_id"] = msg.id
            save_jb_ticket(ticket)
        try:
            await ctx.message.delete()
        except Exception:
            pass

    @commands.command(name="jbbatal")
    async def jbbatal(self, ctx, *, alasan: str = "Tidak ada alasan"):
        if not any(r.id == ADMIN_ROLE_ID for r in ctx.author.roles):
            return
        ch_id = ctx.channel.id
        if ch_id not in self.active_tickets:
            await ctx.send("Channel ini bukan tiket jual beli aktif.", delete_after=5)
            return
        ticket = self.active_tickets[ch_id]
        guild = ctx.guild
        p1 = guild.get_member(ticket["p1_id"])
        p2 = guild.get_member(ticket["p2_id"]) if ticket.get("p2_id") else None

        e = discord.Embed(title="Tiket Jual Beli Dibatalkan", color=COLOR_BATAL,
                          timestamp=datetime.datetime.now(datetime.timezone.utc))
        e.add_field(name="Dibatalkan oleh", value=ctx.author.mention, inline=True)
        e.add_field(name="Alasan", value=alasan, inline=False)
        e.add_field(name="\u200b", value="Tiket akan ditutup dalam 5 detik.", inline=False)
        e.set_footer(text=STORE_NAME)

        mentions = " ".join(filter(None, [p1.mention if p1 else None, p2.mention if p2 else None]))
        await ctx.send(content=mentions or None, embed=e)

        delete_jb_ticket(ch_id)
        del self.active_tickets[ch_id]
        await asyncio.sleep(5)
        await ctx.channel.delete()


async def setup(bot):
    await bot.add_cog(JualBeli(bot))
    bot.add_view(JBAdminSetupView())
    bot.add_view(JBItemDiterimaView())
    print("Cog JualBeli siap.")
