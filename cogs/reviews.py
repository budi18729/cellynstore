"""Sistem rating & ulasan (review) toko.

Alur:
1. Setiap layanan menutup tiket -> menulis baris ke `transaction_log` (sudah ada).
2. Poller di cog ini mendeteksi transaksi baru (id > last_tx) lalu mengirim
   prompt rating ⭐1-5 ke buyer via DM (fallback ke channel testimoni bila DM tertutup).
3. Buyer klik bintang -> muncul modal ulasan (opsional) -> rating tersimpan.
4. Ulasan diposting ke channel testimoni sebagai embed.
5. Command /rating menampilkan statistik (rata-rata, jumlah, sebaran, ulasan terbaru).

Mengganti cog testimoni lama (auto-reply ucapan terima kasih). Filosofi toko:
rating = garansi, jadi semua transaksi diberi kesempatan rating.
"""

import re

import discord
from discord import app_commands
from discord.ext import commands, tasks

from utils.config import GUILD_ID, STORE_NAME, TESTIMONI_CHANNEL_ID
from utils import reviews as rv

COLOR_REVIEW = 0xFFC107  # kuning/emas
POLL_INTERVAL_SECONDS = 60

# Nama layanan ramah-tampilan untuk embed.
LAYANAN_LABEL = {
    "robux": "Robux",
    "vilog": "Vilog (Boost/Premium)",
    "gp_topup": "Garena/Gameplay Top Up",
    "jualbeli": "Jual Beli",
    "midman": "Middleman",
    "ml": "Mobile Legends",
    "ff": "Free Fire",
    "lainnya": "Layanan Lainnya",
    "cloudphone": "Cloud Phone",
    "nitro": "Discord Nitro",
}


def _pretty_layanan(layanan: str | None) -> str:
    if not layanan:
        return "Order"
    base = layanan.split(":", 1)[0]
    label = LAYANAN_LABEL.get(base, base.replace("_", " ").title())
    # tampilkan sub-grup bila ada (mis. lainnya:editing -> Layanan Lainnya · Editing)
    if ":" in layanan:
        sub = layanan.split(":", 1)[1]
        if sub and sub != "custom":
            label += f" · {sub.title()}"
        elif sub == "custom":
            label += " · Custom"
    return label


def _stars(rating: int) -> str:
    rating = max(0, min(5, int(rating or 0)))
    return "⭐" * rating + "☆" * (5 - rating)


# ── Modal ulasan teks ────────────────────────────────────────────────────────────
class ReviewModal(discord.ui.Modal):
    def __init__(self, review_id: int, rating: int):
        super().__init__(title=f"Ulasan ({rating}/5)", timeout=600)
        self.review_id = review_id
        self.rating = rating
        self.review_text = discord.ui.TextInput(
            label="Ulasan kamu (opsional)",
            placeholder="Ceritakan pengalaman belanjamu... (boleh dikosongkan)",
            style=discord.TextStyle.paragraph,
            required=False,
            max_length=500,
        )
        self.add_item(self.review_text)

    async def on_submit(self, interaction: discord.Interaction):
        text = (self.review_text.value or "").strip() or None
        ok = rv.submit_rating(self.review_id, self.rating, text)
        if not ok:
            await interaction.response.send_message(
                "Rating ini sudah pernah kamu kirim sebelumnya. Terima kasih! 🙏",
                ephemeral=True,
            )
            return
        await interaction.response.send_message(
            f"Makasih banyak! Rating **{self.rating}/5** {_stars(self.rating)} kamu sudah tercatat "
            "dan jadi garansi transaksimu. 💛",
            ephemeral=True,
        )
        cog = interaction.client.cogs.get("Reviews")
        if cog:
            await cog.publish_review(self.review_id)
        # Bersihkan tombol di prompt (kalau bisa diakses).
        try:
            await interaction.message.edit(view=None)
        except Exception:
            pass


