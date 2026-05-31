import discord
from discord.ext import commands
import asyncio
from dotenv import load_dotenv
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import urllib.request

load_dotenv()

TOKEN = os.getenv("TOKEN")
ERROR_LOG_CHANNEL_ID = int(os.getenv("ERROR_LOG_CHANNEL_ID", 0))
BOT_DIR = os.path.dirname(os.path.abspath(__file__))

COGS = [
    "cogs.midman", "cogs.selfroles", "cogs.robux", "cogs.ml",
    "cogs.jualbeli", "cogs.reviews", "cogs.giveaway", "cogs.welcome",
    "cogs.broadcast", "cogs.auto_react", "cogs.server_stats", "cogs.lainnya",
    "cogs.orders", "cogs.qr", "cogs.poll", "cogs.embed_builder",
    "cogs.autoposter", "cogs.gp", "cogs.afk", "cogs.relay",
    "cogs.vilog", "cogs.store_status", "cogs.free_game_notifier", "cogs.mobile_game_notifier", "cogs.genshin_notifier", "cogs.top_spender", "cogs.warranty"
]


def create_bot():
    intents = discord.Intents.default()
    intents.message_content = True
    intents.members = True
    return commands.Bot(command_prefix="!", intents=intents)


def init_database():
    try:
        from utils.db import init_db
        init_db()
        print("[INIT] Database initialized.")
    except Exception as e:
        print(f"[INIT] init_db error: {e}")


def start_admin_panel():
    try:
        admin_log = open(os.path.join(BOT_DIR, "admin.log"), "a")
        subprocess.Popen(
            [sys.executable, os.path.join(BOT_DIR, "admin.py")],
            stdout=admin_log,
            stderr=admin_log
        )
        print("[ADMIN] Admin panel started.")
    except Exception as e:
        print(f"[ADMIN] Failed to start admin panel: {e}")


def install_cloudflared():
    try:
        cf_path = os.path.join(BOT_DIR, "cloudflared")
        if os.path.exists(cf_path):
            return cf_path
        print("[CF] Installing cloudflared...")
        arch = subprocess.check_output(["uname", "-m"]).decode().strip()
        cf_bin = "cloudflared-linux-amd64" if "x86_64" in arch else "cloudflared-linux-arm64"
        url = f"https://github.com/cloudflare/cloudflared/releases/latest/download/{cf_bin}"

        # Unduh tanpa bergantung pada 'wget' (tidak selalu tersedia, mis. Endercloud).
        # Utamakan urllib bawaan Python; fallback ke curl bila ada.
        downloaded = False
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=120) as resp, open(cf_path, "wb") as out:
                shutil.copyfileobj(resp, out)
            downloaded = True
        except Exception as e:
            print(f"[CF] urllib download gagal ({e}); coba curl...")
            if shutil.which("curl"):
                subprocess.run(["curl", "-fsSL", "-o", cf_path, url], check=True)
                downloaded = True
            elif shutil.which("wget"):
                subprocess.run(["wget", "-q", "-O", cf_path, url], check=True)
                downloaded = True

        if not downloaded:
            print("[CF] Tidak ada metode unduh tersedia (urllib/curl/wget).")
            return None

        os.chmod(cf_path, 0o755)
        print("[CF] cloudflared installed.")
        return cf_path
    except Exception as e:
        print(f"[CF] Failed to install cloudflared: {e}")
        return None


def start_cloudflared():
    try:
        cf_path = install_cloudflared()
        if not cf_path:
            return
        cf_log_path = os.path.join(BOT_DIR, "cloudflared.log")
        cf_log = open(cf_log_path, "a")
        subprocess.Popen(
            [cf_path, "tunnel", "--url", "http://localhost:5000"],
            stdout=cf_log,
            stderr=cf_log
        )
        print("[CF] Cloudflare tunnel started.")
    except Exception as e:
        print(f"[CF] Failed to start cloudflared: {e}")


async def setup_and_run(bot):
    """Setup event handlers, load cogs, dan jalankan bot."""

    @bot.event
    async def on_ready():
        print(f"[BOT] Login sebagai {bot.user}")
        await asyncio.sleep(8)
        try:
            from utils.config import GUILD_ID
            guild = discord.Object(id=GUILD_ID)
            bot.tree.copy_global_to(guild=guild)
            synced = await bot.tree.sync(guild=guild)
            print(f"[BOT] Synced {len(synced)} slash command(s) to guild {GUILD_ID}")
            bot.tree.clear_commands(guild=None)
            await bot.tree.sync()
        except Exception as e:
            print(f"[BOT] Sync error: {e}")

        if not ERROR_LOG_CHANNEL_ID:
            return
        ch = bot.get_channel(ERROR_LOG_CHANNEL_ID)
        if not ch:
            return

        cf_url = None
        cf_log = os.path.join(BOT_DIR, "cloudflared.log")
        if os.path.exists(cf_log):
            try:
                with open(cf_log, "r", errors="ignore") as f:
                    matches = re.findall(r'https://\S+trycloudflare\.com', f.read())
                    if matches:
                        cf_url = matches[-1]
            except Exception:
                pass

        if cf_url:
            embed = discord.Embed(
                title="🌐 Admin Panel Online Password Cellyn123",
                description=f"Admin panel dapat diakses di:\n**{cf_url}**",
                color=0x7c6aff
            )
            embed.set_footer(text="URL ini berubah setiap bot restart.")
        else:
            embed = discord.Embed(
                title="⚠️ Admin Panel",
                description="Bot online tapi URL Cloudflare Tunnel tidak ditemukan.\nCek `cloudflared.log` di server.",
                color=0xFFA500
            )
        await ch.send(embed=embed)

    async with bot:
        for cog in COGS:
            try:
                await bot.load_extension(cog)
            except Exception as e:
                print(f"[COG] Gagal load {cog}: {e}")
        await bot.start(TOKEN)


async def main():
    # Self-check .env lebih awal: error jelas bila variabel wajib kosong,
    # peringatan untuk variabel opsional yang mati diam-diam.
    from utils.env_check import run_startup_check
    if not run_startup_check():
        print("[ENV] Variabel wajib belum lengkap. Perbaiki .env lalu jalankan ulang.")
        return

    init_database()

    threading.Thread(target=start_admin_panel, daemon=True).start()
    threading.Thread(target=start_cloudflared, daemon=True).start()

    time.sleep(3)

    retry_delay = 60   # detik awal sebelum retry
    max_delay = 600    # maksimal 10 menit

    while True:
        bot = create_bot()
        try:
            await setup_and_run(bot)
            # Kalau bot.start() selesai normal (misal bot.close() dipanggil)
            print("[BOT] Bot disconnected normally. Stopping.")
            break

        except discord.errors.HTTPException as e:
            if e.status == 429:
                print(f"[RATE LIMIT] Kena 429! Menunggu {retry_delay} detik sebelum retry...")
                await asyncio.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, max_delay)
            else:
                print(f"[HTTP ERROR] {e} — retry dalam 30 detik...")
                await asyncio.sleep(30)

        except discord.errors.LoginFailure:
            print("[ERROR] Token tidak valid! Cek file .env kamu.")
            break

        except Exception as e:
            print(f"[ERROR] Unexpected error: {e} — retry dalam 30 detik...")
            await asyncio.sleep(30)

        else:
            retry_delay = 60  # reset delay kalau berhasil


asyncio.run(main())
