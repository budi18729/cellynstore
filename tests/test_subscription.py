"""Unit test untuk utils/subscription.py (parse durasi & sisa masa)."""
import datetime

import utils.subscription as sub


def test_parse_duration_bulan_tahun_minggu():
    assert sub.parse_duration_days("CANVA PRO 1 Bulan") == 30
    assert sub.parse_duration_days("CHATGPT PLUS 3 Bulan") == 90
    assert sub.parse_duration_days("SPOTIFY PREMIUM 1 Tahun") == 365
    assert sub.parse_duration_days("XBOX GAMEPASS CODE 2 Minggu") == 14
    assert sub.parse_duration_days("NETFLIX 7 Hari") == 7


def test_parse_duration_per_unit_form():
    assert sub.parse_duration_days("HBO MAX STANDARD SHARING (per Bulan)") == 30
    assert sub.parse_duration_days("Layanan per tahun") == 365


def test_parse_duration_none_for_non_subscription():
    assert sub.parse_duration_days("100 Robux") is None
    assert sub.parse_duration_days("86 Diamond") is None
    assert sub.parse_duration_days("") is None
    assert sub.parse_duration_days(None) is None


def test_is_subscription():
    assert sub.is_subscription("CANVA PRO 1 Bulan") is True
    assert sub.is_subscription("100 Robux") is False


def test_expiry_and_days_remaining():
    start = "2026-01-01T00:00:00+00:00"
    exp = sub.expiry_date(start, "CANVA PRO 1 Bulan")
    assert exp == datetime.datetime(2026, 1, 31, tzinfo=datetime.timezone.utc)

    # 10 hari setelah mulai, produk 30 hari -> sisa 20 hari
    now = datetime.datetime(2026, 1, 11, tzinfo=datetime.timezone.utc)
    assert sub.days_remaining(start, "CANVA PRO 1 Bulan", now=now) == 20

    # sudah lewat -> negatif
    now_late = datetime.datetime(2026, 2, 15, tzinfo=datetime.timezone.utc)
    assert sub.days_remaining(start, "CANVA PRO 1 Bulan", now=now_late) < 0


def test_days_remaining_default_for_non_subscription():
    start = "2026-01-01T00:00:00+00:00"
    # tanpa durasi & tanpa default -> None
    assert sub.days_remaining(start, "100 Robux") is None
    # dengan default 7 hari
    now = datetime.datetime(2026, 1, 3, tzinfo=datetime.timezone.utc)
    assert sub.days_remaining(start, "100 Robux", now=now, default_days=7) == 5


def test_expiry_handles_naive_datetime_and_bad_input():
    assert sub.expiry_date(None, "CANVA PRO 1 Bulan") is None
    assert sub.expiry_date("not-a-date", "CANVA PRO 1 Bulan") is None
    # naive datetime diperlakukan sebagai UTC
    naive = datetime.datetime(2026, 1, 1)
    exp = sub.expiry_date(naive, "1 Minggu")
    assert exp == datetime.datetime(2026, 1, 8, tzinfo=datetime.timezone.utc)


def test_warranty_transactions_include_closed_at(db):
    import importlib
    import utils.reviews as rv
    importlib.reload(rv)
    rv.init_reviews_db()

    db.log_transaction(layanan="lainnya:editing", nominal=10000,
                       item="CANVA PRO 1 Bulan", user_id=111)
    tx = rv.fetch_new_transactions(0)[0]
    rid = rv.create_pending(tx["id"], 111, "lainnya:editing", "CANVA PRO 1 Bulan", 10000)
    rv.submit_rating(rid, 5, "mantap")

    wt = rv.get_warranty_transactions(111)
    assert len(wt) == 1
    assert wt[0]["item"] == "CANVA PRO 1 Bulan"
    # closed_at kini ikut ter-join dari transaction_log
    assert wt[0]["closed_at"] is not None
