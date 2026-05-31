"""Unit test untuk utils/reviews.py (sistem rating & ulasan).

Menguji: seeding anti-spam transaksi historis, deteksi transaksi baru, anti-
duplikat (tx_id UNIQUE), submit rating (valid/invalid/double), kedaluwarsa 24
jam, statistik (avg/sebaran/prefix-match), dan top reviewer.
"""
import datetime
import importlib


def _log_tx(realdb, layanan, user_id, item="X", nominal=1000):
    realdb.log_transaction(layanan=layanan, nominal=nominal, item=item, user_id=user_id)


def _rv():
    import utils.reviews as rv
    importlib.reload(rv)
    rv.init_reviews_db()
    return rv


def test_poller_seed_skips_historical(db):
    rv = _rv()
    _log_tx(db, "robux", 111)
    _log_tx(db, "vilog", 222)
    # First run: pointer di-seed ke MAX(id) -> transaksi historis TIDAK diprompt.
    assert rv.get_last_tx_id() == 0
    rv.set_last_tx_id(rv.current_max_tx_id())
    assert rv.fetch_new_transactions(rv.get_last_tx_id()) == []


def test_fetch_new_transactions(db):
    rv = _rv()
    _log_tx(db, "robux", 111)
    rv.set_last_tx_id(rv.current_max_tx_id())
    _log_tx(db, "lainnya:editing", 333, item="REMINI", nominal=15000)
    _log_tx(db, "ml", 444, item="86 Diamond", nominal=20000)
    new = rv.fetch_new_transactions(rv.get_last_tx_id())
    assert len(new) == 2
    assert {t["user_id"] for t in new} == {333, 444}


def test_create_pending_dedup(db):
    rv = _rv()
    _log_tx(db, "robux", 111)
    tx = rv.fetch_new_transactions(0)[0]
    rid = rv.create_pending(tx["id"], tx["user_id"], tx["layanan"], tx["item"], tx["nominal"])
    assert rid is not None
    # tx_id UNIQUE -> duplikat ditolak (None)
    assert rv.create_pending(tx["id"], tx["user_id"]) is None


def test_submit_rating_valid_and_guards(db):
    rv = _rv()
    _log_tx(db, "robux", 111)
    tx = rv.fetch_new_transactions(0)[0]
    rid = rv.create_pending(tx["id"], tx["user_id"])
    # valid
    assert rv.submit_rating(rid, 5, "mantap") is True
    # double-submit diblok (status sudah 'rated')
    assert rv.submit_rating(rid, 3, "berubah") is False
    # nilai invalid diblok
    rid2 = rv.create_pending(999, 222)
    assert rv.submit_rating(rid2, 9) is False
    assert rv.submit_rating(rid2, 0) is False
    r = rv.get_review(rid)
    assert r["rating"] == 5 and r["status"] == rv.STATUS_RATED


def test_24h_expiry(db):
    rv = _rv()
    _log_tx(db, "robux", 111)
    tx = rv.fetch_new_transactions(0)[0]
    rid = rv.create_pending(tx["id"], tx["user_id"])
    r = rv.get_review(rid)
    created = datetime.datetime.fromisoformat(r["created_at"])
    deadline = datetime.datetime.fromisoformat(r["deadline_at"])
    # deadline = created + 24 jam
    assert abs((deadline - created).total_seconds() - 24 * 3600) < 1
    # belum expired
    assert rv.fetch_expired_pending() == []
    # backdate deadline ke masa lalu -> terdeteksi expired
    conn = db.get_conn()
    c = conn.cursor()
    past = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=1)).isoformat()
    c.execute("UPDATE reviews SET deadline_at=? WHERE id=?", (past, rid))
    conn.commit()
    conn.close()
    assert [e["id"] for e in rv.fetch_expired_pending()] == [rid]
    # mark_expired sekali jalan; rating setelah expired ditolak
    assert rv.mark_expired(rid) is True
    assert rv.mark_expired(rid) is False
    assert rv.submit_rating(rid, 5) is False


def test_stats_and_prefix_match(db):
    rv = _rv()
    # 3 rating: editing(5), gaming(3), robux(4)
    for i, (lay, rating) in enumerate([("lainnya:editing", 5), ("lainnya:gaming", 3), ("robux", 4)]):
        _log_tx(db, lay, 100 + i)
        tx = rv.fetch_new_transactions(rv.get_last_tx_id())[-1]
        rid = rv.create_pending(tx["id"], tx["user_id"], tx["layanan"])
        rv.set_last_tx_id(tx["id"])
        rv.submit_rating(rid, rating)
    allst = rv.get_stats()
    assert allst["count"] == 3
    assert allst["distribution"][5] == 1 and allst["distribution"][4] == 1 and allst["distribution"][3] == 1
    # prefix-match: 'lainnya' mencakup editing + gaming
    lain = rv.get_stats("lainnya")
    assert lain["count"] == 2
    assert abs(lain["average"] - 4.0) < 1e-6


def test_get_recent_reviews(db):
    rv = _rv()
    _log_tx(db, "robux", 111)
    tx = rv.fetch_new_transactions(0)[0]
    rid = rv.create_pending(tx["id"], tx["user_id"])
    rv.submit_rating(rid, 5, "keren")
    recent = rv.get_recent_reviews(limit=5)
    assert len(recent) == 1 and recent[0]["review_text"] == "keren"


def test_top_reviewers(db):
    rv = _rv()
    # user 111 rates 3x, user 222 rates 1x
    n = 0
    for uid, times in [(111, 3), (222, 1)]:
        for _ in range(times):
            n += 1
            _log_tx(db, "robux", uid)
            tx = rv.fetch_new_transactions(rv.get_last_tx_id())[-1]
            rid = rv.create_pending(tx["id"], uid)
            rv.set_last_tx_id(tx["id"])
            rv.submit_rating(rid, 5)
    top = rv.get_top_reviewers(limit=10)
    assert top[0]["user_id"] == 111 and top[0]["count"] == 3
    assert top[1]["user_id"] == 222 and top[1]["count"] == 1