# ── Tombol bintang persisten (DynamicItem) ───────────────────────────────────────
class StarButton(
    discord.ui.DynamicItem[discord.ui.Button],
    template=r"review:(?P<rid>\d+):(?P<stars>[1-5])",
):
    """Tombol bintang yang tetap berfungsi setelah bot restart.

    custom_id pola: review:<review_id>:<stars>
    """

    def __init__(self, review_id: int, stars: int):
        self.review_id = review_id
        self.stars = stars
        super().__init__(
            discord.ui.Button(
                label="⭐" * stars,
                style=discord.ButtonStyle.secondary,
                custom_id=f"review:{review_id}:{stars}",
            )
        )

    @classmethod
    async def from_custom_id(cls, interaction, item, match: re.Match):
        return cls(int(match["rid"]), int(match["stars"]))

    async def callback(self, interaction: discord.Interaction):
        review = rv.get_review(self.review_id)
        if not review:
            await interaction.response.send_message(
                "Rating ini sudah tidak tersedia.", ephemeral=True
            )
            return
        if review["status"] != rv.STATUS_PENDING:
            await interaction.response.send_message(
                "Kamu sudah memberi rating untuk transaksi ini. Terima kasih! 🙏",
                ephemeral=True,
            )
            return
        # Hanya pemilik transaksi yang boleh memberi rating.
        if interaction.user.id != review["user_id"]:
            await interaction.response.send_message(
                "Tombol rating ini bukan untuk kamu.", ephemeral=True
            )
            return
        await interaction.response.send_modal(ReviewModal(self.review_id, self.stars))


def build_rating_view(review_id: int) -> discord.ui.View:
    """View berisi 5 tombol bintang untuk sebuah review."""
    view = discord.ui.View(timeout=None)
    for s in (1, 2, 3, 4, 5):
        view.add_item(StarButton(review_id, s))
    return view


def build_prompt_embed(review: dict) -> discord.Embed:
    embed = discord.Embed(
        title="⭐ Beri Rating Transaksimu",
        description=(
            f"Terima kasih sudah berbelanja di **{STORE_NAME}**!\n\n"
            "Beri rating untuk transaksi ini dengan menekan tombol bintang di bawah.\n"
            "**Rating = garansi** transaksimu, jadi jangan lupa ya! 💛"
        ),
        color=COLOR_REVIEW,
    )
    embed.add_field(name="Layanan", value=_pretty_layanan(review.get("layanan")), inline=True)
    if review.get("item"):
        embed.add_field(name="Item", value=str(review["item"])[:256], inline=True)
    if review.get("nominal"):
        embed.add_field(name="Nominal", value=f"Rp {review['nominal']:,}", inline=True)
    embed.set_footer(text=STORE_NAME)
    return embed


def build_published_embed(review: dict, member: discord.abc.User | None) -> discord.Embed:
    name = member.display_name if member else f"User {review['user_id']}"
    embed = discord.Embed(
        title=f"{_stars(review['rating'])}  ({review['rating']}/5)",
        description=review.get("review_text") or "_(tanpa ulasan teks)_",
        color=COLOR_REVIEW,
        timestamp=discord.utils.utcnow(),
    )
    if member:
        embed.set_author(name=name, icon_url=member.display_avatar.url)
    else:
        embed.set_author(name=name)
    embed.add_field(name="Layanan", value=_pretty_layanan(review.get("layanan")), inline=True)
    if review.get("item"):
        embed.add_field(name="Item", value=str(review["item"])[:256], inline=True)
    embed.set_footer(text=f"{STORE_NAME} • Ulasan Member")
    return embed


