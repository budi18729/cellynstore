"""Insight pelanggan untuk admin: ringkasan riwayat saat tiket dibuka.

Saat seorang member membuka tiket, bot mengirim embed ringkas ke channel
ADMIN (bukan ke channel tiket, supaya data belanja tidak terlihat member):
jumlah order, total belanja, rata-rata rating, order terakhir, layanan favorit.
Admin langsung tahu sedang melayani pelanggan baru atau langganan setia.

Bagian data (`get_customer_stats`) & pembentuk embed (`build_insight_embed`)
murni/testable. `send_insight` adalah helper async yang dipanggil tiap cog tiket.
"""

import discord

from utils.db import get_conn
from utils.config import STORE_NAME

COLOR_INSIGHT = 0x5865F2


def get_customer_stats(user_id: int) -> dict:
    """Ringkas riwayat transaksi seorang member dari transaction_log + reviews.

    Return {
      'orders', 'total_spend', 'last_item', 'last_at', 'first_at',
      'rating_count', 'rating_avg', 'top_layanan'
    }. Semua aman bila member belum punya transaksi (nilai 0/None).
    """
    conn = get_conn()
    c = conn.cursor()

    c.execute(
        """
        SELECT COUNT(*) AS orders, COALESCE(SUM(nominal), 0) AS total_spend,
               MIN(closed_at) AS first_at, MAX(closed_at) AS last_at
        FROM transaction_log WHERE user_id = ?
        """,
        (user_id,),
    )
    row = c.fetchone()
    orders = row["orders"] or 0
    total_spend = row["total_spend"] or 0
    first_at = row["first_at"]
    last_at = row["last_at"]

    last_item = None
    if orders:
        c.execute(
            "SELECT item FROM transaction_log WHERE user_id = ? ORDER BY id DESC LIMIT 1",
            (user_id,),
        )
        r = c.fetchone()
        last_item = r["item"] if r else None

    # Layanan paling sering dibeli.
    top_layanan = None
    c.execute(
        """
        SELECT layanan, COUNT(*) AS n FROM transaction_log
        WHERE user_id = ? GROUP BY layanan ORDER BY n DESC LIMIT 1
        """,
        (user_id,),
    )
    r = c.fetchone()
    if r:
        top_layanan = r["layanan"]

    # Rata-rata rating yang pernah ia berikan. Tabel reviews mungkin belum
    # dibuat (init_reviews_db dipanggil oleh cog reviews/warranty saat load).
    rating_count = 0
    rating_avg = 0.0
    try:
        c.execute(
            "SELECT COUNT(*) AS n, AVG(rating) AS avg FROM reviews WHERE user_id = ? AND rating IS NOT NULL",
            (user_id,),
        )
        r = c.fetchone()
        rating_count = r["n"] or 0
        rating_avg = round(r["avg"], 2) if r["avg"] is not None else 0.0
    except Exception:
        pass

    conn.close()
    return {
        "orders": orders,
        "total_spend": total_spend,
        "last_item": last_item,
        "last_at": last_at,
        "first_at": first_at,
        "rating_count": rating_count,
        "rating_avg": rating_avg,
        "top_layanan": top_layanan,
    }


def _fmt_rupiah(n) -> str:
    try:
        return f"Rp {int(n):,}".replace(",", ".")
    except (TypeError, ValueError):
        return f"Rp {n}"


def _pretty_layanan(layanan: str) -> str:
    if not layanan:
        return "-"
    mapping = {
        "robux": "Robux Store", "gp": "Robux Gamepass", "ml": "Topup Game",
        "ff": "Topup Game", "vilog": "Boost via Login", "jualbeli": "Jual Beli",
        "midman": "Midman Trade",
    }
    base = layanan.split(":")[0]
    return mapping.get(base, layanan.replace(":", " · ").title())


