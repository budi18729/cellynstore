"""Unit test untuk utils/customer_insight.py (stats + embed builder)."""
import importlib


def _ci():
    import utils.customer_insight as ci
    importlib.reload(ci)
    return ci


def _log(db, user_id, layanan="robux", item="X", nominal=1000):
    db.log_transaction(layanan=layanan, nominal=nominal, item=item, user_id=user_id)


def test_stats_empty_for_new_customer(db):
    ci = _ci()
    s = ci.get_customer_stats(999)
    assert s["orders"] == 0
    assert s["total_spend"] == 0
    assert s["last_item"] is None
    assert s["rating_count"] == 0


def test_stats_aggregate(db):
    ci = _ci()
    _log(db, 111, layanan="robux", item="100 Robux", nominal=50000)
    _log(db, 111, layanan="lainnya:editing", item="CANVA PRO 1 Bulan", nominal=10000)
    _log(db, 111, layanan="robux", item="200 Robux", nominal=80000)
    # user lain tidak ikut
    _log(db, 222, layanan="ml", item="86 Diamond", nominal=20000)

    s = ci.get_customer_stats(111)
    assert s["orders"] == 3
    assert s["total_spend"] == 140000
    assert s["last_item"] == "200 Robux"        # terbaru (id desc)
    assert s["top_layanan"] == "robux"          # 2x robux > 1x lainnya
    assert s["first_at"] is not None and s["last_at"] is not None


def test_stats_rating_avg_from_reviews(db):
    ci = _ci()
    import utils.reviews as rv
    importlib.reload(rv)
    rv.init_reviews_db()
    _log(db, 111, item="100 Robux", nominal=50000)
    tx = rv.fetch_new_transactions(0)[0]
    rid = rv.create_pending(tx["id"], 111, "robux", "100 Robux", 50000)
    rv.submit_rating(rid, 4, "ok")

    s = ci.get_customer_stats(111)
    assert s["rating_count"] == 1
    assert s["rating_avg"] == 4.0


def test_build_embed_new_customer(db):
    ci = _ci()
    s = ci.get_customer_stats(999)
    embed = ci.build_insight_embed(s, "Budi", ticket_mention="#tiket")
    assert "Baru" in embed.kwargs.get("title", "")


def test_build_embed_repeat_customer(db):
    ci = _ci()
    for i in range(4):
        _log(db, 111, layanan="robux", item=f"Item{i}", nominal=10000)
    s = ci.get_customer_stats(111)
    embed = ci.build_insight_embed(s, "Budi", ticket_mention="#tiket")
    title = embed.kwargs.get("title", "")
    assert "Berulang" in title or "Setia" in title
    # ada field total order & total belanja
    names = [f["name"] for f in embed.fields]
    assert "Total Order" in names and "Total Belanja" in names
