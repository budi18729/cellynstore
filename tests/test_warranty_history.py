"""Unit test untuk helper riwayat order (#4) & garansi (#6) di utils/reviews.py."""
import importlib


def _rv():
    import utils.reviews as rv
    importlib.reload(rv)
    rv.init_reviews_db()
    return rv


def _log_tx(realdb, layanan, user_id, item="X", nominal=1000):
    realdb.log_transaction(layanan=layanan, nominal=nominal, item=item, user_id=user_id)


def test_get_user_transactions_only_own_and_status(db):
    rv = _rv()
    # user 111: 2 transaksi, user 222: 1 transaksi
    _log_tx(db, "robux", 111, item="100 Robux", nominal=50000)
    _log_tx(db, "ml", 111, item="86 Diamond", nominal=20000)
    _log_tx(db, "vilog", 222, item="Boost", nominal=30000)

    own = rv.get_user_transactions(111)
    assert len(own) == 2
    assert all(t["item"] in ("100 Robux", "86 Diamond") for t in own)
    # terbaru dulu (id desc)
    assert own[0]["item"] == "86 Diamond"
    # user lain tidak tercampur
    assert rv.count_user_transactions(111) == 2
    assert rv.count_user_transactions(222) == 1

    other = rv.get_user_transactions(222)
    assert len(other) == 1 and other[0]["item"] == "Boost"


def test_user_transaction_review_status_join(db):
    rv = _rv()
    _log_tx(db, "robux", 111, item="100 Robux")
    tx = rv.fetch_new_transactions(0)[0]
    # belum ada review -> status None
    rows = rv.get_user_transactions(111)
    assert rows[0]["review_status"] is None
    # buat + rating -> status 'rated'
    rid = rv.create_pending(tx["id"], 111, "robux", "100 Robux", 50000)
    rv.submit_rating(rid, 5, "mantap")
    rows = rv.get_user_transactions(111)
    assert rows[0]["review_status"] == rv.STATUS_RATED
    assert rows[0]["rating"] == 5


def test_has_valid_warranty(db):
    rv = _rv()
    _log_tx(db, "robux", 111, item="100 Robux")
    tx = rv.fetch_new_transactions(0)[0]
    rid = rv.create_pending(tx["id"], 111, "robux", "100 Robux", 50000)
    # pending -> belum bergaransi
    assert rv.has_valid_warranty(111) is False
    # setelah rating -> bergaransi
    rv.submit_rating(rid, 4, None)
    assert rv.has_valid_warranty(111) is True
    # user tanpa transaksi -> False
    assert rv.has_valid_warranty(999) is False


def test_warranty_expired_not_eligible(db):
    rv = _rv()
    _log_tx(db, "robux", 111, item="100 Robux")
    tx = rv.fetch_new_transactions(0)[0]
    rid = rv.create_pending(tx["id"], 111, "robux", "100 Robux", 50000)
    rv.mark_expired(rid)  # lewat 24 jam tanpa rating
    assert rv.has_valid_warranty(111) is False
    assert rv.get_warranty_transactions(111) == []


def test_get_warranty_transactions_detail(db):
    rv = _rv()
    _log_tx(db, "robux", 111, item="100 Robux", nominal=50000)
    tx = rv.fetch_new_transactions(0)[0]
    rid = rv.create_pending(tx["id"], 111, "robux", "100 Robux", 50000)
    rv.submit_rating(rid, 5, "keren")
    wt = rv.get_warranty_transactions(111)
    assert len(wt) == 1
    assert wt[0]["item"] == "100 Robux"
    assert wt[0]["rating"] == 5
    assert wt[0]["tx_id"] == tx["id"]
