"""
seed.py — Isi data produk default ke database.
Jalankan SEKALI saat setup perangkat baru:
  python3 seed.py

Aman dijalankan berulang — pakai INSERT OR IGNORE, tidak akan duplikat.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.db import get_conn, init_db

# ── DATA DEFAULT ──────────────────────────────────────────────────────────────

ML_PRODUCTS = [
    {"dm": 3,   "harga": 1500},
    {"dm": 5,   "harga": 2000},
    {"dm": 10,  "harga": 3000},
    {"dm": 12,  "harga": 4000},
    {"dm": 14,  "harga": 4500},
    {"dm": 17,  "harga": 5000},
    {"dm": 19,  "harga": 5500},
    {"dm": 28,  "harga": 7500},
    {"dm": 33,  "harga": 9500},
    {"dm": 36,  "harga": 10000},
    {"dm": 44,  "harga": 11000},
    {"dm": 50,  "harga": 15500},
    {"dm": 56,  "harga": 15500},
    {"dm": 59,  "harga": 16000},
    {"dm": 74,  "harga": 18000},
    {"dm": 85,  "harga": 22000},
    {"dm": 100, "harga": 25000},
    {"dm": 110, "harga": 29000},
    {"dm": 112, "harga": 29500},
    {"dm": 140, "harga": 37000},
    {"dm": 144, "harga": 38000},
    {"dm": 170, "harga": 44000},
    {"dm": 172, "harga": 44500},
    {"dm": 185, "harga": 47000},
    {"dm": 222, "harga": 57000},
    {"dm": 229, "harga": 60000},
    {"dm": 240, "harga": 62000},
    {"dm": 257, "harga": 66000},
    {"dm": 270, "harga": 74000},
    {"dm": 284, "harga": 75000},
    {"dm": 296, "harga": 76000},
    {"dm": 301, "harga": 81000},
    {"dm": 346, "harga": 86000},
]

FF_PRODUCTS = [
    {"dm": 5,   "harga": 1000},
    {"dm": 10,  "harga": 2000},
    {"dm": 15,  "harga": 3000},
    {"dm": 20,  "harga": 4000},
    {"dm": 25,  "harga": 5000},
    {"dm": 30,  "harga": 6000},
    {"dm": 40,  "harga": 7000},
    {"dm": 55,  "harga": 8000},
    {"dm": 70,  "harga": 9000},
    {"dm": 75,  "harga": 10000},
    {"dm": 80,  "harga": 11000},
    {"dm": 90,  "harga": 11500},
    {"dm": 100, "harga": 12000},
    {"dm": 120, "harga": 16000},
    {"dm": 130, "harga": 17000},
    {"dm": 140, "harga": 18000},
    {"dm": 145, "harga": 19000},
    {"dm": 150, "harga": 20000},
    {"dm": 160, "harga": 21500},
    {"dm": 170, "harga": 23000},
    {"dm": 180, "harga": 24500},
    {"dm": 190, "harga": 25000},
    {"dm": 200, "harga": 26000},
    {"dm": 210, "harga": 26500},
    {"dm": 250, "harga": 34000},
    {"dm": 260, "harga": 35000},
    {"dm": 280, "harga": 35500},
    {"dm": 300, "harga": 39000},
    {"dm": 355, "harga": 43000},
    {"dm": 360, "harga": 45500},
    {"dm": 375, "harga": 48000},
    {"dm": 405, "harga": 51000},
    {"dm": 425, "harga": 53000},
    {"dm": 475, "harga": 60000},
    {"dm": 500, "harga": 63000},
    {"dm": 510, "harga": 65000},
    {"dm": 545, "harga": 70000},
    {"dm": 565, "harga": 72000},
    {"dm": 635, "harga": 79000},
    {"dm": 790, "harga": 90000},
]

ROBUX_PRODUCTS = [
    {"category": "GAMEPASS", "name": "VIP + LUCK",                "robux": 445},
    {"category": "GAMEPASS", "name": "MUTATION",                   "robux": 295},
    {"category": "GAMEPASS", "name": "ADVANCED LUCK",              "robux": 525},
    {"category": "GAMEPASS", "name": "EXTRA LUCK",                 "robux": 245},
    {"category": "GAMEPASS", "name": "DOUBLE EXP",                 "robux": 195},
    {"category": "GAMEPASS", "name": "SELL ANYWHERE",              "robux": 315},
    {"category": "GAMEPASS", "name": "SMALL LUCK",                 "robux": 50},
    {"category": "GAMEPASS", "name": "HYPERBOATPACK",              "robux": 999},
    {"category": "CRATE",    "name": "VALENTINE CRATE 1X",         "robux": 249},
    {"category": "CRATE",    "name": "VALENTINE CRATE 5X",         "robux": 1245},
    {"category": "CRATE",    "name": "ELDERWOOD CRATE 1X",         "robux": 99},
    {"category": "CRATE",    "name": "ELDERWOOD CRATE 5X",         "robux": 495},
    {"category": "BOOST",    "name": "BOOST SERVER LUCK X2",       "robux": 99},
    {"category": "BOOST",    "name": "BOOST SERVER LUCK X8 3 JAM", "robux": 800},
    {"category": "BOOST",    "name": "BOOST X8 3 JAM",             "robux": 300},
    {"category": "BOOST",    "name": "BOOST X8 6 JAM",             "robux": 1300},
    {"category": "BOOST",    "name": "BOOST X8 12 JAM",            "robux": 1890},
    {"category": "BOOST",    "name": "BOOST X8 24 JAM",            "robux": 3100},
    {"category": "LIMITED",  "name": "DARK MATTER SCYTHE",         "robux": 999},
    {"category": "LIMITED",  "name": "KITTY GUITAR",               "robux": 899},
    {"category": "LIMITED",  "name": "VOIDCRAFT BOAT",             "robux": 549},
]

VILOG_BOOSTS = [
    {"nama": "X8 6 JAM",  "robux": 1300},
    {"nama": "X8 12 JAM", "robux": 1890},
    {"nama": "X8 24 JAM", "robux": 3100},
]

# ── SEED ─────────────────────────────────────────────────────────────────────

def seed():
    print("Inisialisasi database...")
    init_db()

    conn = get_conn()
    c = conn.cursor()

    # ML Products
    c.execute("SELECT COUNT(*) FROM ml_products")
    if c.fetchone()[0] == 0:
        for p in ML_PRODUCTS:
            c.execute("INSERT INTO ml_products (dm, harga) VALUES (?, ?)", (p["dm"], p["harga"]))
        print(f"  ✓ ML Products: {len(ML_PRODUCTS)} produk")
    else:
        print(f"  - ML Products: sudah ada, skip")

    # FF Products
    c.execute("SELECT COUNT(*) FROM ff_products")
    if c.fetchone()[0] == 0:
        for p in FF_PRODUCTS:
            c.execute("INSERT INTO ff_products (dm, harga) VALUES (?, ?)", (p["dm"], p["harga"]))
        print(f"  ✓ FF Products: {len(FF_PRODUCTS)} produk")
    else:
        print(f"  - FF Products: sudah ada, skip")

    # Robux Products
    c.execute("SELECT COUNT(*) FROM robux_products")
    if c.fetchone()[0] == 0:
        for p in ROBUX_PRODUCTS:
            c.execute(
                "INSERT INTO robux_products (category, name, robux) VALUES (?, ?, ?)",
                (p["category"], p["name"], p["robux"])
            )
        print(f"  ✓ Robux Products: {len(ROBUX_PRODUCTS)} produk")
    else:
        print(f"  - Robux Products: sudah ada, skip")

    # Vilog Boosts
    c.execute("SELECT COUNT(*) FROM vilog_boosts")
    if c.fetchone()[0] == 0:
        for b in VILOG_BOOSTS:
            c.execute(
                "INSERT INTO vilog_boosts (nama, robux) VALUES (?, ?)",
                (b["nama"], b["robux"])
            )
        print(f"  ✓ Vilog Boosts: {len(VILOG_BOOSTS)} paket")
    else:
        print(f"  - Vilog Boosts: sudah ada, skip")

    conn.commit()
    conn.close()
    print("\nSeed selesai!")

if __name__ == "__main__":
    seed()
