"""
utils/service_info.py
Helper untuk membaca/menyimpan informasi layanan (deskripsi, S&K, cara bayar)
yang ditampilkan ke member sebelum membuka tiket.
"""
from utils.db import get_conn


def _ensure_table():
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS service_info (
            service_key  TEXT PRIMARY KEY,
            description  TEXT DEFAULT '',
            terms        TEXT DEFAULT '',
            payment_info TEXT DEFAULT ''
        )
    """)
    conn.commit()
    conn.close()


_ensure_table()


def get_service_info(service_key: str) -> dict:
    """Ambil info layanan. Return dict dengan key description, terms, payment_info."""
    conn = get_conn()
    c = conn.cursor()
    row = c.execute(
        "SELECT description, terms, payment_info FROM service_info WHERE service_key=?",
        (service_key,)
    ).fetchone()
    conn.close()
    if row:
        return {
            "description": row["description"] or "",
            "terms": row["terms"] or "",
            "payment_info": row["payment_info"] or "",
        }
    return {"description": "", "terms": "", "payment_info": ""}


def set_service_info(service_key: str, description: str, terms: str, payment_info: str):
    """Simpan info layanan ke DB."""
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        INSERT OR REPLACE INTO service_info (service_key, description, terms, payment_info)
        VALUES (?, ?, ?, ?)
    """, (service_key, description, terms, payment_info))
    conn.commit()
    conn.close()


def build_info_embed(service_name: str, info: dict, color: int = 0x5865F2) -> "discord.Embed":
    """
    Buat embed informasi layanan untuk ditampilkan ke member sebelum buka tiket.
    Hanya field yang diisi yang ditampilkan.
    """
    import discord
    from utils.config import STORE_NAME

    THUMBNAIL = "https://i.imgur.com/CWtUCzj.png"

    embed = discord.Embed(
        title=f"ℹ️  INFO — {service_name.upper()}",
        color=color,
    )

    if info.get("description"):
        embed.add_field(name="📋 Deskripsi", value=info["description"], inline=False)

    if info.get("terms"):
        embed.add_field(name="📜 Syarat & Ketentuan", value=info["terms"], inline=False)

    if info.get("payment_info"):
        embed.add_field(name="💳 Cara Pembayaran", value=info["payment_info"], inline=False)

    embed.set_footer(text=f"{STORE_NAME} • Klik Lanjutkan untuk membuka tiket")
    return embed


# Daftar service key yang dipakai di seluruh bot
SERVICE_KEYS = {
    "midman_trade":  "Midman Trade",
    "midman_jb":     "Midman Jual Beli",
    "vilog":         "Boost Via Login",
    "robux":         "Robux Store",
    "gp":            "Topup Robux via Gamepass",
    "ml":            "Topup Game",
    "lainnya":       "Cloud Phone & Nitro",
    "scaset":        "SC TB / Aset Game",
}
