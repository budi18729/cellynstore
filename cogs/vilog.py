"""
cogs/vilog.py — Topup Robux via Login (Vilog)

Flow: admin posts catalog → member clicks Order → input jumlah robux (kelipatan 500) + login → tiket dibuat.
Admin set rate via !ratevilog <angka> (Rp per Robux).
"""

import asyncio
import datetime
import re

import discord
from discord.ext import commands

from utils.config import (
    ADMIN_ROLE_ID,
    GUILD_ID,
    STORE_NAME,
    TICKET_CATEGORY_ID,
    TRANSCRIPT_CHANNEL_ID,
    LOG_CHANNEL_ID,
    VILOG_CATALOG_CHANNEL_ID,
)
from utils.db import get_conn
from utils.vilog_db import load_vilog_tickets, save_vilog_ticket, delete_vilog_ticket
from utils.robux_stock import get_available as get_robux_stock_available, get_out_total as get_robux_out_total, record_outgoing as record_robux_outgoing
from utils.store_hours import is_store_open

COLOR = 0xF1C40F

MIN_ROBUX = 500
STEP_ROBUX = 500
MAX_ROBUX = 10_000


def _get_setting(key: str) -> str | None:
    conn = get_conn()
    row = conn.execute("SELECT value FROM bot_state WHERE key=?", (key,)).fetchone()
    conn.close()
    return row["value"] if row else None


def _set_setting(key: str, value: str):
    conn = get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO bot_state (key, value) VALUES (?,?)",
        (key, value),
    )
    conn.commit()
    conn.close()


def get_vilog_rate() -> int:
    raw = _get_setting("vilog_rate") or ""
    try:
        return int(raw)
    except Exception:
        return 0


def set_vilog_rate(rate: int):
    _set_setting("vilog_rate", str(rate))


def _format_rp(amount: int) -> str:
    return f"Rp {amount:,}"


def _calc_total(robux: int, rate: int) -> int:
    return robux * rate


def _sanitize_channel_name(name: str) -> str:
    name = name.lower().strip()
    name = re.sub(r"[^a-z0-9\-]+", "-", name)
    name = re.sub(r"-{2,}", "-", name).strip("-")
    if not name:
        return "member"
    return name[:60]


def build_catalog_embed(rate: int) -> discord.Embed:
    price_lines = []
    if rate > 0:
        for rbx in range(MIN_ROBUX, MAX_ROBUX + 1, STEP_ROBUX):
            price_lines.append(f"{rbx:>5} = {_format_rp(_calc_total(rbx, rate))}")
    price_table = "```" + "\n".join(price_lines) + "```" if price_lines else "-"
    stock_available = get_robux_stock_available()
    stock_out_total = get_robux_out_total()
    embed = discord.Embed(
        title=f"TOPUP ROBUX VIA LOGIN (VILOG) — {STORE_NAME}",
        description=(
            "Topup Robux via login akun Roblox.\n"
            f"Order tersedia dalam kelipatan **{STEP_ROBUX} Robux**"
        ),
        color=COLOR,
        timestamp=datetime.datetime.now(datetime.timezone.utc),
    )
    embed.add_field(name="Daftar harga", value=price_table, inline=False)
    embed.add_field(name="Stock Tersedia", value=f"**{stock_available:,} Robux**", inline=True)
    embed.add_field(name="Robux Keluar (Total)", value=f"**{stock_out_total:,} Robux**", inline=True)
    embed.add_field(
        name="Catatan",
        value=(
            "- Premium hanya bisa 1x per bulan\n"
            "- Proses 15–30 menit (maks. 3 jam tergantung antrian)\n"
            "- Wajib menyertakan kode backup terbaru (min. 3)\n"
            "- Pastikan email & password benar agar proses lancar\n"
            "- Akun roblox wajib memiliki email aktif"
        ),
        inline=False,
    )
    embed.set_footer(text=f"{STORE_NAME} • Support kelipatan {STEP_ROBUX} (max {MAX_ROBUX})")
    return embed