def build_insight_embed(stats: dict, member_name: str, avatar_url: str = None,
                        ticket_mention: str = None) -> discord.Embed:
    """Bangun embed insight pelanggan (admin-facing). Murni, gampang dites."""
    orders = stats.get("orders", 0)

    if orders <= 0:
        embed = discord.Embed(
            title="🆕 Pelanggan Baru",
            description=f"**{member_name}** membuka tiket — belum ada riwayat transaksi.",
            color=COLOR_INSIGHT,
        )
        if ticket_mention:
            embed.add_field(name="Tiket", value=ticket_mention, inline=True)
        if avatar_url:
            embed.set_thumbnail(url=avatar_url)
        embed.set_footer(text=f"{STORE_NAME} · insight pelanggan")
        return embed

    # Sapaan dinamis berdasarkan loyalitas.
    if orders >= 10:
        tag = "👑 Pelanggan Setia"
    elif orders >= 3:
        tag = "🔁 Pelanggan Berulang"
    else:
        tag = "🙂 Sudah Pernah Order"

    embed = discord.Embed(
        title=f"{tag} — {member_name}",
        description=f"Order ke-**{orders + 1}** sedang dibuka. Layani dengan baik! 🤝",
        color=COLOR_INSIGHT,
    )
    embed.add_field(name="Total Order", value=f"{orders}x", inline=True)
    embed.add_field(name="Total Belanja", value=_fmt_rupiah(stats.get("total_spend", 0)), inline=True)

    if stats.get("rating_count"):
        avg = stats["rating_avg"]
        stars = "⭐" * max(0, min(5, int(round(avg))))
        embed.add_field(name="Rating Diberikan", value=f"{stars} {avg:.2f} ({stats['rating_count']}x)", inline=True)

    if stats.get("top_layanan"):
        embed.add_field(name="Paling Sering", value=_pretty_layanan(stats["top_layanan"]), inline=True)

    if stats.get("last_item"):
        last_at = (stats.get("last_at") or "")[:10]
        val = str(stats["last_item"])[:200]
        if last_at:
            val += f"\n`{last_at}`"
        embed.add_field(name="Order Terakhir", value=val, inline=False)

    if ticket_mention:
        embed.add_field(name="Tiket", value=ticket_mention, inline=False)

    if avatar_url:
        embed.set_thumbnail(url=avatar_url)
    embed.set_footer(text=f"{STORE_NAME} · insight pelanggan")
    return embed


def _resolve_insight_channel_id() -> int:
    """Channel tujuan insight: CUSTOMER_INSIGHT_CHANNEL_ID, fallback LOG_CHANNEL_ID."""
    from utils.config import LOG_CHANNEL_ID
    try:
        from utils.config import CUSTOMER_INSIGHT_CHANNEL_ID
    except ImportError:
        CUSTOMER_INSIGHT_CHANNEL_ID = 0
    return CUSTOMER_INSIGHT_CHANNEL_ID or LOG_CHANNEL_ID or 0


async def send_insight(bot, ticket_channel, member):
    """Kirim insight pelanggan ke channel admin. Best-effort (tak pernah melempar).

    Dipanggil tiap cog tiket setelah channel tiket dibuat. `member` boleh objek
    discord User/Member; minimal punya `.id`.
    """
    try:
        channel_id = _resolve_insight_channel_id()
        if not channel_id:
            return
        channel = bot.get_channel(channel_id)
        if channel is None:
            return
        user_id = getattr(member, "id", None)
        if user_id is None:
            return
        stats = get_customer_stats(user_id)
        name = getattr(member, "display_name", None) or getattr(member, "name", None) or f"User {user_id}"
        avatar_url = None
        try:
            avatar_url = member.display_avatar.url
        except Exception:
            avatar_url = None
        ticket_mention = getattr(ticket_channel, "mention", None)
        embed = build_insight_embed(stats, name, avatar_url=avatar_url, ticket_mention=ticket_mention)
        await channel.send(embed=embed)
    except Exception as e:
        print(f"[CustomerInsight] send error: {e}")
