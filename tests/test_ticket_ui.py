"""Unit test untuk utils/ticket_ui.py (penamaan channel, warna, embed)."""
import sys
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# utils.config butuh STORE_NAME; sediakan stub agar tidak butuh .env.
import types
if "utils.config" not in sys.modules:
    sys.modules["utils.config"] = types.SimpleNamespace(STORE_NAME="Cellyn Store")

import utils.ticket_ui as tu


def test_format_number_7_digit():
    assert tu.format_number(44) == "0000044"
    assert tu.format_number(0) == "0000000"
    assert tu.format_number(1234567) == "1234567"


def test_channel_name_format():
    assert tu.channel_name("robux", 42, "Budi") == "🏷️-robux-0000042-budi"
    # sanitize: spasi/karakter aneh dibuang, lowercase
    assert tu.channel_name("lainnya", 7, "Citra Budi!") == "🏷️-lainnya-0000007-citrabudi"
    # username kosong -> fallback 'user'
    assert tu.channel_name("ml", 1, "!!!") == "🏷️-ml-0000001-user"


def test_neon_colors_per_layanan():
    assert tu.neon_color("robux") == 0xFF10F0
    assert tu.neon_color("lainnya") == 0x1F51FF
    # tak dikenal -> default
    assert tu.neon_color("unknown") == tu.DEFAULT_NEON


def test_avatar_url_none_safe():
    assert tu.avatar_url(None) is None

    class M:
        class display_avatar:
            url = "https://cdn/x.png"
    assert tu.avatar_url(M()) == "https://cdn/x.png"


def test_open_ticket_embed_basic():
    class Member:
        mention = "@budi"
    e = tu.open_ticket_embed("robux", 42, Member(), item="1000 Robux", total="Rp 150.000")
    assert "TIKET ROBUX" in e.kwargs["title"] and "#0000042" in e.kwargs["title"]
    assert e.kwargs["color"] == 0xFF10F0
    names = [f["name"] for f in e.fields]
    assert "Member" in names and "Item" in names


def test_warranty_status_line():
    # Belum rating -> belum aktif
    assert "Belum Aktif" in tu.warranty_status_line(None)
    assert "Belum Aktif" in tu.warranty_status_line(0)
    # Sudah rating -> aktif + jumlah bintang
    s = tu.warranty_status_line(5)
    assert "Aktif" in s and "5" in s and "Belum" not in s


def test_success_log_text_belum_dan_sudah_rating():
    common = dict(
        seller="<@1>", buyer="<@2>",
        product="Apple Music 1 Bulan All Device",
        qty=1, harga=11000, rating_channel_id=999,
    )
    # Belum rating
    belum = tu.success_log_text(rating=None, **common)
    assert "TERIMA KASIH SUDAH ORDER" in belum
    assert "**Seller** : <@1>" in belum
    assert "**Buyer** : <@2>" in belum
    assert "**Product** : Apple Music 1 Bulan All Device" in belum
    assert "**Jumlah** : 1" in belum
    assert "Rp 11.000" in belum
    assert "Belum Aktif" in belum
    assert "<#999>" in belum  # mention channel rating

    # Sudah rating -> teks otomatis berubah
    sudah = tu.success_log_text(rating=5, **common)
    assert "✅" in sudah and "Aktif (Sudah DiRating 5" in sudah
    assert "Belum Aktif" not in sudah

