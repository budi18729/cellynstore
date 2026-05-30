from utils.db import get_conn


AVAILABLE_KEY = "robux_stock_available"
OUT_TOTAL_KEY = "robux_stock_out_total"


def _get_int(key: str, default: int = 0) -> int:
    conn = get_conn()
    row = conn.execute("SELECT value FROM bot_state WHERE key=?", (key,)).fetchone()
    conn.close()
    if not row:
        return default
    try:
        return int(row["value"])
    except Exception:
        return default


def _set_int(key: str, value: int):
    conn = get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO bot_state (key, value) VALUES (?, ?)",
        (key, str(int(value))),
    )
    conn.commit()
    conn.close()


def get_available() -> int:
    return _get_int(AVAILABLE_KEY, 0)


def set_available(value: int):
    _set_int(AVAILABLE_KEY, max(0, int(value)))


def add_available(delta: int) -> int:
    current = get_available()
    new_value = max(0, current + int(delta))
    set_available(new_value)
    return new_value


def get_out_total() -> int:
    return _get_int(OUT_TOTAL_KEY, 0)


def add_out_total(delta: int) -> int:
    current = get_out_total()
    new_value = max(0, current + int(delta))
    _set_int(OUT_TOTAL_KEY, new_value)
    return new_value


def record_outgoing(robux_amount: int):
    """Decrement available and increment out_total for completed Robux orders."""
    amount = max(0, int(robux_amount))
    if amount <= 0:
        return
    add_out_total(amount)
    add_available(-amount)

