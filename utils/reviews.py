"""Data layer untuk sistem rating & ulasan (review) toko.

Sumber pemicu rating adalah tabel `transaction_log` (diisi semua layanan saat
tiket ditutup). Modul ini menyimpan rating/ulasan ke tabel `reviews` dan
melacak transaksi terakhir yang sudah diproses lewat `bot_state`.

Catatan desain:
- Satu rating per transaksi: kolom `tx_id` UNIQUE (anti-spam & anti-duplikat).
- `tx_id` boleh NULL untuk rating manual (mis. via command), tetap dibatasi
  oleh logika pemanggil bila perlu.
- Tidak meng-import discord; murni SQLite supaya gampang di-unit-test.
"""

import datetime

from utils.db import get_conn

# Kunci bot_state untuk melacak id transaction_log terakhir yang sudah diminta rating.
LAST_TX_KEY = "reviews_last_tx_id"

# Status review.
STATUS_PENDING = "pending"     # prompt sudah dikirim, menunggu rating member
STATUS_RATED = "rated"         # member sudah memberi rating
STATUS_PUBLISHED = "published" # ulasan sudah diposting ke channel testimoni

VALID_RATINGS = (1, 2, 3, 4, 5)


def init_reviews_db():
    """Buat tabel `reviews` bila belum ada. Idempoten."""
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS reviews (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            tx_id        INTEGER UNIQUE,
            user_id      INTEGER NOT NULL,
            layanan      TEXT,
            item         TEXT,
            nominal      INTEGER DEFAULT 0,
            rating       INTEGER,
            review_text  TEXT,
            status       TEXT NOT NULL DEFAULT 'pending',
            prompt_msg_id    INTEGER,
            published_msg_id INTEGER,
            created_at   TEXT NOT NULL,
            rated_at     TEXT
        )
        """
    )
    conn.commit()
    conn.close()


def _now_iso():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


# ── Pelacakan transaksi (poller) ────────────────────────────────────────────────
def get_last_tx_id() -> int:
    """Ambil id transaction_log terakhir yang sudah diproses (0 bila belum ada)."""
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT value FROM bot_state WHERE key=?", (LAST_TX_KEY,))
    row = c.fetchone()
    conn.close()
    if not row:
        return 0
    try:
        return int(row["value"])
    except (TypeError, ValueError):
        return 0


def set_last_tx_id(tx_id: int):
    """Simpan id transaction_log terakhir yang sudah diproses."""
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "INSERT OR REPLACE INTO bot_state (key, value) VALUES (?, ?)",
        (LAST_TX_KEY, str(int(tx_id))),
    )
    conn.commit()
    conn.close()


def current_max_tx_id() -> int:
    """id terbesar di transaction_log saat ini (0 bila kosong)."""
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT MAX(id) AS m FROM transaction_log")
    row = c.fetchone()
    conn.close()
    return int(row["m"]) if row and row["m"] is not None else 0


def fetch_new_transactions(after_id: int, limit: int = 50) -> list[dict]:
    """Ambil transaksi dengan id > after_id yang punya user_id, urut id menaik."""
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        """
        SELECT id, layanan, nominal, item, user_id, closed_at
        FROM transaction_log
        WHERE id > ? AND user_id IS NOT NULL
        ORDER BY id ASC
        LIMIT ?
        """,
        (after_id, limit),
    )
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── CRUD review ──────────────────────────────────────────────────────────────────
def create_pending(tx_id, user_id: int, layanan: str = None, item: str = None,
                   nominal: int = 0) -> int | None:
    """Buat baris review status 'pending'. Return review id, atau None bila
    tx_id sudah pernah dibuat (UNIQUE) — anti-duplikat."""
    conn = get_conn()
    c = conn.cursor()
    try:
        c.execute(
            """
            INSERT INTO reviews (tx_id, user_id, layanan, item, nominal, status, created_at)
            VALUES (?,?,?,?,?,?,?)
            """,
            (tx_id, user_id, layanan, item, nominal or 0, STATUS_PENDING, _now_iso()),
        )
        conn.commit()
        return c.lastrowid
    except Exception as e:
        # IntegrityError (tx_id UNIQUE) -> sudah ada, lewati.
        if "UNIQUE" in str(e).upper():
            return None
        raise
    finally:
        conn.close()


def set_prompt_msg_id(review_id: int, msg_id: int):
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE reviews SET prompt_msg_id=? WHERE id=?", (msg_id, review_id))
    conn.commit()
    conn.close()


def get_review(review_id: int) -> dict | None:
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM reviews WHERE id=?", (review_id,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None


def submit_rating(review_id: int, rating: int, review_text: str = None) -> bool:
    """Simpan rating (1-5) + ulasan opsional, set status 'rated'.

    Hanya berlaku bila review masih 'pending' (anti-double-submit). Return True
    bila tersimpan, False bila tidak valid / sudah dirating sebelumnya.
    """
    if rating not in VALID_RATINGS:
        return False
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        """
        UPDATE reviews
        SET rating=?, review_text=?, status=?, rated_at=?
        WHERE id=? AND status=?
        """,
        (rating, review_text, STATUS_RATED, _now_iso(), review_id, STATUS_PENDING),
    )
    changed = c.rowcount
    conn.commit()
    conn.close()
    return changed > 0


def set_published(review_id: int, published_msg_id: int):
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "UPDATE reviews SET status=?, published_msg_id=? WHERE id=?",
        (STATUS_PUBLISHED, published_msg_id, review_id),
    )
    conn.commit()
    conn.close()


# ── Statistik & listing ──────────────────────────────────────────────────────────
def get_stats(layanan: str = None) -> dict:
    """Ringkasan rating: jumlah, rata-rata, dan sebaran bintang 1-5.

    Bila `layanan` diberikan, difilter untuk layanan itu (prefix match juga,
    mis. 'lainnya' mencakup 'lainnya:editing')."""
    conn = get_conn()
    c = conn.cursor()
    where = "rating IS NOT NULL"
    params: list = []
    if layanan:
        where += " AND (layanan = ? OR layanan LIKE ?)"
        params += [layanan, f"{layanan}:%"]
    c.execute(f"SELECT COUNT(*) AS n, AVG(rating) AS avg FROM reviews WHERE {where}", params)
    row = c.fetchone()
    n = row["n"] or 0
    avg = round(row["avg"], 2) if row["avg"] is not None else 0.0

    dist = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    c.execute(
        f"SELECT rating, COUNT(*) AS cnt FROM reviews WHERE {where} GROUP BY rating",
        params,
    )
    for r in c.fetchall():
        if r["rating"] in dist:
            dist[r["rating"]] = r["cnt"]
    conn.close()
    return {"count": n, "average": avg, "distribution": dist}


def get_recent_reviews(limit: int = 5, layanan: str = None) -> list[dict]:
    """Ulasan terbaru yang sudah dirating (untuk ditampilkan di command stats)."""
    conn = get_conn()
    c = conn.cursor()
    where = "rating IS NOT NULL"
    params: list = []
    if layanan:
        where += " AND (layanan = ? OR layanan LIKE ?)"
        params += [layanan, f"{layanan}:%"]
    c.execute(
        f"SELECT * FROM reviews WHERE {where} ORDER BY rated_at DESC LIMIT ?",
        params + [limit],
    )
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]
