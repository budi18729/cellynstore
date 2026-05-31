"""Unit test untuk follow-up langganan: seleksi murni + helper DB dedup."""
import datetime

import utils.subscription as sub


def test_needs_followup_within_lead_window():
    start = "2026-01-01T00:00:00+00:00"  # CANVA 1 Bulan -> habis 2026-01-31
    # 2 hari sebelum habis (29 Jan) dengan lead 3 -> True
    now = datetime.datetime(2026, 1, 29, tzinfo=datetime.timezone.utc)
    assert sub.needs_followup(start, "CANVA PRO 1 Bulan", now=now, lead_days=3) is True


def test_needs_followup_too_early():
    start = "2026-01-01T00:00:00+00:00"
    now = datetime.datetime(2026, 1, 10, tzinfo=datetime.timezone.utc)  # masih 20 hari
    assert sub.needs_followup(start, "CANVA PRO 1 Bulan", now=now, lead_days=3) is False


def test_needs_followup_already_expired():
    start = "2026-01-01T00:00:00+00:00"
    now = datetime.datetime(2026, 2, 5, tzinfo=datetime.timezone.utc)  # sudah lewat
    assert sub.needs_followup(start, "CANVA PRO 1 Bulan", now=now, lead_days=3) is False


def test_needs_followup_non_subscription():
    start = "2026-01-01T00:00:00+00:00"
    now = datetime.datetime(2026, 1, 2, tzinfo=datetime.timezone.utc)
    assert sub.needs_followup(start, "100 Robux", now=now, lead_days=3) is False


def test_fetch_candidates_and_mark_sent(db):
    db.log_transaction(layanan="lainnya:musik", nominal=15000,
                       item="SPOTIFY PREMIUM 1 Bulan", user_id=111)
    db.log_transaction(layanan="robux", nominal=50000,
                       item="100 Robux", user_id=222)

    rows = db.fetch_followup_candidates()
    assert len(rows) == 2
    assert all(r["followup_sent_at"] is None for r in rows)

    sub_row = next(r for r in rows if "SPOTIFY" in r["item"])
    # tandai sekali -> True, kedua kali -> False (idempoten)
    assert db.mark_followup_sent(sub_row["id"]) is True
    assert db.mark_followup_sent(sub_row["id"]) is False

    # baris yang sudah ditandai tidak muncul lagi
    rows2 = db.fetch_followup_candidates()
    assert all(r["id"] != sub_row["id"] for r in rows2)
