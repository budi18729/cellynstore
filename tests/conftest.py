"""Konfigurasi pytest: arahkan DB ke file sementara & sediakan discord stub.

Semua modul yang diuji di sini murni (SQLite / logika), tidak butuh koneksi
Discord. ticket_ui meng-import `discord`, jadi kita sediakan stub minimal.
"""
import os
import sys
import types
import tempfile

import pytest

# Pastikan root repo ada di sys.path (tests/ dijalankan dari root).
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def _install_discord_stub():
    """Stub minimal `discord` agar utils.ticket_ui bisa di-import tanpa discord.py."""
    if "discord" in sys.modules:
        return

    class _Embed:
        def __init__(self, *a, **k):
            self.kwargs = k
            self.fields = []
            self.thumbnail = None
            self.footer = None

        def add_field(self, name, value, inline=False):
            self.fields.append({"name": name, "value": value, "inline": inline})
            return self

        def set_thumbnail(self, url=None):
            self.thumbnail = url
            return self

        def set_footer(self, text=None, **k):
            self.footer = text
            return self

    discord = types.ModuleType("discord")
    discord.Embed = _Embed
    discord.abc = types.SimpleNamespace(User=object)
    discord.utils = types.SimpleNamespace(utcnow=lambda: None)
    sys.modules["discord"] = discord


_install_discord_stub()


@pytest.fixture()
def db(monkeypatch):
    """DB SQLite sementara yang sudah di-init (skema lengkap)."""
    import utils.db as realdb

    tmpdir = tempfile.mkdtemp()
    dbfile = os.path.join(tmpdir, "test.db")
    monkeypatch.setattr(realdb, "DB_FILE", dbfile)
    realdb.init_db()
    return realdb
