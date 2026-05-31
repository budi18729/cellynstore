"""Unit test untuk laporan harian (#7) & pengingat rating (#4 reminder)."""
import datetime
import importlib


def _rv():
    import utils.reviews as rv
    importlib.reload(rv)
    rv.init_reviews_db()
    return rv


def _log_tx(realdb, layanan, user_id, item="X", nominal=1000, closed_at=None):
    realdb.log_transaction(
        layanan=layanan, nominal=nominal, item=item, user_id=user_id,
        closed_at=closed_at,
    )


def test_get_daily_report_aggregates(db):
    rv = _rv()
    today = datetime.datetime(2026, 5, 30, 10, 0, tzinfo=datetime.timezone.utc)
    other = datetime.datetime(2026, 5, 29, 10, 0, tzinfo=datetime.timezone.utc)
    _log_tx(db, "robux", 1, nominal=50000, closed_at=today)
    _log_tx(db, "robux", 2, nominal=30000, closed_at=today)
    _log_tx(db, "ml", 3, nominal=20000, closed_at=today)
    _log_tx(db, "vilog", 4, nominal=99999, closed_at=other)  # hari lain, jangan kehitung

    rep = rv.get_daily_report("2026-05-30")
    assert rep["total_tx"] == 3
    assert rep["total_omzet"] == 100000
    # per layanan: robux (2x, 80000) di atas ml (1x, 20000)
    assert rep["per_layanan"][0]["layanan"] == "robux"
    assert rep["per_layanan"][0]["count"] == 2
    assert rep["per_layanan"][0]["omzet"] == 80000
    # vilog hari lain tidak muncul
    assert all(p["layanan"] != "vilog" for p in rep["per_layanan"])


def test_get_daily_report_rating(db):
    rv = _rv()
    today = datetime.datetime(2026, 5, 30, 10, 0, tzinfo=datetime.timezone.utc)
    _log_tx(db, "robux", 1, closed_at=today)
    tx = rv.fetch_new_transactions(0)[0]
    rid = rv.create_pending(tx["id"], 1, "robux")
    rv.submit_rating(rid, 5, "mantap")
    rep = rv.get_daily_report(datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d"))
    assert rep["rating_count"] == 1
    assert rep["rating_avg"] == 5.0


def test_get_daily_report_empty(db):
    rv = _rv()
    rep = rv.get_daily_report("2020-01-01")
    assert rep["total_tx"] == 0
    assert rep["total_omzet"] == 0
    assert rep["per_layanan"] == []
    assert rep["rating_count"] == 0


def test_reminder_window_and_mark(db):
    rv = _rv()
    _log_tx(db, "robux", 1)
    tx = rv.fetch_new_transactions(0)[0]
    rid = rv.create_pending(tx["id"], 1, "robux")
    # deadline default = +24h, jadi belum masuk window reminder (<=6h)
    assert rv.fetch_due_for_reminder() == []
    # majukan deadline ke 3 jam dari sekarang -> masuk window
    conn = db.get_conn()
    c = conn.cursor()
    soon = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=3)).isoformat()
    c.execute("UPDATE reviews SET deadline_at=? WHERE id=?", (soon, rid))
    conn.commit()
    conn.close()
    due = rv.fetch_due_for_reminder()
    assert [r["id"] for r in due] == [rid]
    # mark sekali jalan; tidak muncul lagi
    assert rv.mark_reminded(rid) is True
    assert rv.mark_reminded(rid) is False
    assert rv.fetch_due_for_reminder() == []


def test_reminder_skips_already_rated(db):
    rv = _rv()
    _log_tx(db, "robux", 1)
    tx = rv.fetch_new_transactions(0)[0]
    rid = rv.create_pending(tx["id"], 1, "robux")
    rv.submit_rating(rid, 5)  # sudah rating
    conn = db.get_conn()
    c = conn.cursor()
    soon = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=2)).isoformat()
    c.execute("UPDATE reviews SET deadline_at=? WHERE id=?", (soon, rid))
    conn.commit()
    conn.close()
    # status sudah 'rated', bukan 'pending' -> tidak masuk reminder
    assert rv.fetch_due_for_reminder() == []