class VilogOrderModal(discord.ui.Modal, title="Order Robux Via Login (Vilog)"):
    robux = discord.ui.TextInput(
        label="Jumlah Robux",
        placeholder=f"Contoh: {MIN_ROBUX} / {MIN_ROBUX + STEP_ROBUX} / 1000",
        required=True,
        max_length=10,
    )
    email = discord.ui.TextInput(
        label="Email",
        placeholder="Email akun Roblox kamu",
        required=True,
        max_length=128,
    )
    password = discord.ui.TextInput(
        label="Password Roblox",
        placeholder="Password akun Roblox kamu",
        required=True,
        max_length=128,
        style=discord.TextStyle.short,
    )
    backup_codes = discord.ui.TextInput(
        label="Kode Backup (min 3)",
        placeholder="Tempel minimal 3 kode backup, pisahkan pakai enter",
        required=True,
        max_length=600,
        style=discord.TextStyle.paragraph,
    )
    premium = discord.ui.TextInput(
        label="Premium (yes/no) (opsional)",
        placeholder="yes atau no (boleh kosong)",
        required=False,
        max_length=8,
    )

    def __init__(self, cog: "Vilog"):
        super().__init__()
        self.cog = cog

    async def on_submit(self, interaction: discord.Interaction):
        rate = get_vilog_rate()
        if rate <= 0:
            await interaction.response.send_message(
                "Rate Vilog belum diset oleh admin. Coba lagi nanti.",
                ephemeral=True,
            )
            return

        try:
            robux = int(str(self.robux.value).replace(".", "").replace(",", "").strip())
        except Exception:
            await interaction.response.send_message(
                f"Jumlah robux tidak valid. Contoh: `{MIN_ROBUX}` / `{MIN_ROBUX + STEP_ROBUX}`.",
                ephemeral=True,
            )
            return

        if robux < MIN_ROBUX or robux % STEP_ROBUX != 0:
            await interaction.response.send_message(
                f"Jumlah robux harus kelipatan {STEP_ROBUX} dan minimal {MIN_ROBUX}.",
                ephemeral=True,
            )
            return
        if robux > MAX_ROBUX:
            await interaction.response.send_message(
                f"Maksimal order adalah {MAX_ROBUX} Robux.",
                ephemeral=True,
            )
            return

        codes_raw = str(self.backup_codes.value).strip()
        codes = [c.strip() for c in re.split(r"[\n,]+", codes_raw) if c.strip()]
        if len(codes) < 3:
            await interaction.response.send_message(
                "Kode backup minimal 3. Pisahkan dengan enter atau koma.",
                ephemeral=True,
            )
            return

        premium_raw = str(self.premium.value).strip().lower()
        premium = False
        if premium_raw:
            if premium_raw in {"yes", "y", "true", "1"}:
                premium = True
            elif premium_raw in {"no", "n", "false", "0"}:
                premium = False
            else:
                await interaction.response.send_message(
                    "Field premium harus `yes` atau `no` (atau kosong).",
                    ephemeral=True,
                )
                return

        await interaction.response.defer(ephemeral=True, thinking=True)
        await self.cog.create_ticket(
            interaction=interaction,
            robux=robux,
            email=str(self.email.value).strip(),
            password=str(self.password.value).strip(),
            backup_codes=codes,
            premium=premium,
            rate=rate,
        )


class VilogCatalogView(discord.ui.View):
    def __init__(self, cog: "Vilog", store_open: bool | None = None):
        super().__init__(timeout=None)
        self.cog = cog
        store_open = is_store_open() if store_open is None else store_open
        if not store_open:
            for child in self.children:
                child.disabled = True

    @discord.ui.button(label="Order", style=discord.ButtonStyle.primary, custom_id="vilog_order", emoji="🎫")
    async def order(self, interaction: discord.Interaction, button: discord.ui.Button):
        rate = get_vilog_rate()
        if rate <= 0:
            await interaction.response.send_message(
                "Rate Vilog belum diset oleh admin. Coba lagi nanti.",
                ephemeral=True,
            )
            return
        # Cegah ticket dobel per user
        if any(t.get("user_id") == interaction.user.id for t in self.cog.active_tickets.values()):
            await interaction.response.send_message(
                "Kamu masih punya tiket Vilog yang aktif. Selesaikan dulu tiket itu.",
                ephemeral=True,
            )
            return
        await interaction.response.send_modal(VilogOrderModal(self.cog))


