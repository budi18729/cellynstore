#!/bin/bash

# Color codes
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
GREEN='\033[0;32m'
PURPLE='\033[0;35m'
WHITE='\033[1;37m'
GRAY='\033[0;37m'
NC='\033[0m'

BOT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_FILE="$BOT_DIR/watchdog.log"
MAX_RETRIES=5
MANUAL_STOP=0

# Load .env
if [ -f "$BOT_DIR/.env" ]; then
    while IFS='=' read -r key value; do
        [[ "$key" =~ ^#.*$ || -z "$key" ]] && continue
        value=$(echo "$value" | tr -d '"' | tr -d "'")
        export "$key=$value"
    done < "$BOT_DIR/.env"
fi

STORE_NAME_ENV=$(grep -E "^STORE_NAME=" "$BOT_DIR/.env" 2>/dev/null | cut -d '=' -f2- | tr -d '"' | tr -d "'")
[ -z "$STORE_NAME_ENV" ] && STORE_NAME_ENV="Cellyn Store"

trap 'MANUAL_STOP=1; echo -e "\n${YELLOW}  Dihentikan manual.${NC}"; [ -n "$ADMIN_PID" ] && kill $ADMIN_PID 2>/dev/null; [ -n "$CF_PID" ] && kill $CF_PID 2>/dev/null; exit 0' SIGINT SIGTERM

log() {
    local level="$1"
    local msg="$2"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    case "$level" in
        INFO)  echo -e "${CYAN}  [${timestamp}] i  ${msg}${NC}" | tee -a "$LOG_FILE" ;;
        OK)    echo -e "${GREEN}  [${timestamp}] v  ${msg}${NC}" | tee -a "$LOG_FILE" ;;
        WARN)  echo -e "${YELLOW}  [${timestamp}] !  ${msg}${NC}" | tee -a "$LOG_FILE" ;;
        ERROR) echo -e "${RED}  [${timestamp}] x  ${msg}${NC}" | tee -a "$LOG_FILE" ;;
    esac
}

