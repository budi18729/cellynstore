"""Unit test untuk helper transaction_log baru (qty + referensi pesan log)."""


def test_log_transaction_returns_id_and_qty(db):
    tx_id = db.log_transaction(
        layanan="robux", nominal=11000, item="Apple Music 1 Bulan",
        admin_id=1, user_id=2, qty=3,
    )
    assert isinstance(tx_id, int) and tx_id > 0
    row = db.get_transaction(tx_id)
    assert row is not None
    assert row["qty"] == 3
    assert row["item"] == "Apple Music 1 Bulan"
    assert row["nominal"] == 11000
    assert row["admin_id"] == 1 and row["user_id"] == 2


def test_log_transaction_default_qty(db):
    tx_id = db.log_transaction(layanan="ml", nominal=20000, item="86 Diamond", user_id=5)
    row = db.get_transaction(tx_id)
    assert row["qty"] == 1  # default


def test_set_transaction_log_message(db):
    tx_id = db.log_transaction(layanan="vilog", nominal=30000, item="Boost", user_id=7)
    row = db.get_transaction(tx_id)
    assert row["log_channel_id"] is None and row["log_message_id"] is None
    db.set_transaction_log_message(tx_id, 111222, 333444)
    row = db.get_transaction(tx_id)
    assert row["log_channel_id"] == 111222
    assert row["log_message_id"] == 333444


def test_get_transaction_missing(db):
    assert db.get_transaction(999999) is None