# ── COG ────────────────────────────────────────────────────────────────────────
class Reviews(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        rv.init_reviews_db()

    async def cog_load(self):
        # Daftarkan handler tombol persisten sekali.
        self.bot.add_dynamic_items(StarButton)
        self.poll_transactions.start()

    def cog_unload(self):
        self.poll_transactions.cancel()

    # ── Poller transaksi baru ─────────────────────
    @tasks.loop(seconds=POLL_INTERVAL_SECONDS)
    async def poll_transactions(self):
        try:
            last = rv.get_last_tx_id()
            new_txs = rv.fetch_new_transactions(last)
            if not new_txs:
                return
            for tx in new_txs:
                try:
                    await self._handle_new_tx(tx)
                except Exception as e:
                    print(f"[Reviews] handle tx {tx.get('id')} error: {e}")
                # Selalu majukan pointer agar tidak mengulang transaksi yang sama.
                rv.set_last_tx_id(tx["id"])
        except Exception as e:
            print(f"[Reviews] poll error: {e}")

    @poll_transactions.before_loop
    async def _before_poll(self):
        await self.bot.wait_until_ready()
        # Pada run pertama (belum ada pointer), mulai dari MAX(id) saat ini supaya
        # transaksi historis tidak dikirimi prompt rating beruntun.
        if rv.get_last_tx_id() == 0:
            rv.set_last_tx_id(rv.current_max_tx_id())

    async def _handle_new_tx(self, tx: dict):
        review_id = rv.create_pending(
            tx_id=tx["id"],
            user_id=tx["user_id"],
            layanan=tx.get("layanan"),
            item=tx.get("item"),
            nominal=tx.get("nominal") or 0,
        )
        if review_id is None:
            return  # sudah pernah diproses (tx_id UNIQUE)

        review = rv.get_review(review_id)
        embed = build_prompt_embed(review)
        view = build_rating_view(review_id)

        user = self.bot.get_user(tx["user_id"])
        if user is None:
            try:
                user = await self.bot.fetch_user(tx["user_id"])
            except Exception:
                user = None

        # Coba DM dulu.
        if user is not None:
            try:
                msg = await user.send(embed=embed, view=view)
                rv.set_prompt_msg_id(review_id, msg.id)
                return
            except discord.Forbidden:
                pass  # DM tertutup -> fallback ke channel
            except Exception as e:
                print(f"[Reviews] DM error user {tx['user_id']}: {e}")

        # Fallback: kirim prompt di channel testimoni dengan mention.
        await self._send_prompt_to_channel(review_id, tx["user_id"], embed, view)

    async def _send_prompt_to_channel(self, review_id, user_id, embed, view):
        if not TESTIMONI_CHANNEL_ID:
            return
        channel = self.bot.get_channel(TESTIMONI_CHANNEL_ID)
        if channel is None:
            return
        try:
            msg = await channel.send(content=f"<@{user_id}>", embed=embed, view=view)
            rv.set_prompt_msg_id(review_id, msg.id)
        except Exception as e:
            print(f"[Reviews] channel prompt error: {e}")

    # ── Publikasi ulasan ──────────────────────────
    async def publish_review(self, review_id: int):
        review = rv.get_review(review_id)
        if not review or review.get("rating") is None:
            return
        if review.get("status") == rv.STATUS_PUBLISHED:
            return
        if not TESTIMONI_CHANNEL_ID:
            return
        channel = self.bot.get_channel(TESTIMONI_CHANNEL_ID)
        if channel is None:
            return

        member = None
        guild = self.bot.get_guild(GUILD_ID)
        if guild:
            member = guild.get_member(review["user_id"])
        if member is None:
            member = self.bot.get_user(review["user_id"])

        embed = build_published_embed(review, member)
        try:
            msg = await channel.send(embed=embed)
            rv.set_published(review_id, msg.id)
        except Exception as e:
            print(f"[Reviews] publish error: {e}")

    # ── Command statistik ─────────────────────────
    @app_commands.command(name="rating", description="Lihat statistik rating & ulasan toko.")
    @app_commands.describe(layanan="Filter layanan (mis. robux, vilog, lainnya). Kosongkan untuk semua.")
    async def rating(self, interaction: discord.Interaction, layanan: str = None):
        stats = rv.get_stats(layanan)
        scope = _pretty_layanan(layanan) if layanan else "Semua Layanan"
        if stats["count"] == 0:
            await interaction.response.send_message(
                f"Belum ada rating untuk **{scope}**.", ephemeral=True
            )
            return

        dist = stats["distribution"]
        total = stats["count"]
        dist_lines = []
        for s in (5, 4, 3, 2, 1):
            cnt = dist.get(s, 0)
            bar_len = round((cnt / total) * 10) if total else 0
            bar = "█" * bar_len + "░" * (10 - bar_len)
            dist_lines.append(f"`{s}★` {bar} {cnt}")

        embed = discord.Embed(
            title=f"📊 Rating — {scope}",
            description=(
                f"**{_stars(round(stats['average']))}**  "
                f"**{stats['average']:.2f}/5**  ·  {total} ulasan"
            ),
            color=COLOR_REVIEW,
        )
        embed.add_field(name="Sebaran", value="\n".join(dist_lines), inline=False)

        recent = rv.get_recent_reviews(limit=3, layanan=layanan)
        if recent:
            lines = []
            for r in recent:
                txt = (r.get("review_text") or "").strip()
                txt = (txt[:80] + "…") if len(txt) > 80 else txt
                lines.append(f"{_stars(r['rating'])} — {txt or '_(tanpa ulasan)_'}")
            embed.add_field(name="Ulasan Terbaru", value="\n".join(lines)[:1024], inline=False)
        embed.set_footer(text=STORE_NAME)
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Reviews(bot))
    print("Cog Reviews siap.")
