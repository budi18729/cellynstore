"""Self-check variabel environment saat startup.

Banyak nilai di utils/config.py dibaca dengan int(os.getenv(...)) TANPA default,
sehingga bila variabelnya kosong, bot crash dengan error yang membingungkan
(TypeError: int(None)). Modul ini memvalidasi .env lebih awal dan memberi pesan
yang jelas: error untuk variabel WAJIB, peringatan untuk yang opsional.

Murni (tanpa Discord) supaya gampang di-unit-test.
"""
import os

# Variabel yang WAJIB ada & non-kosong; bila tidak, bot tidak bisa jalan benar.
REQUIRED = [
    "TOKEN",
    "GUILD_ID",
    "ADMIN_ROLE_ID",
    "TICKET_CATEGORY_ID",
    "LOG_CHANNEL_ID",
    "TRANSCRIPT_CHANNEL_ID",
    "MIDMAN_CHANNEL_ID",
    "BACKUP_CHANNEL_ID",
    "ERROR_LOG_CHANNEL_ID",
    "SELFROLES_CHANNEL_ID",
    "ROBUX_CATALOG_CHANNEL_ID",
    "ML_CATALOG_CHANNEL_ID",
]

# Variabel yang sebaiknya diisi; bila kosong, fitur terkait mati diam-diam.
RECOMMENDED = {
    "TESTIMONI_CHANNEL_ID": "publikasi rating/ulasan & fallback prompt rating",
    "LAINNYA_AUTOREPLY_CHANNEL_ID": "auto-reply kata kunci layanan lainnya",
    "WARRANTY_CHANNEL_ID": "panel klaim garansi",
    "DAILY_REPORT_CHANNEL_ID": "laporan harian otomatis",
    "DANA_NUMBER": "info pembayaran DANA",
    "BCA_NUMBER": "info pembayaran BCA",
}

# ID numerik yang, bila diisi, harus berupa angka.
NUMERIC = [
    "GUILD_ID", "ADMIN_ROLE_ID", "TICKET_CATEGORY_ID", "LOG_CHANNEL_ID",
    "TRANSCRIPT_CHANNEL_ID", "MIDMAN_CHANNEL_ID", "BACKUP_CHANNEL_ID",
    "ERROR_LOG_CHANNEL_ID", "SELFROLES_CHANNEL_ID", "ROBUX_CATALOG_CHANNEL_ID",
    "ML_CATALOG_CHANNEL_ID", "TESTIMONI_CHANNEL_ID", "LAINNYA_AUTOREPLY_CHANNEL_ID",
    "VILOG_CHANNEL_ID", "VILOG_CATALOG_CHANNEL_ID", "INVITE_REWARD_CHANNEL_ID",
    "REVIEWER_BADGE_ROLE_ID", "REVIEWER_BADGE_THRESHOLD", "WARRANTY_CHANNEL_ID",
    "DAILY_REPORT_CHANNEL_ID",
]


def check_env(getenv=os.getenv) -> dict:
    """Periksa environment. Return dict:
        {"missing_required":[...], "missing_recommended":[(name,desc)...],
         "invalid_numeric":[...], "ok":bool}
    `getenv` bisa diganti untuk testing.
    """
    def _empty(name):
        v = getenv(name)
        return v is None or str(v).strip() == ""

    missing_required = [n for n in REQUIRED if _empty(n)]
    missing_recommended = [(n, d) for n, d in RECOMMENDED.items() if _empty(n)]

    invalid_numeric = []
    for n in NUMERIC:
        v = getenv(n)
        if v is None or str(v).strip() == "":
            continue
        try:
            int(str(v).strip())
        except (TypeError, ValueError):
            invalid_numeric.append(n)

    ok = not missing_required and not invalid_numeric
    return {
        "missing_required": missing_required,
        "missing_recommended": missing_recommended,
        "invalid_numeric": invalid_numeric,
        "ok": ok,
    }


def format_report(result: dict) -> str:
    """Bangun pesan laporan ramah-baca dari hasil check_env."""
    lines = []
    if result["missing_required"]:
        lines.append("[ENV] ❌ Variabel WAJIB belum diisi: "
                     + ", ".join(result["missing_required"]))
    if result["invalid_numeric"]:
        lines.append("[ENV] ❌ Variabel berikut harus berupa angka (ID): "
                     + ", ".join(result["invalid_numeric"]))
    for name, desc in result["missing_recommended"]:
        lines.append(f"[ENV] ⚠️  {name} kosong — fitur '{desc}' tidak aktif.")
    if result["ok"] and not result["missing_recommended"]:
        lines.append("[ENV] ✅ Semua variabel environment terisi.")
    elif result["ok"]:
        lines.append("[ENV] ✅ Variabel wajib lengkap (ada peringatan opsional di atas).")
    return "\n".join(lines)


def run_startup_check(getenv=os.getenv, printer=print) -> bool:
    """Jalankan check & cetak laporan. Return True bila variabel wajib lengkap."""
    result = check_env(getenv)
    printer(format_report(result))
    return result["ok"]
