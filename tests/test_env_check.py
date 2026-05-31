"""Unit test untuk utils/env_check.py (self-check .env startup)."""
import sys
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from utils import env_check


def _fake_getenv(values: dict):
    return lambda name, default=None: values.get(name, default)


def _full_env():
    env = {n: "123" for n in env_check.REQUIRED}
    env["TOKEN"] = "abc.def.ghi"
    for n in env_check.RECOMMENDED:
        env[n] = "1"
    return env


def test_all_present_ok():
    res = env_check.check_env(_fake_getenv(_full_env()))
    assert res["ok"] is True
    assert res["missing_required"] == []
    assert res["missing_recommended"] == []
    assert res["invalid_numeric"] == []


def test_missing_required_fails():
    env = _full_env()
    del env["TOKEN"]
    del env["GUILD_ID"]
    res = env_check.check_env(_fake_getenv(env))
    assert res["ok"] is False
    assert "TOKEN" in res["missing_required"]
    assert "GUILD_ID" in res["missing_required"]


def test_empty_string_counts_as_missing():
    env = _full_env()
    env["ADMIN_ROLE_ID"] = "   "
    res = env_check.check_env(_fake_getenv(env))
    assert res["ok"] is False
    assert "ADMIN_ROLE_ID" in res["missing_required"]


def test_missing_recommended_warns_but_ok():
    env = _full_env()
    del env["TESTIMONI_CHANNEL_ID"]
    res = env_check.check_env(_fake_getenv(env))
    assert res["ok"] is True  # recommended tidak bikin gagal
    names = [n for n, _ in res["missing_recommended"]]
    assert "TESTIMONI_CHANNEL_ID" in names


def test_invalid_numeric_fails():
    env = _full_env()
    env["GUILD_ID"] = "not-a-number"
    res = env_check.check_env(_fake_getenv(env))
    assert res["ok"] is False
    assert "GUILD_ID" in res["invalid_numeric"]


def test_run_startup_check_returns_bool_and_prints():
    out = []
    ok = env_check.run_startup_check(_fake_getenv(_full_env()), printer=out.append)
    assert ok is True
    assert out and "ENV" in out[0]

    out2 = []
    env = _full_env(); del env["TOKEN"]
    ok2 = env_check.run_startup_check(_fake_getenv(env), printer=out2.append)
    assert ok2 is False
    assert "TOKEN" in out2[0]
