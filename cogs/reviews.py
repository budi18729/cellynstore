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
import datetime

import discord
from discord import app_commands
from discord.ext import commands, tasks

from utils.config import (
    GUILD_ID, STORE_NAME, TESTIMONI_CHANNEL_ID,
    REVIEWER_BADGE_ROLE_ID, REVIEWER_BADGE_THRESHOLD,
    ROBUX_CATALOG_CHANNEL_ID, ML_CATALOG_CHANNEL_ID,
    VILOG_CATALOG_CHANNEL_ID, MIDMAN_CHANNEL_ID,
)
from utils import reviews as rv

COLOR_REVIEW = 0xFFC107  # kuning/emas
POLL_INTERVAL_SECONDS = 60

# Role member loyal (didapat otomatis dari transaksi). Dipakai gating /riwayat.
# Konsisten dengan cog lain yang assign role by-name saat transaksi selesai.
ROYAL_CUSTOMER_ROLE_NAME = "Royal Customer"

# Channel katalog per layanan (untuk tombol "Order Lagi" di prompt rating).
# gp & lainnya pakai channel hardcoded (sesuai cog masing-masing).
GP_CATALOG_CHANNEL_ID = 1478917118715236603
LAINNYA_CATALOG_CHANNEL_ID = 1476349829113315489

ORDER_AGAIN = {
    "robux": (ROBUX_CATALOG_CHANNEL_ID, "🛒 Order Robux Lagi"),
    "vilog": (VILOG_CATALOG_CHANNEL_ID, "🛒 Order Robux Via Login Lagi"),
    "ml": (ML_CATALOG_CHANNEL_ID, "🛒 Order Mobile Legends Lagi"),
    "ff": (ML_CATALOG_CHANNEL_ID, "🛒 Order Free Fire Lagi"),
    "gp": (GP_CATALOG_CHANNEL_ID, "🛒 Order Robux Gamepass Lagi"),
    "lainnya": (LAINNYA_CATALOG_CHANNEL_ID, "🛒 Order Layanan Lainnya Lagi"),
    "jualbeli": (MIDMAN_CHANNEL_ID, "🛒 Jual Beli Lagi"),
    "midman": (MIDMAN_CHANNEL_ID, "🛒 Middleman Lagi"),
}


def _order_again_button(layanan: str | None) -> discord.ui.Button | None:
    """Tombol link 'Order Lagi' yang mengarah ke channel katalog layanan terkait.

    Memetakan layanan transaksi (mis. 'vilog', 'lainnya:editing') -> channel +
    label. Mengembalikan None bila layanan/channel tidak diketahui.
    """
    if not layanan:
        return None
    base = layanan.split(":", 1)[0].lower()
    entry = ORDER_AGAIN.get(base)
    if not entry:
        return None
    channel_id, label = entry
    if not channel_id:
        return None
    url = f"https://discord.com/channels/{GUILD_ID}/{channel_id}"
    return discord.ui.Button(label=label, style=discord.ButtonStyle.link, url=url)

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


def _warranty_emoji(review_status: str | None) -> str:
    """Emoji status garansi untuk baris riwayat."""
    if review_status in (rv.STATUS_RATED, rv.STATUS_PUBLISHED):
        return "🟢"  # sudah rating -> garansi aktif
    if review_status == rv.STATUS_PENDING:
        return "🟡"  # menunggu rating
    if review_status == rv.STATUS_EXPIRED:
        return "🔴"  # lewat 24 jam -> garansi hangus
    return "⚪"      # tidak ada data review


