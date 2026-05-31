"""Utilitas durasi langganan: parse durasi dari nama produk & hitung kedaluwarsa.

Durasi langganan di toko ini HANYA tersimpan di string nama produk
(transaction_log.item), mis. "CANVA PRO 1 Bulan", "SPOTIFY ... 3 Bulan",
"XBOX GAMEPASS CODE 2 Minggu", atau bentuk "(per Bulan)".

Modul ini murni (tanpa discord/DB) supaya gampang di-unit-test dan bisa
dipakai bersama oleh fitur garansi pintar (#1) & follow-up langganan (#3).
"""

import datetime
import re

# Perkiraan jumlah hari per satuan durasi (bulan/tahun dibulatkan umum).
_UNIT_DAYS = {
    "hari": 1,
    "minggu": 7,
    "bulan": 30,
    "tahun": 365,
}

# Sinonim satuan -> kunci kanonik di _UNIT_DAYS.
_UNIT_ALIASES = {
    "hari": "hari", "day": "hari", "days": "hari",
    "minggu": "minggu", "week": "minggu", "weeks": "minggu", "mgg": "minggu",
    "bulan": "bulan", "bln": "bulan", "month": "bulan", "months": "bulan", "mo": "bulan",
    "tahun": "tahun", "thn": "tahun", "year": "tahun", "years": "tahun", "yr": "tahun",
}

_UNIT_PATTERN = "|".join(sorted(_UNIT_ALIASES, key=len, reverse=True))
# "1 Bulan", "3 bln", "2 Minggu", "1 Tahun" (angka + satuan)
_NUM_UNIT_RE = re.compile(rf"(\d+)\s*({_UNIT_PATTERN})\b", re.IGNORECASE)
# "(per Bulan)" / "per bulan" -> dianggap 1 bulan
_PER_UNIT_RE = re.compile(rf"per\s+({_UNIT_PATTERN})\b", re.IGNORECASE)


def parse_duration_days(name: str):
    """Perkirakan durasi langganan (dalam hari) dari nama produk.

    Mengembalikan int hari, atau None bila nama tidak mengandung durasi
    (mis. produk non-langganan seperti "100 Robux", "86 Diamond").
    Bila ada beberapa angka+satuan, ambil yang PERTAMA (paling relevan).
    """
    if not name:
        return None
    text = str(name).lower()

    m = _NUM_UNIT_RE.search(text)
    if m:
        qty = int(m.group(1))
        unit = _UNIT_ALIASES[m.group(2).lower()]
        if qty > 0:
            return qty * _UNIT_DAYS[unit]

    m = _PER_UNIT_RE.search(text)
    if m:
        unit = _UNIT_ALIASES[m.group(1).lower()]
        return _UNIT_DAYS[unit]

    return None


def is_subscription(name: str) -> bool:
    """True bila nama produk mengandung durasi langganan."""
    return parse_duration_days(name) is not None


def _parse_dt(value):
    """Parse ISO string / datetime jadi datetime aware (UTC). None bila gagal."""
    if value is None:
        return None
    if isinstance(value, datetime.datetime):
        dt = value
    else:
        try:
            dt = datetime.datetime.fromisoformat(str(value))
        except (ValueError, TypeError):
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    return dt


def expiry_date(start, name: str, default_days: int = None):
    """Tanggal kedaluwarsa = start + durasi(nama).

    `start` boleh ISO string atau datetime. Bila nama tidak punya durasi,
    pakai `default_days` (bila diberikan) atau None.
    """
    start_dt = _parse_dt(start)
    if start_dt is None:
        return None
    days = parse_duration_days(name)
    if days is None:
        days = default_days
    if days is None:
        return None
    return start_dt + datetime.timedelta(days=days)


def days_remaining(start, name: str, now=None, default_days: int = None):
    """Sisa hari sampai kedaluwarsa (bisa negatif bila sudah lewat).

    None bila durasi tak diketahui & tak ada default. Sisa waktu positif
    dibulatkan ke ATAS (sisa 0.1 hari tetap dihitung "1 hari lagi").
    """
    exp = expiry_date(start, name, default_days=default_days)
    if exp is None:
        return None
    now_dt = _parse_dt(now) or datetime.datetime.now(datetime.timezone.utc)
    secs = (exp - now_dt).total_seconds()
    if secs > 0:
        return int(-(-secs // 86400))  # ceil
    return int(secs // 86400)          # floor (negatif = sudah lewat)



def needs_followup(closed_at, item: str, now=None, lead_days: int = 3) -> bool:
    """True bila langganan akan habis dalam <= lead_days (dan belum habis).

    Dipakai untuk memilih transaksi langganan yang perlu DM follow-up.
    Produk non-langganan (durasi tak terbaca) -> False.
    """
    days = parse_duration_days(item)
    if days is None:
        return False  # bukan langganan -> tak ada follow-up
    sisa = days_remaining(closed_at, item, now=now)
    if sisa is None:
        return False
    return 0 < sisa <= lead_days
