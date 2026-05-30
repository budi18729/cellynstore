import sqlite3

DB_FILE = "midman.db"

def get_conn():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS tickets (
            channel_id        INTEGER PRIMARY KEY,
            pihak1_id         INTEGER,
            pihak2_id         INTEGER,
            item_p1           TEXT,
            item_p2           TEXT,
            fee_final         INTEGER,
            fee_paid          INTEGER DEFAULT 0,
            link_server       TEXT,
            admin_id          INTEGER,
            embed_message_id  INTEGER,
            ticket_number     INTEGER,
            opened_at         TEXT,
            fee_warning_id    INTEGER,
            verified_by_id    INTEGER,
            warned            INTEGER DEFAULT 0,
            warn_message_id   INTEGER,
            last_activity     TEXT
        )
    ''')
    for col, defval in [
        ('warned', 'INTEGER DEFAULT 0'),
        ('warn_message_id', 'INTEGER'),
        ('last_activity', 'TEXT'),
    ]:
        try:
            c.execute(f'ALTER TABLE tickets ADD COLUMN {col} {defval}')
        except Exception as e:
            if 'duplicate column' not in str(e).lower():
                print(f"[DB] Migration tickets {col}: {e}")
    c.execute('''
        CREATE TABLE IF NOT EXISTS counter (
            id    INTEGER PRIMARY KEY DEFAULT 1,
            count INTEGER DEFAULT 0
        )
    ''')
    c.execute('INSERT OR IGNORE INTO counter (id, count) VALUES (1, 0)')
    c.execute('''
        CREATE TABLE IF NOT EXISTS vilog_tickets (
            channel_id      INTEGER PRIMARY KEY,
            user_id         INTEGER,
            username_roblox TEXT,
            password        TEXT,
            email           TEXT,
            backup_codes    TEXT,
            premium         INTEGER DEFAULT 0,
            boost_nama      TEXT,
            boost_robux     INTEGER,
            metode          TEXT,
            nominal         INTEGER,
            admin_id        INTEGER,
            opened_at       TEXT,
            warned          INTEGER DEFAULT 0,
            warn_message_id INTEGER,
            last_activity   TEXT
        )
    ''')
    for col, defval in [
        ("email", "TEXT"),
        ("backup_codes", "TEXT"),
        ("premium", "INTEGER DEFAULT 0"),
        ("warned", "INTEGER DEFAULT 0"),
        ("warn_message_id", "INTEGER"),
        ("last_activity", "TEXT"),
    ]:
        try:
            c.execute(f'ALTER TABLE vilog_tickets ADD COLUMN {col} {defval}')
        except Exception as e:
            if 'duplicate column' not in str(e).lower():
                print(f"[DB] Migration vilog_tickets {col}: {e}")
    c.execute('''
        CREATE TABLE IF NOT EXISTS robux_rate (
            id    INTEGER PRIMARY KEY DEFAULT 1,
            rate  INTEGER DEFAULT 0
        )
    ''')
    c.execute('INSERT OR IGNORE INTO robux_rate (id, rate) VALUES (1, 0)')
    c.execute('''
        CREATE TABLE IF NOT EXISTS robux_tickets (
            channel_id  INTEGER PRIMARY KEY,
            user_id     INTEGER,
            item_id     INTEGER,
            item_name   TEXT,
            robux       INTEGER,
            rate        INTEGER,
            total       INTEGER,
            payment_method TEXT,
            payment_embed_msg_id INTEGER,
            paid        INTEGER DEFAULT 0,
            admin_id    INTEGER,
            opened_at   TEXT,
            warned      INTEGER DEFAULT 0,
            warn_message_id INTEGER,
            last_activity   TEXT
        )
    ''')
    for col, defval in [
        ('warned', 'INTEGER DEFAULT 0'),
        ('warn_message_id', 'INTEGER'),
        ('last_activity', 'TEXT'),
    ]:
        try:
            c.execute(f'ALTER TABLE robux_tickets ADD COLUMN {col} {defval}')
        except Exception as e:
            if 'duplicate column' not in str(e).lower():
                print(f"[DB] Migration robux_tickets {col}: {e}")
    c.execute('''
        CREATE TABLE IF NOT EXISTS bot_state (
            key   TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS ml_tickets (
            channel_id      INTEGER PRIMARY KEY,
            user_id         INTEGER,
            id_ml           TEXT,
            server_id       TEXT,
            dm              INTEGER,
            harga           INTEGER,
            opened_at       TEXT,
            game            TEXT DEFAULT 'ML',
            warned          INTEGER DEFAULT 0,
            item_label      TEXT,
            warn_message_id INTEGER,
            last_activity   TEXT
        )
    ''')
    for col, defval in [
        ('game', "TEXT DEFAULT 'ML'"),
        ('warned', 'INTEGER DEFAULT 0'),
        ('item_label', 'TEXT'),
        ('warn_message_id', 'INTEGER'),
        ('last_activity', 'TEXT'),
    ]:
        try:
            c.execute(f'ALTER TABLE ml_tickets ADD COLUMN {col} {defval}')
        except Exception as e:
            if 'duplicate column' not in str(e).lower():
                print(f"[DB] Migration ml_tickets {col}: {e}")

    c.execute('''
        CREATE TABLE IF NOT EXISTS ml_products (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            dm      INTEGER NOT NULL,
            harga   INTEGER NOT NULL
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS ff_products (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            dm      INTEGER NOT NULL,
            harga   INTEGER NOT NULL
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS robux_products (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            category    TEXT NOT NULL,
            name        TEXT NOT NULL,
            robux       INTEGER NOT NULL,
            active      INTEGER DEFAULT 1
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS vilog_boosts (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            nama    TEXT NOT NULL,
            robux   INTEGER NOT NULL,
            active  INTEGER DEFAULT 1
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS jb_tickets (
            channel_id      INTEGER PRIMARY KEY,
            p1_id           INTEGER,
            p2_id           INTEGER,
            deskripsi       TEXT,
            harga           INTEGER,
            fee_final       INTEGER,
            fee_penanggung  TEXT,
            admin_id        INTEGER,
            opened_at       TEXT,
            warned          INTEGER DEFAULT 0,
            status          TEXT DEFAULT 'menunggu_admin',
            last_activity   TEXT,
            warn_message_id INTEGER,
            embed_message_id INTEGER
        )
    ''')
    for col, defval in [
        ('warned', 'INTEGER DEFAULT 0'),
        ('last_activity', 'TEXT'),
        ('warn_message_id', 'INTEGER'),
        ('embed_message_id', 'INTEGER'),
    ]:
        try:
            c.execute(f'ALTER TABLE jb_tickets ADD COLUMN {col} {defval}')
        except Exception as e:
            if 'duplicate column' not in str(e).lower():
                print(f"[DB] Migration jb_tickets {col}: {e}")
    c.execute('''
        CREATE TABLE IF NOT EXISTS wdp_products (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            jumlah  INTEGER NOT NULL,
            harga   INTEGER NOT NULL
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS autopost_tasks (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            label             TEXT NOT NULL,
            channel_id        TEXT NOT NULL,
            message           TEXT NOT NULL,
            interval_minutes  INTEGER NOT NULL DEFAULT 60,
            active            INTEGER NOT NULL DEFAULT 1,
            last_sent         TEXT DEFAULT NULL
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS transaction_log (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            layanan     TEXT NOT NULL,
            nominal     INTEGER DEFAULT 0,
            item        TEXT,
            admin_id    INTEGER,
            user_id     INTEGER,
            closed_at   TEXT NOT NULL,
            durasi_detik INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()
    print("[DB] Database diinisialisasi.")


def log_transaction(layanan: str, nominal: int = 0, item: str = None,
                    admin_id: int = None, user_id: int = None,
                    closed_at=None, durasi_detik: int = 0):
    import datetime
    if closed_at is None:
        closed_at = datetime.datetime.now(datetime.timezone.utc)
    closed_at_str = closed_at.isoformat() if hasattr(closed_at, 'isoformat') else str(closed_at)
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "INSERT INTO transaction_log (layanan, nominal, item, admin_id, user_id, closed_at, durasi_detik) VALUES (?,?,?,?,?,?,?)",
        (layanan, nominal, item, admin_id, user_id, closed_at_str, durasi_detik)
    )
    conn.commit()
    conn.close()