def _warranty_label(review_status: str | None) -> str:
    """Label status garansi yang mudah dibaca member."""
    if review_status in (rv.STATUS_RATED, rv.STATUS_PUBLISHED):
        return "garansi aktif (sudah rating)"
    if review_status == rv.STATUS_PENDING:
        return "belum rating (segera, batas 24 jam)"
    if review_status == rv.STATUS_EXPIRED:
        return "garansi hangus (tidak rating dalam 24 jam)"
    return "tanpa garansi"


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
        if self.rating == 5:
            # Auto-thank spesial untuk rating sempurna.
            await interaction.response.send_message(
                f"🎉✨ WAH, RATING SEMPURNA {_stars(5)}! ✨🎉\n"
                f"Makasih banyak udah kasih **5/5** — kamu the best! 💛\n"
                f"Garansi transaksimu **aktif**, dan ditunggu next order-nya di {STORE_NAME}! 🛍️",
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                f"Makasih banyak! Rating **{self.rating}/5** {_stars(self.rating)} kamu sudah tercatat "
                "dan jadi garansi transaksimu. 💛",
                ephemeral=True,
            )
        cog = interaction.client.cogs.get("Reviews")
        if cog:
            await cog.update_success_log(self.review_id)
            await cog.publish_review(self.review_id)
            await cog.maybe_award_badge(interaction.user)
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
        if review["status"] == rv.STATUS_EXPIRED:
            await interaction.response.send_message(
                f"Maaf, batas waktu **{rv.RATING_DEADLINE_HOURS} jam** sudah lewat, "
                "jadi rating untuk transaksi ini sudah ditutup dan garansi tidak berlaku. 🙏",
                ephemeral=True,
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


def build_rating_view(review_id: int, layanan: str = None) -> discord.ui.View:
    """View berisi 5 tombol bintang + tombol 'Order Lagi' (link) untuk sebuah review."""
    view = discord.ui.View(timeout=None)
    for s in (1, 2, 3, 4, 5):
        view.add_item(StarButton(review_id, s))
    btn = _order_again_button(layanan)
    if btn is not None:
        view.add_item(btn)
    return view


def build_prompt_embed(review: dict, avatar_url: str = None) -> discord.Embed:
    deadline_txt = ""
    if review.get("deadline_at"):
        try:
            dl = datetime.datetime.fromisoformat(review["deadline_at"])
            # Tampilkan sebagai timestamp Discord relatif (mis. "in 24 hours") + absolut.
            ts = int(dl.timestamp())
            deadline_txt = f"\n\n⏳ **Batas waktu: <t:{ts}:R>** (<t:{ts}:f>)"
        except Exception:
            deadline_txt = ""

    embed = discord.Embed(
        title="⭐ Beri Rating Transaksimu",
        description=(
            f"Terima kasih sudah berbelanja di **{STORE_NAME}**!\n\n"
            "Beri rating untuk transaksi ini dengan menekan tombol bintang di bawah.\n\n"
            f"⚠️ **PENTING: Rating = Garansi.**\n"
            f"Kamu wajib memberi rating dalam **{rv.RATING_DEADLINE_HOURS} jam**. "
            f"**Tanpa rating sebelum batas waktu, transaksimu TIDAK mendapat garansi.** "
            f"Mohon beri rating sesegera mungkin ya! 💛"
            f"{deadline_txt}"
        ),
        color=COLOR_REVIEW,
    )
    if avatar_url:
        embed.set_thumbnail(url=avatar_url)
    embed.add_field(name="Layanan", value=_pretty_layanan(review.get("layanan")), inline=True)
    if review.get("item"):
        embed.add_field(name="Item", value=str(review["item"])[:256], inline=True)
    if review.get("nominal"):
        embed.add_field(name="Nominal", value=f"Rp {review['nominal']:,}", inline=True)
    embed.set_footer(text=f"{STORE_NAME} • Tanpa rating = tanpa garansi")
    return embed


def build_expired_embed(review: dict) -> discord.Embed:
    """Embed pemberitahuan saat 24 jam lewat tanpa rating (garansi hangus)."""
    embed = discord.Embed(
        title="⌛ Waktu Rating Habis — Garansi Hangus",
        description=(
            f"Batas waktu **{rv.RATING_DEADLINE_HOURS} jam** untuk memberi rating sudah lewat, "
            f"sehingga transaksi ini **tidak mendapat garansi**.\n\n"
            f"Lain kali jangan lupa beri rating segera setelah transaksi ya, agar garansimu aktif. 🙏"
        ),
        color=0xED4245,  # merah
    )
    embed.add_field(name="Layanan", value=_pretty_layanan(review.get("layanan")), inline=True)
    if review.get("item"):
        embed.add_field(name="Item", value=str(review["item"])[:256], inline=True)
    embed.set_footer(text=f"{STORE_NAME} • Tanpa rating = tanpa garansi")
    return embed


def build_published_embed(review: dict, member: discord.abc.User | None) -> discord.Embed:
    """Embed ulasan yang diposting ke channel rating setelah member memberi rating.

    Format: title = nama member (thumbnail = foto profilnya), lalu bintang,
    ulasan, produk, tanggal, dan baris terima kasih.
    """
    name = member.display_name if member else f"User {review['user_id']}"
    rating = int(review.get("rating") or 0)

    ulasan = (review.get("review_text") or "").strip()
    ulasan_line = f'Ulasan: "{ulasan}"' if ulasan else "Ulasan: -"

    # Tanggal DD/MM/YY dari rated_at (fallback hari ini).
    tgl = datetime.datetime.now(datetime.timezone.utc)
    if review.get("rated_at"):
        try:
            tgl = datetime.datetime.fromisoformat(review["rated_at"])
        except Exception:
            pass
    tgl_str = tgl.strftime("%d/%m/%y")

    product = review.get("item") or _pretty_layanan(review.get("layanan"))

    desc = (
        f"{_stars(rating)} ({rating}/5)\n"
        f"{ulasan_line}\n"
        f"Product: {product}\n"
        f"{tgl_str}\n"
        f"**Rating & ulasan diterima, Terimakasih**"
    )
    embed = discord.Embed(
        title=name,
        description=desc,
        color=COLOR_REVIEW,
        timestamp=discord.utils.utcnow(),
    )
    if member:
        embed.set_thumbnail(url=member.display_avatar.url)
    embed.set_footer(text=STORE_NAME)
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
        self.expire_pending.start()
        self.remind_pending.start()

    def cog_unload(self):
        self.poll_transactions.cancel()
        self.expire_pending.cancel()
        self.remind_pending.cancel()

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

    # ── Poller kedaluwarsa 24 jam ─────────────────
    @tasks.loop(minutes=10)
    async def expire_pending(self):
        try:
            overdue = rv.fetch_expired_pending()
            for review in overdue:
                if rv.mark_expired(review["id"]):
                    await self._notify_expired(review)
        except Exception as e:
            print(f"[Reviews] expire loop error: {e}")

    @expire_pending.before_loop
    async def _before_expire(self):
        await self.bot.wait_until_ready()

    # ── Poller pengingat rating (sebelum deadline) ─
    @tasks.loop(minutes=30)
    async def remind_pending(self):
        try:
            due = rv.fetch_due_for_reminder()
            for review in due:
                if rv.mark_reminded(review["id"]):
                    await self._send_reminder(review)
        except Exception as e:
            print(f"[Reviews] reminder loop error: {e}")

    @remind_pending.before_loop
    async def _before_remind(self):
        await self.bot.wait_until_ready()

    async def _send_reminder(self, review: dict):
        """Kirim pengingat agar member rating sebelum garansi hangus."""
        deadline_txt = ""
        if review.get("deadline_at"):
            try:
                ts = int(datetime.datetime.fromisoformat(review["deadline_at"]).timestamp())
                deadline_txt = f"\n\n⏳ **Sisa waktu: <t:{ts}:R>** — setelah itu garansi hangus."
            except Exception:
                deadline_txt = ""
        embed = discord.Embed(
            title="⏰ Jangan Lupa Beri Rating!",
            description=(
                f"Transaksimu di **{STORE_NAME}** belum kamu beri rating.\n"
                f"**Rating = Garansi.** Beri rating sekarang agar garansimu aktif "
                f"sebelum batas waktu habis. 💛{deadline_txt}"
            ),
            color=COLOR_REVIEW,
        )
        if review.get("item"):
            embed.add_field(name="Item", value=str(review["item"])[:256], inline=True)
        embed.set_footer(text=f"{STORE_NAME} • Tanpa rating = tanpa garansi")

        view = build_rating_view(review["id"], layanan=review.get("layanan"))
        user = self.bot.get_user(review["user_id"])
        if user is None:
            try:
                user = await self.bot.fetch_user(review["user_id"])
            except Exception:
                user = None
        if user is not None:
            try:
                await user.send(embed=embed, view=view)
                return
            except discord.Forbidden:
                pass
            except Exception as e:
                print(f"[Reviews] reminder DM error {review['user_id']}: {e}")
        # Fallback ke channel testimoni.
        if TESTIMONI_CHANNEL_ID:
            channel = self.bot.get_channel(TESTIMONI_CHANNEL_ID)
            if channel is not None:
                try:
                    await channel.send(content=f"<@{review['user_id']}>", embed=embed, view=view)
                except Exception as e:
                    print(f"[Reviews] reminder channel error: {e}")

    async def _notify_expired(self, review: dict):
        """Beri tahu buyer bahwa waktu rating habis & garansi hangus."""
        embed = build_expired_embed(review)
        user = self.bot.get_user(review["user_id"])
        if user is None:
            try:
                user = await self.bot.fetch_user(review["user_id"])
            except Exception:
                user = None
        # Coba bersihkan tombol pada prompt lama (best-effort, hanya untuk DM).
        if user is not None:
            try:
                await user.send(embed=embed)
                return
            except discord.Forbidden:
                pass
            except Exception as e:
                print(f"[Reviews] notify expired DM error {review['user_id']}: {e}")
        # Fallback ke channel testimoni.
        if TESTIMONI_CHANNEL_ID:
            channel = self.bot.get_channel(TESTIMONI_CHANNEL_ID)
            if channel is not None:
                try:
                    await channel.send(content=f"<@{review['user_id']}>", embed=embed)
                except Exception as e:
                    print(f"[Reviews] notify expired channel error: {e}")

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

        user = self.bot.get_user(tx["user_id"])
        if user is None:
            try:
                user = await self.bot.fetch_user(tx["user_id"])
            except Exception:
                user = None

        embed = build_prompt_embed(review, avatar_url=(user.display_avatar.url if user else None))
        view = build_rating_view(review_id, layanan=tx.get("layanan"))

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

    # ── Update pesan log transaksi setelah rating ──
    async def update_success_log(self, review_id: int):
        """Edit pesan log 'transaksi berhasil' agar status garansi jadi 'Aktif'.

        Mencari pesan via transaction_log (tx_id -> log_channel_id/log_message_id),
        lalu merender ulang teks flat dengan rating yang baru.
        """
        try:
            from utils.db import get_transaction
            from utils import ticket_ui

            review = rv.get_review(review_id)
            if not review or not review.get("tx_id") or review.get("rating") is None:
                return
            tx = get_transaction(review["tx_id"])
            if not tx or not tx.get("log_channel_id") or not tx.get("log_message_id"):
                return

            channel = self.bot.get_channel(tx["log_channel_id"])
            if channel is None:
                return
            try:
                msg = await channel.fetch_message(tx["log_message_id"])
            except Exception:
                return

            seller = f"<@{tx['admin_id']}>" if tx.get("admin_id") else "Admin"
            buyer = f"<@{tx['user_id']}>" if tx.get("user_id") else "-"
            new_text = ticket_ui.success_log_text(
                seller=seller,
                buyer=buyer,
                product=tx.get("item") or "-",
                qty=tx.get("qty") or 1,
                harga=tx.get("nominal") or 0,
                rating=review["rating"],
                rating_channel_id=TESTIMONI_CHANNEL_ID,
            )
            await msg.edit(content=new_text)
        except Exception as e:
            print(f"[Reviews] update success log error: {e}")

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

    # ── Badge reviewer ────────────────────────────
    async def maybe_award_badge(self, user):
        """Beri role badge reviewer bila member mencapai ambang jumlah rating."""
        if not REVIEWER_BADGE_ROLE_ID:
            return
        try:
            total = rv.count_user_reviews(user.id)
            if total < REVIEWER_BADGE_THRESHOLD:
                return
            guild = self.bot.get_guild(GUILD_ID)
            if guild is None:
                return
            member = guild.get_member(user.id)
            role = guild.get_role(REVIEWER_BADGE_ROLE_ID)
            if member is None or role is None or role in member.roles:
                return
            await member.add_roles(role, reason="Reviewer aktif (badge)")
        except Exception as e:
            print(f"[Reviews] award badge error: {e}")

    # ── Command leaderboard reviewer ──────────────
    @app_commands.command(name="topreviewer", description="Lihat member paling rajin memberi rating.")
    async def topreviewer(self, interaction: discord.Interaction):
        top = rv.get_top_reviewers(limit=10)
        if not top:
            await interaction.response.send_message(
                "Belum ada yang memberi rating.", ephemeral=True
            )
            return
        medals = {0: "🥇", 1: "🥈", 2: "🥉"}
        lines = []
        for i, r in enumerate(top):
            prefix = medals.get(i, f"`#{i+1}`")
            lines.append(
                f"{prefix} <@{r['user_id']}> — **{r['count']}** ulasan "
                f"(rata-rata {r['avg_rating']:.1f}⭐)"
            )
        embed = discord.Embed(
            title="🏆 Top Reviewer",
            description="\n".join(lines),
            color=COLOR_REVIEW,
        )
        if REVIEWER_BADGE_ROLE_ID:
            embed.set_footer(
                text=f"{STORE_NAME} • Beri {REVIEWER_BADGE_THRESHOLD}+ rating untuk dapat badge reviewer!"
            )
        else:
            embed.set_footer(text=STORE_NAME)
        await interaction.response.send_message(embed=embed)

    # ── Riwayat order member (khusus Royal Customer) ──
    @app_commands.command(name="riwayat", description="Lihat riwayat transaksimu (khusus Royal Customer).")
    async def riwayat(self, interaction: discord.Interaction):
        # Gating: hanya member dengan role "Royal Customer" (didapat dari transaksi).
        member = interaction.user
        roles = getattr(member, "roles", [])
        has_royal = any(getattr(r, "name", "") == ROYAL_CUSTOMER_ROLE_NAME for r in roles)
        if not has_royal:
            await interaction.response.send_message(
                f"Fitur **/riwayat** khusus member **{ROYAL_CUSTOMER_ROLE_NAME}**.\n"
                "Role ini otomatis kamu dapatkan setelah melakukan transaksi di Cellyn Store. 💛",
                ephemeral=True,
            )
            return

        txs = rv.get_user_transactions(member.id, limit=15)
        total = rv.count_user_transactions(member.id)
        if not txs:
            await interaction.response.send_message(
                "Belum ada riwayat transaksi atas akunmu.", ephemeral=True
            )
            return

        lines = []
        for t in txs:
            when = (t.get("closed_at") or "")[:10]
            lay = _pretty_layanan(t.get("layanan"))
            item = (t.get("item") or "-")
            nominal = t.get("nominal") or 0
            lines.append(
                f"{_warranty_emoji(t.get('review_status'))} `{when}` · **{lay}**\n"
                f"   {item} — Rp {nominal:,} · {_warranty_label(t.get('review_status'))}"
            )

        embed = discord.Embed(
            title="🧾 Riwayat Transaksimu",
            description="\n".join(lines)[:4000],
            color=COLOR_REVIEW,
        )
        embed.add_field(name="Total Transaksi", value=str(total), inline=True)
        embed.set_footer(text=f"{STORE_NAME} • menampilkan {len(txs)} terbaru")
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Reviews(bot))
    print("Cog Reviews siap.")
