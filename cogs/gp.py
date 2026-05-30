"""
cogs/gp.py — Topup Robux via Gamepass
Flow: input nominal → preview harga → konfirmasi → tiket → bayar → gamepass link → selesai
"""
import math
import time
import asyncio
import datetime
import discord
from discord.ext import commands, tasks
from utils.config import (
    ADMIN_ROLE_ID, LOG_CHANNEL_ID, STORE_NAME,
    TICKET_CATEGORY_ID, GUILD_ID, TRANSCRIPT_CHANNEL_ID
)
from utils.db import get_conn
from utils.gp_db import (
    load_gp_tickets, save_gp_ticket, delete_gp_ticket,
    get_gp_rate, set_gp_rate
)
from utils.robux_stock import get_available as get_robux_stock_available, get_out_total as get_robux_out_total, record_outgoing as record_robux_outgoing
from utils.store_hours import is_store_open

GP_CATALOG_CHANNEL_ID = 1478917118715236603
MIN_ROBUX = 300
THUMBNAIL = "https://i.imgur.com/CWtUCzj.png"
COLOR = 0x9B59B6

def ensure_gp_table():
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS gp_tickets (
            channel_id       INTEGER PRIMARY KEY,
            user_id          INTEGER,
            robux            INTEGER,
            gp_price         INTEGER,
            rate             INTEGER,
            total            INTEGER,
            paid             INTEGER DEFAULT 0,
            gp_link          TEXT,
            admin_id         INTEGER,
            opened_at        TEXT,
            warned           INTEGER DEFAULT 0,
            warn_message_id  INTEGER,
            last_activity    TEXT
        )
    """)
    for col, defval in [
        ("warned",          "INTEGER DEFAULT 0"),
        ("warn_message_id", "INTEGER"),
        ("last_activity",   "TEXT"),
        ("gp_link",         "TEXT"),
    ]:
        try:
            conn.execute(f"ALTER TABLE gp_tickets ADD COLUMN {col} {defval}")
        except Exception as e:
            if "duplicate column" not in str(e).lower():
                print(f"[GP] Migration {col}: {e}")
    conn.commit()
    conn.close()

ensure_gp_table()


def calc_gp_price(robux: int) -> int:
    """Hitung harga gamepass yang harus dibuat buyer (after 30% Roblox cut)."""
    return math.ceil(robux / 0.7)


def build_catalog_embed(rate: int) -> discord.Embed:
    stock_available = get_robux_stock_available()
    stock_out_total = get_robux_out_total()
    embed = discord.Embed(
        title=f"TOPUP ROBUX VIA GAMEPASS — {STORE_NAME}",
        description=(
            f"Topup Robux aman tanpa perlu kasih password akun!\n"
            f"Robux masuk dalam **3-7 hari kerja** setelah admin beli gamepass kamu.\n\n"
            f"Minimal order: **{MIN_ROBUX} Robux**\n\n"
            f"Klik tombol di bawah untuk mulai order."
        ),
        color=COLOR,
        timestamp=datetime.datetime.now(datetime.timezone.utc)
    )
    embed.add_field(
        name="Rate",
        value=f"**Rp {rate:,}/Robux**",
        inline=False
    )
    embed.add_field(name="Stock Tersedia", value=f"**{stock_available:,} Robux**", inline=True)
    embed.add_field(name="Robux Keluar (Total)", value=f"**{stock_out_total:,} Robux**", inline=True)
    embed.add_field(
        name="Cara Order",
        value=(
            "1. Klik **Order Sekarang**\n"
            "2. Input jumlah Robux yang diinginkan\n"
            "3. Bot hitung harga gamepass + total bayar\n"
            "4. Konfirmasi → tiket terbuka\n"
            "5. Bayar tagihan ke admin\n"
            "6. Buat gamepass sesuai harga yang ditentukan, kirim link ke tiket\n"
            "7. Admin beli gamepass kamu\n"
            "8. Tunggu Robux masuk 3-7 hari 🎉"
        ),
        inline=False
    )
    embed.add_field(
        name="Catatan",
        value=(
            "• Robux yang kamu terima adalah **after tax** (sudah dipotong 30% Roblox)\n"
            "• Jangan hapus gamepass sebelum Robux masuk\n"
            "• Harga gamepass dihitung otomatis oleh bot"
        ),
        inline=False
    )
    embed.set_footer(text=f"{STORE_NAME} • Rate dapat berubah sewaktu-waktu")
    return embed


class CatalogView(discord.ui.View):
    def __init__(self, store_open: bool | None = None):
        super().__init__(timeout=None)
        store_open = is_store_open() if store_open is None else store_open
        if not store_open:
            for child in self.children:
                child.disabled = True

    @discord.ui.button(label="Order", style=discord.ButtonStyle.primary, custom_id="gp_order", emoji="🎫")
    async def order(self, interaction: discord.Interaction, button: discord.ui.Button):
        rate = get_gp_rate()
        if rate == 0:
            await interaction.response.send_message("Rate belum diset oleh admin. Coba lagi nanti.", ephemeral=True)
            return
        from utils.service_info import get_service_info, build_info_embed
        info = get_service_info("gp")
        has_info = any([info["description"], info["terms"], info["payment_info"]])
        if has_info:
            embed = build_info_embed("Topup Robux via Gamepass", info, COLOR)
            await interaction.response.send_message(embed=embed, view=GPInfoView(rate), ephemeral=True)
        else:
            modal = NominalModal(rate)
            await interaction.response.send_modal(modal)


class GPInfoView(discord.ui.View):
    def __init__(self, rate: int):
        super().__init__(timeout=120)
        self.rate = rate

    @discord.ui.button(label="✅ Lanjutkan", style=discord.ButtonStyle.success, custom_id="gp_info_lanjut")
    async def lanjut(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = NominalModal(self.rate)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="❌ Batal", style=discord.ButtonStyle.danger, custom_id="gp_info_batal")
    async def batal(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="Dibatalkan.", embed=None, view=None)


class NominalModal(discord.ui.Modal, title="Topup Robux via Gamepass"):
    nominal = discord.ui.TextInput(
        label=f"Jumlah Robux (minimal {MIN_ROBUX})",
        placeholder=f"Contoh: 500",
        min_length=1,
        max_length=6,
    )

    def __init__(self, rate: int):
        super().__init__()
        self.rate = rate

    async def on_submit(self, interaction: discord.Interaction):
        try:
            robux = int(self.nominal.value.strip())
        except ValueError:
            await interaction.response.send_message("Input tidak valid, masukkan angka.", ephemeral=True)
            return

        if robux < MIN_ROBUX:
            await interaction.response.send_message(f"Minimal order {MIN_ROBUX} Robux.", ephemeral=True)
            return

        gp_price = calc_gp_price(robux)
        total = gp_price * self.rate

        embed = discord.Embed(
            title="📋 Konfirmasi Order Robux via Gamepass",
            color=COLOR
        )
        embed.add_field(name="Rate", value=f"**Rp {self.rate:,}/Robux**", inline=True)
        embed.add_field(name="Robux yang Diterima", value=f"**{robux} Robux** (after tax)", inline=True)
        embed.add_field(name="Total Bayar", value=f"**Rp {total:,}**", inline=True)
        embed.add_field(
            name="Harga Gamepass yang Harus Dibuat",
            value=f"**{gp_price} Robux**\n*(set harga gamepass kamu sebesar ini)*",
            inline=False
        )
        embed.add_field(
            name="Catatan",
            value="Klik **Konfirmasi** untuk buka tiket dan lanjutkan transaksi.",
            inline=False
        )

        view = ConfirmView(robux=robux, gp_price=gp_price, rate=self.rate, total=total)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class ConfirmView(discord.ui.View):
    def __init__(self, robux, gp_price, rate, total):
        super().__init__(timeout=120)
        self.robux = robux
        self.gp_price = gp_price
        self.rate = rate
        self.total = total

    @discord.ui.button(label="✅ Konfirmasi", style=discord.ButtonStyle.success, custom_id="gp_confirm")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        cog = interaction.client.cogs.get("GPStore")
        member = interaction.user
        guild = interaction.guild

        for ch_id, t in cog.active_tickets.items():
            if t["user_id"] == member.id:
                existing = guild.get_channel(ch_id)
                if existing:
                    await interaction.response.edit_message(
                        content=f"Kamu masih punya tiket aktif di {existing.mention}!",
                        embed=None, view=None
                    )
                    return

        await interaction.response.edit_message(content="Membuat tiket...", embed=None, view=None)

        ticket_category = guild.get_channel(TICKET_CATEGORY_ID)
        admin_role = guild.get_role(ADMIN_ROLE_ID)
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            member: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        }
        if admin_role:
            overwrites[admin_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        channel = await guild.create_text_channel(
            name=f"gp-{member.name}", category=ticket_category, overwrites=overwrites
        )

        now = datetime.datetime.now(datetime.timezone.utc)
        ticket = {
            "channel_id":  channel.id,
            "user_id":     member.id,
            "robux":       self.robux,
            "gp_price":    self.gp_price,
            "rate":        self.rate,
            "total":       self.total,
            "paid":        False,
            "gp_link":     None,
            "admin_id":    None,
            "opened_at":   now.isoformat(),
            "last_activity": now.isoformat(),
            "warned":      False,
            "warn_message_id": None,
        }
        cog.active_tickets[channel.id] = ticket
        save_gp_ticket(ticket)

        embed = discord.Embed(
            title=f"TOPUP ROBUX VIA GAMEPASS — {STORE_NAME}",
            color=COLOR,
            timestamp=now
        )
        embed.add_field(name="Rate", value=f"**Rp {self.rate:,}/Robux**", inline=True)
        embed.add_field(name="Member", value=member.mention, inline=True)
        embed.add_field(name="Robux Diterima", value=f"{self.robux} Robux (after tax)", inline=True)
        embed.add_field(name="Total Tagihan", value=f"**Rp {self.total:,}**", inline=True)
        embed.add_field(
            name="Harga Gamepass",
            value=f"**{self.gp_price} Robux**\n*(buat gamepass dengan harga ini setelah bayar)*",
            inline=True
        )
        embed.add_field(
            name="Langkah Selanjutnya",
            value=(
                "1. **Bayar tagihan** ke admin (QRIS/DANA/BCA)\n"
                "2. Kirim bukti pembayaran di tiket ini\n"
                "3. Setelah admin konfirmasi, buat gamepass dengan harga **{} Robux**\n"
                "4. Kirim link gamepass di sini\n"
                "5. Tunggu Robux masuk 3-7 hari 🎉"
            ).format(self.gp_price),
            inline=False
        )
        embed.add_field(
            name="Peringatan",
            value="Tiket tidak aktif 2 jam akan otomatis ditutup.",
            inline=False
        )
        embed.set_footer(text=f"{STORE_NAME} • Jangan hapus gamepass sebelum Robux masuk")

        ping = admin_role.mention if admin_role else ""
        await channel.send(
            content=f"Halo {member.mention}! Tiket topup Robux via gamepass telah dibuat. {ping}",
            embed=embed
        )
        await interaction.followup.send(f"Tiket dibuat! {channel.mention}", ephemeral=True)

    @discord.ui.button(label="❌ Batal", style=discord.ButtonStyle.danger, custom_id="gp_cancel_confirm")
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="Order dibatalkan.", embed=None, view=None)


class GPStore(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.catalog_message_id = None
        self.active_tickets = load_gp_tickets()
        self.auto_close_task.start()

    def cog_unload(self):
        self.auto_close_task.cancel()

    @tasks.loop(minutes=10)
    async def auto_close_task(self):
        now = datetime.datetime.now(datetime.timezone.utc)
        for ch_id, ticket in list(self.active_tickets.items()):
            if ticket.get("paid"):
                continue
            last = ticket.get("last_activity") or ticket.get("opened_at")
            if not last:
                continue
            last_dt = datetime.datetime.fromisoformat(last)
            if last_dt.tzinfo is None:
                last_dt = last_dt.replace(tzinfo=datetime.timezone.utc)
            elapsed = (now - last_dt).total_seconds()
            guild = self.bot.get_guild(GUILD_ID)
            if not guild:
                continue
            channel = guild.get_channel(ch_id)
            if elapsed >= 7200:
                delete_gp_ticket(ch_id)
                self.active_tickets.pop(ch_id, None)
                if channel:
                    try:
                        await channel.send(
                            "Tiket ini otomatis ditutup karena tidak ada aktivitas selama 2 jam. "
                            "Channel akan dihapus dalam 10 detik."
                        )
                        await asyncio.sleep(10)
                        await channel.delete()
                    except Exception:
                        pass
            elif elapsed >= 3600 and not ticket.get("warned"):
                if channel:
                    try:
                        warn_embed = discord.Embed(title="PERINGATAN TIKET", color=0xFFA500)
                        warn_embed.add_field(name="\u200b", value=(
                            "Tiket tidak ada aktivitas selama **1 jam**.\n\n"
                            "Segera selesaikan pembayaran atau hubungi admin.\n\n"
                            "Tiket akan otomatis ditutup dalam **1 jam lagi** (<t:"
                            + str(int(time.time()) + 3600) + ":R>)."
                        ), inline=False)
                        _user = guild.get_member(ticket["user_id"])
                        _mn = _user.mention if _user else ""
                        warn_msg = await channel.send(content=_mn, embed=warn_embed)
                        ticket["warn_message_id"] = warn_msg.id
                    except Exception:
                        pass
                ticket["warned"] = True
                save_gp_ticket(ticket)

    @auto_close_task.before_loop
    async def before_auto_close(self):
        await self.bot.wait_until_ready()

    async def refresh_catalog(self):
        guild = self.bot.get_guild(GUILD_ID)
        if not guild:
            return
        ch = guild.get_channel(GP_CATALOG_CHANNEL_ID)
        if not ch:
            return
        rate = get_gp_rate()
        embed = build_catalog_embed(rate)
        if self.catalog_message_id:
            try:
                msg = await ch.fetch_message(self.catalog_message_id)
                await msg.edit(embed=embed, view=CatalogView(store_open=is_store_open()))
                return
            except Exception:
                pass
        async for msg in ch.history(limit=20):
            if msg.author == self.bot.user:
                try:
                    await msg.delete()
                except Exception:
                    pass
        sent = await ch.send(embed=embed, view=CatalogView(store_open=is_store_open()))
        self.catalog_message_id = sent.id

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        custom_id = ""
        try:
            custom_id = (interaction.data or {}).get("custom_id", "")
        except Exception:
            custom_id = ""

        # Backward-compat: old tickets might still have SUDAH BAYAR / VERIFIKASI buttons.
        if custom_id.startswith("gp_paid_") or custom_id.startswith("gp_verify_"):
            try:
                await interaction.response.send_message(
                    "Fitur tombol pembayaran sudah dinonaktifkan. Kirim bukti pembayaran di chat, admin akan konfirmasi manual.",
                    ephemeral=True,
                )
            except Exception:
                pass

    @commands.command(name="gpdone")
    async def gpdone_cmd(self, ctx):
        """Admin konfirmasi sudah beli gamepass & selesaikan tiket."""
        if not any(r.id == ADMIN_ROLE_ID for r in ctx.author.roles):
            return
        await ctx.message.delete()
        channel_id = ctx.channel.id
        if channel_id not in self.active_tickets:
            await ctx.send("Channel ini bukan tiket GP aktif.", delete_after=5)
            return
        ticket = self.active_tickets[channel_id]
        if not ticket.get("gp_link"):
            await ctx.send("Link gamepass belum dikirim oleh member!", delete_after=5)
            return

        member = ctx.guild.get_member(ticket["user_id"])
        now = datetime.datetime.now(datetime.timezone.utc)
        opened_at = datetime.datetime.fromisoformat(ticket["opened_at"])
        durasi_secs = int((now - opened_at).total_seconds())

        from utils.counter import next_ticket_number
        nomor = next_ticket_number()

        transcript_ch = ctx.guild.get_channel(TRANSCRIPT_CHANNEL_ID)
        if transcript_ch:
            try:
                from utils.transcript import generate as generate_transcript
                transcript_file = await generate_transcript(ctx.channel, STORE_NAME)
                await transcript_ch.send(
                    content=f"Transcript GP Topup — {ctx.channel.name}",
                    file=transcript_file
                )
            except Exception as e:
                print(f"[GP] Gagal kirim transcript: {e}")

        log_ch = ctx.guild.get_channel(LOG_CHANNEL_ID)
        if log_ch:
            log_embed = discord.Embed(
                title=f"GP TOPUP SUKSES — #{nomor:04d}",
                description="Gamepass berhasil dibeli. Robux masuk 3-7 hari.",
                color=COLOR,
                timestamp=now
            )
            log_embed.add_field(name="Admin", value=f"{ctx.author.mention}\n`{ctx.author.id}`", inline=False)
            log_embed.add_field(name="Member", value=f"{member.mention if member else ticket['user_id']}\n`{ticket['user_id']}`", inline=False)
            log_embed.add_field(name="Robux", value=f"{ticket['robux']} Robux (after tax)", inline=True)
            log_embed.add_field(name="Harga Gamepass", value=f"{ticket['gp_price']} Robux", inline=True)
            log_embed.add_field(name="Total", value=f"Rp {ticket['total']:,}", inline=False)
            log_embed.set_footer(text=STORE_NAME)
            await log_ch.send(embed=log_embed)

        try:
            from utils.db import log_transaction
            log_transaction(
                layanan="gp_topup",
                nominal=ticket.get("total", 0),
                item=f"{ticket.get('robux', 0)} Robux via Gamepass",
                admin_id=ctx.author.id,
                user_id=ticket.get("user_id"),
                closed_at=now,
                durasi_detik=durasi_secs
            )
        except Exception as e:
            print(f"[GP] Gagal log transaksi: {e}")

        # Stock Robux (global)
        try:
            record_robux_outgoing(int(ticket.get("robux", 0) or 0))
            await self.refresh_catalog()
            robux_cog = self.bot.cogs.get("RobuxStore")
            if robux_cog and hasattr(robux_cog, "refresh_catalog"):
                await robux_cog.refresh_catalog()
            vilog_cog = self.bot.cogs.get("Vilog")
            if vilog_cog and hasattr(vilog_cog, "refresh_embed"):
                await vilog_cog.refresh_embed(ctx.guild)
        except Exception as e:
            print(f"[Stock] Gagal update stock robux (GP): {e}")

        try:
            royal_role = discord.utils.get(ctx.guild.roles, name="Royal Customer")
            if royal_role and member and royal_role not in member.roles:
                await member.add_roles(royal_role)
        except Exception as e:
            print(f"[GP] Gagal assign Royal Customer: {e}")

        await ctx.channel.send(
            f"✅ Gamepass sudah dibeli! Robux kamu akan masuk dalam 3-7 hari kerja.\n"
            f"Terima kasih telah berbelanja di {STORE_NAME}!\n"
            f"Channel ini akan dihapus dalam 10 detik."
        )
        delete_gp_ticket(channel_id)
        del self.active_tickets[channel_id]
        await asyncio.sleep(10)
        await ctx.channel.delete()

    @commands.command(name="gplink")
    async def gplink_cmd(self, ctx, *, link: str = None):
        """Member kirim link gamepass via command (opsional, bisa juga tulis langsung)."""
        channel_id = ctx.channel.id
        if channel_id not in self.active_tickets:
            return
        ticket = self.active_tickets[channel_id]
        if ctx.author.id != ticket["user_id"]:
            return
        if not link:
            await ctx.send("Format: `!gplink <url gamepass>`", delete_after=5)
            return
        ticket["gp_link"] = link
        ticket["last_activity"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        save_gp_ticket(ticket)
        admin_role = ctx.guild.get_role(ADMIN_ROLE_ID)
        ping = admin_role.mention if admin_role else ""
        await ctx.send(
            f"{ping} Link gamepass telah dikirim!\n"
            f"🔗 {link}\n"
            f"Admin silakan beli gamepass ini, lalu ketik `!gpdone` untuk selesaikan tiket."
        )

    @commands.command(name="gpbatal")
    async def gpbatal_cmd(self, ctx, *, alasan: str = None):
        if not any(r.id == ADMIN_ROLE_ID for r in ctx.author.roles):
            return
        await ctx.message.delete()
        channel_id = ctx.channel.id
        if channel_id not in self.active_tickets:
            await ctx.send("Channel ini bukan tiket GP aktif.", delete_after=5)
            return
        alasan_str = alasan or "Tidak ada alasan"
        await ctx.channel.send(
            f"Tiket dibatalkan oleh {ctx.author.mention}.\n"
            f"Alasan: {alasan_str}\n"
            f"Channel akan dihapus dalam 5 detik."
        )
        delete_gp_ticket(channel_id)
        del self.active_tickets[channel_id]
        await asyncio.sleep(5)
        await ctx.channel.delete()

    @commands.command(name="gpcatalog")
    async def gpcatalog_cmd(self, ctx):
        if not any(r.id == ADMIN_ROLE_ID for r in ctx.author.roles):
            return
        await ctx.message.delete()
        await self.refresh_catalog()
        await ctx.send("Catalog GP dikirim!", delete_after=5)

    @commands.command(name="gprate")
    async def gprate_cmd(self, ctx, rate: int = None):
        if not any(r.id == ADMIN_ROLE_ID for r in ctx.author.roles):
            return
        await ctx.message.delete()
        if rate is None or rate <= 0:
            current = get_gp_rate()
            await ctx.send(f"Rate GP saat ini: **Rp {current:,}/Robux**\nGunakan `!gprate <angka>` untuk ubah.", delete_after=10)
            return
        set_gp_rate(rate)
        await self.refresh_catalog()
        await ctx.send(f"Rate GP diubah ke **Rp {rate:,}/Robux** dan catalog diperbarui.", delete_after=5)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        channel_id = message.channel.id
        if channel_id not in self.active_tickets:
            return
        ticket = self.active_tickets[channel_id]
        ticket["last_activity"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        save_gp_ticket(ticket)

        if not ticket.get("gp_link"):
            content = message.content.strip()
            if content.startswith("http") and "roblox.com" in content:
                ticket["gp_link"] = content
                save_gp_ticket(ticket)
                await message.channel.send(
                    f"Link gamepass diterima!\n"
                    f"🔗 {content}\n"
                    f"Admin silakan beli gamepass ini, lalu ketik `!gpdone` untuk selesaikan tiket."
                )


async def setup(bot):
    await bot.add_cog(GPStore(bot))
    bot.add_view(CatalogView())
    print("Cog GPStore siap.")