class Vilog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.catalog_message_id: int | None = None
        self.active_tickets = load_vilog_tickets()
        raw_msg = _get_setting("vilog_catalog_message_id")
        if raw_msg and raw_msg.isdigit():
            self.catalog_message_id = int(raw_msg)

    async def refresh_embed(self, guild: discord.Guild):
        """Refresh catalog embed (dipanggil dari command admin atau cog lain)."""
        ch = guild.get_channel(VILOG_CATALOG_CHANNEL_ID)
        if not ch:
            return
        rate = get_vilog_rate()
        embed = build_catalog_embed(rate)
        view = VilogCatalogView(self, store_open=is_store_open())
        if self.catalog_message_id:
            try:
                msg = await ch.fetch_message(self.catalog_message_id)
                await msg.edit(embed=embed, view=view)
                return
            except Exception:
                self.catalog_message_id = None
        try:
            msg = await ch.send(embed=embed, view=view)
            self.catalog_message_id = msg.id
            _set_setting("vilog_catalog_message_id", str(msg.id))
        except Exception as e:
            print(f"[Vilog] Gagal kirim catalog: {e}")

    async def create_ticket(
        self,
        interaction: discord.Interaction,
        robux: int,
        email: str,
        password: str,
        backup_codes: list[str],
        premium: bool,
        rate: int,
    ):
        guild = self.bot.get_guild(GUILD_ID)
        if not guild:
            await interaction.followup.send("Guild tidak ditemukan.", ephemeral=True)
            return

        category = guild.get_channel(TICKET_CATEGORY_ID)
        if not category or not isinstance(category, discord.CategoryChannel):
            await interaction.followup.send("Kategori tiket belum diset / invalid.", ephemeral=True)
            return

        admin_role = guild.get_role(ADMIN_ROLE_ID)
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
        }
        if admin_role:
            overwrites[admin_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)

        total = _calc_total(robux, rate)
        ch_name = f"vilog-{_sanitize_channel_name(interaction.user.display_name)}"
        try:
            channel = await guild.create_text_channel(
                name=ch_name,
                category=category,
                overwrites=overwrites,
                reason="Vilog ticket created",
            )
        except Exception as e:
            await interaction.followup.send(f"Gagal membuat channel tiket: {e}", ephemeral=True)
            return

        now = datetime.datetime.now(datetime.timezone.utc)
        ticket = {
            "channel_id": channel.id,
            "user_id": interaction.user.id,
            "username_roblox": email,  # legacy column
            "email": email,
            "password": password,
            "backup_codes": "\n".join(backup_codes),
            "premium": premium,
            "boost": {"nama": "Vilog", "robux": robux},
            "metode": "vilog",
            "nominal": total,
            "admin_id": None,
            "opened_at": now.isoformat(),
            "warned": False,
        }
        self.active_tickets[channel.id] = ticket
        save_vilog_ticket(ticket)

        info_embed = discord.Embed(
            title="🎫 Tiket Topup Robux via Login (Vilog)",
            color=COLOR,
            timestamp=now,
        )
        info_embed.add_field(name="Member", value=f"{interaction.user.mention}\n`{interaction.user.id}`", inline=False)
        info_embed.add_field(name="Robux", value=f"**{robux} Robux**", inline=True)
        info_embed.add_field(name="Rate", value=f"**{_format_rp(rate)}/Robux**", inline=True)
        info_embed.add_field(name="Total Tagihan", value=f"**{_format_rp(total)}**", inline=False)
        info_embed.add_field(name="Email", value=f"`{email}`", inline=True)
        info_embed.add_field(name="Password", value=f"||`{password}`||", inline=True)
        codes_preview = "\n".join(f"||`{c}`||" for c in backup_codes[:10])
        if len(backup_codes) > 10:
            codes_preview += f"\n(+{len(backup_codes) - 10} kode lagi)"
        info_embed.add_field(name="Kode Backup", value=codes_preview, inline=False)
        info_embed.add_field(name="Premium", value="Yes" if premium else "No", inline=True)
        info_embed.add_field(
            name="Langkah Selanjutnya",
            value=(
                "1. Tunggu admin respon di tiket ini\n"
                "2. Lakukan pembayaran sesuai instruksi admin\n"
                "3. Admin proses topup setelah pembayaran dikonfirmasi"
            ),
            inline=False,
        )
        info_embed.set_footer(text=f"{STORE_NAME} • Jangan share password di luar tiket")

        ping = admin_role.mention if admin_role else ""
        await channel.send(content=f"{ping} Tiket Vilog baru dibuat.", embed=info_embed)
        await interaction.followup.send(f"Tiket dibuat: {channel.mention}", ephemeral=True)

    @commands.command(name="vilogcatalog")
    async def vilogcatalog_cmd(self, ctx: commands.Context):
        if not any(r.id == ADMIN_ROLE_ID for r in ctx.author.roles):
            return
        try:
            await ctx.message.delete()
        except Exception:
            pass
        await self.refresh_embed(ctx.guild)
        await ctx.send("Catalog Vilog dikirim/diupdate!", delete_after=5)

    @commands.command(name="ratevilog")
    async def ratevilog_cmd(self, ctx: commands.Context, rate: int | None = None):
        if not any(r.id == ADMIN_ROLE_ID for r in ctx.author.roles):
            return
        try:
            await ctx.message.delete()
        except Exception:
            pass
        if rate is None or rate <= 0:
            current = get_vilog_rate()
            if current <= 0:
                await ctx.send("Rate Vilog belum diset. Gunakan `!ratevilog <angka>`.", delete_after=10)
            else:
                await ctx.send(f"Rate Vilog saat ini: **{_format_rp(current)}/Robux**", delete_after=10)
            return
        set_vilog_rate(rate)
        await self.refresh_embed(ctx.guild)
        await ctx.send(f"Rate Vilog diubah ke **{_format_rp(rate)}/Robux** dan catalog diperbarui.", delete_after=5)

    @commands.command(name="vilogdone")
    async def vilogdone_cmd(self, ctx: commands.Context):
        if not any(r.id == ADMIN_ROLE_ID for r in ctx.author.roles):
            return
        try:
            await ctx.message.delete()
        except Exception:
            pass
        channel_id = ctx.channel.id
        if channel_id not in self.active_tickets:
            await ctx.send("Channel ini bukan tiket Vilog aktif.", delete_after=5)
            return
        ticket = self.active_tickets[channel_id]
        member = ctx.guild.get_member(ticket["user_id"])
        now = datetime.datetime.now(datetime.timezone.utc)
        opened_at = datetime.datetime.fromisoformat(ticket["opened_at"])
        durasi_secs = int((now - opened_at).total_seconds())

        from utils.counter import next_ticket_number
        nomor = next_ticket_number()

        # Transcript
        transcript_ch = ctx.guild.get_channel(TRANSCRIPT_CHANNEL_ID)
        if transcript_ch:
            try:
                from utils.transcript import generate as generate_transcript
                transcript_file = await generate_transcript(ctx.channel, STORE_NAME)
                await transcript_ch.send(
                    content=f"Transcript Vilog — {ctx.channel.name}",
                    file=transcript_file,
                )
            except Exception as e:
                print(f"[Vilog] Transcript error: {e}")

        # Log embed
        log_ch = ctx.guild.get_channel(LOG_CHANNEL_ID)
        if log_ch:
            log_embed = discord.Embed(
                title=f"VILOG TOPUP SUKSES — #{nomor:04d}",
                description="Topup Robux via login berhasil diproses.",
                color=COLOR,
                timestamp=now,
            )
            log_embed.add_field(name="Admin", value=f"{ctx.author.mention}\n`{ctx.author.id}`", inline=False)
            log_embed.add_field(name="Member", value=f"{member.mention if member else ticket['user_id']}\n`{ticket['user_id']}`", inline=False)
            log_embed.add_field(name="Robux", value=f"{ticket['boost']['robux']} Robux", inline=True)
            log_embed.add_field(name="Total", value=_format_rp(ticket.get("nominal", 0) or 0), inline=True)
            log_embed.set_footer(text=STORE_NAME)
            await log_ch.send(embed=log_embed)

        try:
            from utils.db import log_transaction
            log_transaction(
                layanan="vilog",
                nominal=ticket.get("nominal", 0) or 0,
                item=f"{ticket['boost']['robux']} Robux via Vilog",
                admin_id=ctx.author.id,
                user_id=ticket.get("user_id"),
                closed_at=now,
                durasi_detik=durasi_secs,
            )
        except Exception as e:
            print(f"[Vilog] Log transaksi error: {e}")

        # Stock Robux (global)
        try:
            record_robux_outgoing(int(ticket.get("boost", {}).get("robux", 0) or 0))
            await self.refresh_embed(ctx.guild)
            robux_cog = self.bot.cogs.get("RobuxStore")
            if robux_cog and hasattr(robux_cog, "refresh_catalog"):
                await robux_cog.refresh_catalog()
            gp_cog = self.bot.cogs.get("GPStore")
            if gp_cog and hasattr(gp_cog, "refresh_catalog"):
                await gp_cog.refresh_catalog()
        except Exception as e:
            print(f"[Stock] Gagal update stock robux (Vilog): {e}")

        try:
            royal_role = discord.utils.get(ctx.guild.roles, name="Royal Customer")
            if royal_role and member and royal_role not in member.roles:
                await member.add_roles(royal_role)
        except Exception:
            pass

        await ctx.channel.send(
            f"✅ Topup Vilog selesai diproses. Terima kasih telah berbelanja di {STORE_NAME}!\n"
            f"Channel akan dihapus dalam 10 detik."
        )
        delete_vilog_ticket(channel_id)
        del self.active_tickets[channel_id]
        await asyncio.sleep(10)
        await ctx.channel.delete()

    @commands.command(name="vilogbatal")
    async def vilogbatal_cmd(self, ctx: commands.Context, *, alasan: str = "Tidak ada alasan diberikan."):
        if not any(r.id == ADMIN_ROLE_ID for r in ctx.author.roles):
            return
        try:
            await ctx.message.delete()
        except Exception:
            pass
        channel_id = ctx.channel.id
        if channel_id not in self.active_tickets:
            await ctx.send("Channel ini bukan tiket Vilog aktif.", delete_after=5)
            return
        await ctx.channel.send(
            f"❌ Tiket Vilog dibatalkan oleh {ctx.author.mention}.\n"
            f"Alasan: {alasan}\n"
            f"Channel akan dihapus dalam 5 detik."
        )
        delete_vilog_ticket(channel_id)
        del self.active_tickets[channel_id]
        await asyncio.sleep(5)
        await ctx.channel.delete()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        channel_id = message.channel.id
        if channel_id not in self.active_tickets:
            return
        # touch last_activity for future use (auto-close/warn, etc.)
        try:
            conn = get_conn()
            conn.execute(
                "UPDATE vilog_tickets SET last_activity=? WHERE channel_id=?",
                (datetime.datetime.now(datetime.timezone.utc).isoformat(), channel_id),
            )
            conn.commit()
            conn.close()
        except Exception:
            pass


async def setup(bot: commands.Bot):
    cog = Vilog(bot)
    await bot.add_cog(cog)
    bot.add_view(VilogCatalogView(cog))
    print("Cog Vilog siap.")
