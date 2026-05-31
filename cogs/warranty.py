"""Sistem klaim garansi (#6).

Filosofi toko: "rating = garansi". Member hanya berhak garansi bila sudah
memberi rating untuk transaksinya (dalam batas 24 jam). Verifikasi otomatis
dari tabel `reviews` (status 'rated'/'published').

Alur:
1. Admin pasang panel (tombol) di channel khusus via `!garansi`.
2. Member klik "Klaim Garansi".
3. Bot cek `rv.has_valid_warranty(user_id)`:
   - Tidak berhak -> tolak halus (ephemeral), jelaskan alasannya.
   - Berhak -> buat tiket klaim (channel privat), tag admin, tampilkan
     transaksi yang bergaransi.
4. Admin proses klaim di tiket; `!garansiclose` untuk menutup.
"""
import datetime

import discord
from discord.ext import commands

from utils.config import (
    ADMIN_ROLE_ID, STORE_NAME, TICKET_CATEGORY_ID, WARRANTY_CHANNEL_ID,
)
from utils.counter import next_ticket_number
from utils import reviews as rv
from utils import ticket_ui

THUMBNAIL = "https://i.imgur.com/CX8PHWk.png"
COLOR_WARRANTY = 0x2ECC71
CLAIM_BUTTON_ID = "warranty_claim_open"


def build_panel_embed() -> discord.Embed:
    embed = discord.Embed(
        title="Klaim Garansi",
        description=(
            f"Punya kendala dengan pesananmu di {STORE_NAME}?\n"
            "Klik tombol di bawah untuk membuka tiket klaim garansi.\n\n"
            "**Syarat garansi:** kamu sudah memberi **rating** untuk transaksi "
            "tersebut (dalam batas 24 jam setelah transaksi).\n"
            "Tanpa rating, garansi tidak berlaku."
        ),
        color=COLOR_WARRANTY,
    )
    embed.set_thumbnail(url=THUMBNAIL)
    embed.set_footer(text=STORE_NAME)
    return embed


class WarrantyPanelView(discord.ui.View):
    """View persisten berisi tombol klaim garansi."""

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Klaim Garansi",
        style=discord.ButtonStyle.success,
        emoji="🛡️",
        custom_id=CLAIM_BUTTON_ID,
    )
    async def claim(self, interaction: discord.Interaction, button: discord.ui.Button):
        cog = interaction.client.cogs.get("Warranty")
        if cog is None:
            await interaction.response.send_message(
                "Sistem garansi sedang tidak tersedia.", ephemeral=True
            )
            return
        await cog.handle_claim(interaction)


