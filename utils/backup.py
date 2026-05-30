import discord
import os
import datetime

DB_FILE = "midman.db"
BACKUP_LABEL = "MIDMAN-BACKUP"

async def do_backup(bot, channel_id):
    channel = bot.get_channel(channel_id)
    if not channel:
        print("[BACKUP] Channel tidak ditemukan.")
        return
    if not os.path.exists(DB_FILE):
        print("[BACKUP] File database tidak ditemukan.")
        return
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%d/%m/%Y %H:%M UTC")
    await channel.send(
        content=f"MIDMAN-BACKUP\n{now}\n{DB_FILE}",
        files=[discord.File(DB_FILE)]
    )
    print(f"[BACKUP] Backup berhasil dikirim ke channel {channel_id}.")

async def do_restore(bot, channel_id):
    if os.path.exists(DB_FILE):
        return
    channel = bot.get_channel(channel_id)
    if not channel:
        print("[RESTORE] Channel tidak ditemukan.")
        return
    async for msg in channel.history(limit=100):
        if BACKUP_LABEL not in (msg.content or ""):
            continue
        for attachment in msg.attachments:
            if attachment.filename == DB_FILE:
                await attachment.save(DB_FILE)
                print(f"[RESTORE] {DB_FILE} berhasil di-restore dari backup.")
                return
    print("[RESTORE] Tidak ada backup ditemukan.")