show_banner() {
    clear
    echo -e "${CYAN}"
    echo "  ███╗   ███╗██╗██████╗ ███╗   ███╗ █████╗ ███╗   ██╗"
    echo "  ████╗ ████║██║██╔══██╗████╗ ████║██╔══██╗████╗  ██║"
    echo "  ██╔████╔██║██║██║  ██║██╔████╔██║███████║██╔██╗ ██║"
    echo "  ██║╚██╔╝██║██║██║  ██║██║╚██╔╝██║██╔══██║██║╚██╗██║"
    echo "  ██║ ╚═╝ ██║██║██████╔╝██║ ╚═╝ ██║██║  ██║██║ ╚████║"
    echo "  ╚═╝     ╚═╝╚═╝╚═════╝ ╚═╝     ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝"
    echo -e "${NC}"
    echo -e "${PURPLE}  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${WHITE}      Discord Midman Bot  │  ${CYAN}${STORE_NAME_ENV}${WHITE}  │  Built by Equality${NC}"
    echo -e "${PURPLE}  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

check_update() {
    git -C "$BOT_DIR" fetch origin main --quiet 2>/dev/null
    LOCAL=$(git -C "$BOT_DIR" rev-parse HEAD 2>/dev/null)
    REMOTE=$(git -C "$BOT_DIR" rev-parse origin/main 2>/dev/null)

    if [ "$LOCAL" != "$REMOTE" ]; then
        echo -e "${YELLOW}  UPDATE TERSEDIA!${NC}"
        echo ""
        echo -e "${GRAY}  Changelog:${NC}"
        git -C "$BOT_DIR" log HEAD..origin/main --oneline --no-merges 2>/dev/null | sed 's/^/     /'
        echo ""
        echo -e "${CYAN}  Mengunduh update otomatis...${NC}"
        git -C "$BOT_DIR" pull origin main
        echo -e "${GREEN}  v Update selesai!${NC}"
    else
        echo -e "${GREEN}  v Bot sudah versi terbaru!${NC}"
    fi
    echo ""
}

trim_log() {
    if [ -f "$LOG_FILE" ] && [ $(wc -l < "$LOG_FILE") -gt 1000 ]; then
        tail -500 "$LOG_FILE" > "$LOG_FILE.tmp" && mv "$LOG_FILE.tmp" "$LOG_FILE"
    fi
}

# ── MAIN ──────────────────────────────────────────────────────────

show_banner
check_update

echo -e "${PURPLE}  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
log INFO "Auto-restart aktif — max retry: ${MAX_RETRIES}x"
echo -e "${PURPLE}  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# ── SEED ──────────────────────────────────────────────────────────
source "$BOT_DIR/venv/bin/activate"
python3 -c "from utils.db import init_db; init_db()" 2>/dev/null
ML_COUNT=$(python3 -c "from utils.db import get_conn; c=get_conn().cursor(); c.execute('SELECT COUNT(*) FROM ml_products'); print(c.fetchone()[0])" 2>/dev/null)
if [ "$ML_COUNT" = "0" ] || [ -z "$ML_COUNT" ]; then
    log WARN "Database produk kosong. Menjalankan seed.py..."
    python "$BOT_DIR/seed.py" >> "$BOT_DIR/seed.log" 2>&1
    log OK "Seed selesai."
fi

# ── ADMIN PANEL ───────────────────────────────────────────────────
log INFO "Memulai Admin Panel di port 5000..."
python "$BOT_DIR/admin.py" >> "$BOT_DIR/admin.log" 2>&1 &
ADMIN_PID=$!
log OK "Admin Panel berjalan (PID: $ADMIN_PID)"


# ── CLOUDFLARE TUNNEL ─────────────────────────────────────────────
if ! command -v cloudflared &> /dev/null; then
    log WARN "cloudflared tidak ditemukan. Menginstall..."
    pkg install -y cloudflared >> "$BOT_DIR/cloudflared.log" 2>&1
fi

if command -v cloudflared &> /dev/null; then
    log INFO "Memulai Cloudflare Tunnel..."
    cloudflared tunnel --url http://localhost:5000 >> "$BOT_DIR/cloudflared.log" 2>&1 &
    CF_PID=$!
    sleep 5
    CF_URL=$(grep -o 'https://[^ ]*trycloudflare.com' "$BOT_DIR/cloudflared.log" 2>/dev/null | tail -1)
    if [ -n "$CF_URL" ]; then
        log OK "Admin Panel: $CF_URL"
    else
        log WARN "Cloudflare Tunnel berjalan tapi URL belum tersedia. Cek cloudflared.log"
    fi
else
    log WARN "cloudflared tidak bisa diinstall. Admin Panel hanya via localhost."
fi

echo -e "${PURPLE}  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

retries=0

while true; do
    cd "$BOT_DIR"
    source "$BOT_DIR/venv/bin/activate"
    log INFO "Menjalankan bot... (percobaan ke-$((retries+1)))"

    python3 -c "from utils.db import init_db; init_db()"
    python main.py
    EXIT_CODE=$?

    [ $MANUAL_STOP -eq 1 ] && break

    trim_log

    if [ $EXIT_CODE -eq 0 ]; then
        retries=0
        log OK "Bot restart disengaja (exit 0), counter direset."
        # Restart admin panel agar kode terbaru aktif
        if [ -n "$ADMIN_PID" ] && kill -0 $ADMIN_PID 2>/dev/null; then
            kill $ADMIN_PID 2>/dev/null
            sleep 1
        fi
        log INFO "Restart Admin Panel..."
        python "$BOT_DIR/admin.py" >> "$BOT_DIR/admin.log" 2>&1 &
        ADMIN_PID=$!
        log OK "Admin Panel restart (PID: $ADMIN_PID)"
    else
        retries=$((retries + 1))
        log ERROR "Bot mati! (exit: $EXIT_CODE) — Percobaan $retries/$MAX_RETRIES"
    fi

    if [ $retries -ge $MAX_RETRIES ]; then
        log ERROR "Max retry tercapai! Butuh intervensi manual."
        break
    fi

    log WARN "Restart dalam 10 detik..."
    sleep 10

    log OK "Restart ke-$retries..."
done
