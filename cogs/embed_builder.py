"""
cogs/embed_builder.py
Diload di main.py seperti cog lainnya.
"""
import discord
from discord.ext import commands, tasks
from discord import app_commands
import sqlite3, json, os, datetime

DB_PATH = os.getenv("DB_PATH", "midman.db")
API     = "https://discord.com/api/v10"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def build_embed_payload(data: dict) -> dict:
    embed = {}
    if data.get("title"):       embed["title"] = data["title"]
    if data.get("url"):         embed["url"]   = data["url"]
    if data.get("description"): embed["description"] = data["description"]
    if data.get("color"):
        try: embed["color"] = int(str(data["color"]).lstrip("#"), 16)
        except: pass
    if data.get("timestamp"):
        ts = data["timestamp"]
        embed["timestamp"] = ts + ":00" if len(ts) == 16 else ts
    a = data.get("author", {})
    if a.get("name"):
        au = {"name": a["name"]}
        if a.get("url"):      au["url"]      = a["url"]
        if a.get("icon_url"): au["icon_url"]  = a["icon_url"]
        embed["author"] = au
    if data.get("thumbnail"): embed["thumbnail"] = {"url": data["thumbnail"]}
    if data.get("image"):     embed["image"]     = {"url": data["image"]}
    f = data.get("footer", {})
    if f.get("text"):
        fo = {"text": f["text"]}
        if f.get("icon_url"): fo["icon_url"] = f["icon_url"]
        embed["footer"] = fo
    fields = [{"name": x["name"], "value": x["value"], "inline": bool(x.get("inline", False))}
              for x in data.get("fields", []) if x.get("name") and x.get("value")]
    if fields: embed["fields"] = fields
    return embed

async def send_embed_rest(channel_id: str, embed_data: dict, content_msg: str = "") -> bool:
    import aiohttp
    token = os.getenv("TOKEN", "")
    headers = {"Authorization": f"Bot {token}", "Content-Type": "application/json"}
    payload = {"embeds": [build_embed_payload(embed_data)]}
    if content_msg:
        payload["content"] = content_msg
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{API}/channels/{channel_id}/messages",
                                    headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as r:
                return r.status in (200, 201)
    except Exception:
        return False


class EmbedBuilder(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.auto_send_loop.start()

    def cog_unload(self):
        self.auto_send_loop.cancel()

    # ── Background loop auto-send ──────────────────────────────
    @tasks.loop(minutes=1)
    async def auto_send_loop(self):
        now = datetime.datetime.now(datetime.timezone.utc)
        conn = get_db()
        tasks_due = conn.execute(
            "SELECT * FROM embed_messages WHERE auto_send=1 AND active=1 AND next_send IS NOT NULL"
        ).fetchall()
        conn.close()

        for task in tasks_due:
            try:
                next_send_str = task["next_send"]
                next_dt = datetime.datetime.fromisoformat(next_send_str)
                if next_dt.tzinfo is None:
                    next_dt = next_dt.replace(tzinfo=datetime.timezone.utc)
                if now < next_dt:
                    continue

                embed_data = json.loads(task["embed_json"])
                content_msg = task["content"] or ""
                ok = await send_embed_rest(task["channel_id"], embed_data, content_msg)

                if ok:
                    interval = task["interval_minutes"] or 60
                    scheduled_time = task["scheduled_time"]
                    if scheduled_time:
                        try:
                            h, m = map(int, scheduled_time.split(":"))
                            # scheduled_time disimpan sebagai WIB (UTC+7) → konversi ke UTC
                            wib = datetime.timezone(datetime.timedelta(hours=7))
                            now_wib = now.astimezone(wib)
                            nxt_wib = now_wib.replace(hour=h, minute=m, second=0, microsecond=0)
                            if nxt_wib <= now_wib:
                                nxt_wib += datetime.timedelta(days=1)
                            nxt = nxt_wib.astimezone(datetime.timezone.utc)
                        except Exception:
                            nxt = now + datetime.timedelta(minutes=interval)
                    else:
                        nxt = now + datetime.timedelta(minutes=interval)

                    conn2 = get_db()
                    conn2.execute(
                        "UPDATE embed_messages SET next_send=? WHERE id=?",
                        (nxt.isoformat(), task["id"])
                    )
                    conn2.commit()
                    conn2.close()
                    print(f"[EmbedBuilder] Auto-sent: {task['label']} → #{task['channel_id']}")
                else:
                    print(f"[EmbedBuilder] Gagal auto-send: {task['label']}")
            except Exception as e:
                print(f"[EmbedBuilder] Loop error: {e}")

    @auto_send_loop.before_loop
    async def before_loop(self):
        await self.bot.wait_until_ready()

    # ── Slash: list embed terkirim ──────────────────────────────
    @app_commands.command(name="embed_list", description="[Admin] List semua embed yang pernah dikirim via builder")
    @app_commands.checks.has_permissions(administrator=True)
    async def embed_list(self, interaction: discord.Interaction):
        conn = get_db()
        rows = conn.execute(
            "SELECT id, label, channel_id, message_id, sent_at, auto_send FROM embed_messages ORDER BY sent_at DESC LIMIT 20"
        ).fetchall()
        conn.close()

        if not rows:
            return await interaction.response.send_message("Belum ada embed yang dikirim via builder.", ephemeral=True)

        embed = discord.Embed(title="📋 Embed Terkirim", color=0x5865F2)
        for r in rows:
            ch = self.bot.get_channel(int(r["channel_id"]))
            ch_name = f"<#{r['channel_id']}>" if ch else r["channel_id"]
            auto = "🔄 Auto" if r["auto_send"] else "📨 Manual"
            embed.add_field(
                name=f"#{r['id']} — {r['label']}",
                value=f"Channel: {ch_name}\nMessage ID: `{r['message_id']}`\nDikirim: {r['sent_at'][:16]} | {auto}",
                inline=False
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ── Slash: delete embed terkirim ───────────────────────────
    @app_commands.command(name="embed_delete", description="[Admin] Hapus embed yang dikirim bot (dari Discord & DB)")
    @app_commands.describe(message_id="Message ID embed yang mau dihapus")
    @app_commands.checks.has_permissions(administrator=True)
    async def embed_delete(self, interaction: discord.Interaction, message_id: str):
        conn = get_db()
        row = conn.execute(
            "SELECT * FROM embed_messages WHERE message_id = ?", (message_id,)
        ).fetchone()

        if not row:
            conn.close()
            return await interaction.response.send_message("❌ Message ID tidak ditemukan di DB.", ephemeral=True)

        try:
            ch = self.bot.get_channel(int(row["channel_id"]))
            if ch:
                msg = await ch.fetch_message(int(message_id))
                await msg.delete()
        except Exception:
            pass

        conn.execute("DELETE FROM embed_messages WHERE message_id = ?", (message_id,))
        conn.commit()
        conn.close()

        await interaction.response.send_message(f"✅ Embed `{row['label']}` berhasil dihapus.", ephemeral=True)

    @embed_list.error
    @embed_delete.error
    async def admin_error(self, interaction: discord.Interaction, error):
        await interaction.response.send_message("❌ Kamu tidak punya izin.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(EmbedBuilder(bot))