class Warranty(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self):
        rv.init_reviews_db()

    # ── Inti: proses klaim dari tombol ────────────
    async def handle_claim(self, interaction: discord.Interaction):
        member = interaction.user
        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message(
                "Klaim hanya bisa dari dalam server.", ephemeral=True
            )
            return

        # Verifikasi kelayakan garansi (rating = garansi).
        if not rv.has_valid_warranty(member.id):
            await interaction.response.send_message(
                "Maaf, kamu belum memenuhi syarat garansi.\n"
                "Garansi hanya berlaku untuk transaksi yang **sudah kamu beri rating** "
                "dalam batas **24 jam** setelah transaksi. 🙏",
                ephemeral=True,
            )
            return

        # Cegah tiket klaim ganda untuk member yang sama.
        existing = self._find_existing_claim(guild, member.id)
        if existing is not None:
            await interaction.response.send_message(
                f"Kamu masih punya tiket klaim aktif: {existing.mention}", ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)
        channel = await self._create_claim_ticket(guild, member)
        if channel is None:
            await interaction.followup.send(
                "Gagal membuat tiket klaim. Hubungi admin.", ephemeral=True
            )
            return
        await interaction.followup.send(
            f"Tiket klaim garansimu sudah dibuat: {channel.mention}", ephemeral=True
        )

    def _find_existing_claim(self, guild: discord.Guild, user_id: int):
        """Cari channel klaim aktif milik member (berdasarkan topic penanda)."""
        marker = f"warranty:{user_id}"
        category = guild.get_channel(TICKET_CATEGORY_ID)
        channels = category.text_channels if isinstance(category, discord.CategoryChannel) else guild.text_channels
        for ch in channels:
            if (ch.topic or "") == marker:
                return ch
        return None

    async def _create_claim_ticket(self, guild: discord.Guild, member: discord.Member):
        category = guild.get_channel(TICKET_CATEGORY_ID)
        admin_role = guild.get_role(ADMIN_ROLE_ID)
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            member: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        }
        if admin_role:
            overwrites[admin_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        ticket_number = next_ticket_number()
        try:
            channel = await guild.create_text_channel(
                name=ticket_ui.channel_name("garansi", ticket_number, member.name),
                category=category if isinstance(category, discord.CategoryChannel) else None,
                overwrites=overwrites,
                topic=f"warranty:{member.id}",
            )
        except Exception as e:
            print(f"[Warranty] create channel error: {e}")
            return None

        # Daftar transaksi yang bergaransi (sudah dirating) + sisa masa garansi.
        from utils.config import WARRANTY_DEFAULT_DAYS
        from utils import subscription as sub

        txs = rv.get_warranty_transactions(member.id)
        active_items = []  # produk yang garansinya masih aktif (untuk template klaim)
        if txs:
            lines = []
            for t in txs[:10]:
                when = (t.get("rated_at") or "")[:10]
                item = t.get("item") or "-"
                nominal = t.get("nominal") or 0
                stars = "⭐" * int(t.get("rating") or 0)
                # Sisa masa garansi dihitung dari closed_at + durasi langganan
                # (atau WARRANTY_DEFAULT_DAYS untuk produk non-langganan).
                start = t.get("closed_at") or t.get("rated_at")
                sisa = sub.days_remaining(start, item, default_days=WARRANTY_DEFAULT_DAYS)
                if sisa is None:
                    status = "♾️ tanpa batas"
                elif sisa > 0:
                    status = f"🟢 garansi {sisa} hari lagi"
                    active_items.append(item)
                else:
                    status = "🔴 garansi habis"
                lines.append(f"• `{when}` **{item}** — Rp {nominal:,} · {stars}\n  └ {status}")
            tx_text = "\n".join(lines)
            if len(txs) > 10:
                tx_text += f"\n… dan {len(txs) - 10} transaksi lain."
        else:
            tx_text = "_(tidak ada detail transaksi)_"

        # Template klaim yang sudah terisi (memudahkan member & admin).
        if active_items:
            produk_aktif = ", ".join(dict.fromkeys(active_items))  # unik, jaga urutan
            claim_template = (
                "Silakan lengkapi klaimmu:\n"
                f"```\nProduk      : {produk_aktif[:300]}\n"
                "Kendala     : (jelaskan masalahnya di sini)\n"
                "Bukti       : (lampirkan screenshot/video bila ada)\n```"
            )
        else:
            claim_template = (
                "Silakan lengkapi klaimmu:\n"
                "```\nProduk      : (nama produk)\n"
                "Kendala     : (jelaskan masalahnya di sini)\n"
                "Bukti       : (lampirkan screenshot/video bila ada)\n```"
            )

        embed = discord.Embed(
            title=f"TIKET KLAIM GARANSI · #{ticket_ui.format_number(ticket_number)}",
            description=(
                "Garansi terverifikasi (kamu sudah memberi rating). ✅\n"
                "Jelaskan kendala pesananmu di bawah ini. Admin akan segera membantu."
            ),
            color=COLOR_WARRANTY,
            timestamp=datetime.datetime.now(datetime.timezone.utc),
        )
        embed.add_field(name="Member", value=member.mention, inline=True)
        embed.add_field(name="Tiket", value=f"#{ticket_ui.format_number(ticket_number)}", inline=True)
        embed.add_field(name="Transaksi Bergaransi", value=tx_text[:1024], inline=False)
        embed.add_field(name="Form Klaim", value=claim_template[:1024], inline=False)
        embed.add_field(
            name="Admin",
            value="Gunakan `!garansiclose` untuk menutup tiket setelah selesai.",
            inline=False,
        )
        embed.set_footer(text=STORE_NAME)

        admin_mention = admin_role.mention if admin_role else ""
        await channel.send(content=f"{member.mention} {admin_mention}".strip(), embed=embed)
        return channel

    # ── Command admin: pasang panel ───────────────
    @commands.command(name="garansi")
    async def garansi_panel(self, ctx: commands.Context):
        if not any(r.id == ADMIN_ROLE_ID for r in ctx.author.roles):
            return
        try:
            await ctx.message.delete()
        except Exception:
            pass

        target = None
        if WARRANTY_CHANNEL_ID:
            target = ctx.guild.get_channel(WARRANTY_CHANNEL_ID)
        target = target or ctx.channel

        # Bersihkan panel lama milik bot di channel target.
        try:
            async for msg in target.history(limit=30):
                if msg.author == self.bot.user and msg.embeds:
                    await msg.delete()
        except Exception:
            pass

        await target.send(embed=build_panel_embed(), view=WarrantyPanelView())
        await ctx.send(f"Panel garansi dikirim ke {target.mention}", delete_after=5)

    # ── Command admin: tutup tiket klaim ──────────
    @commands.command(name="garansiclose")
    async def garansi_close(self, ctx: commands.Context):
        if not any(r.id == ADMIN_ROLE_ID for r in ctx.author.roles):
            return
        topic = ctx.channel.topic or ""
        if not topic.startswith("warranty:"):
            await ctx.send("Ini bukan channel tiket klaim garansi.", delete_after=5)
            return
        await ctx.send("Tiket klaim garansi ditutup. Channel dihapus dalam 5 detik...")
        import asyncio
        await asyncio.sleep(5)
        try:
            await ctx.channel.delete()
        except Exception as e:
            print(f"[Warranty] close error: {e}")


async def setup(bot: commands.Bot):
    await bot.add_cog(Warranty(bot))
    bot.add_view(WarrantyPanelView())
    print("Cog Warranty siap.")
