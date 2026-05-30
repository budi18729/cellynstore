import time
import discord
import datetime
import asyncio
from discord.ext import commands, tasks
from utils.config import ADMIN_ROLE_ID, LOG_CHANNEL_ID, STORE_NAME, TICKET_CATEGORY_ID, TRANSCRIPT_CHANNEL_ID, GUILD_ID
from utils.counter import next_ticket_number
from utils.transcript import generate as generate_transcript
from utils.db import get_conn
from utils.store_hours import is_store_open

THUMBNAIL = "https://i.imgur.com/CWtUCzj.png"

# ─── DB helpers ──────────────────────────────────────────────────────────────

def _migrate_db():
    conn = get_conn()
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS games (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT NOT NULL UNIQUE,
        name TEXT NOT NULL,
        color INTEGER DEFAULT 3407872,
        needs_server INTEGER DEFAULT 0,
        id_label TEXT DEFAULT 'Player ID',
        active INTEGER DEFAULT 1
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS game_products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        game_code TEXT NOT NULL,
        label TEXT NOT NULL,
        dm INTEGER NOT NULL DEFAULT 0,
        harga INTEGER NOT NULL,
        active INTEGER DEFAULT 1
    )""")
    conn.commit()
    if c.execute("SELECT COUNT(*) FROM games").fetchone()[0] == 0:
        c.executemany(
            "INSERT OR IGNORE INTO games (code, name, color, needs_server, id_label) VALUES (?,?,?,?,?)",
            [
                ("ML",  "Mobile Legends",       0x3498DB, 1, "ID Mobile Legends"),
                ("WDP", "WDP (Mobile Legends)", 0x3498DB, 1, "ID Mobile Legends"),
                ("FF",  "Free Fire",            0xFF6B35, 0, "Player ID Free Fire"),
            ]
        )
        conn.commit()
    if c.execute("SELECT COUNT(*) FROM game_products WHERE game_code='ML'").fetchone()[0] == 0:
        try:
            rows = c.execute("SELECT dm, harga FROM ml_products ORDER BY dm").fetchall()
            for r in rows:
                c.execute("INSERT INTO game_products (game_code, label, dm, harga) VALUES (?,?,?,?)",
                          ("ML", f"{r['dm']} Diamond", r["dm"], r["harga"]))
            conn.commit()
        except Exception as e:
            print(f"[ML] Migrasi ml_products: {e}")
    if c.execute("SELECT COUNT(*) FROM game_products WHERE game_code='FF'").fetchone()[0] == 0:
        try:
            rows = c.execute("SELECT dm, harga FROM ff_products ORDER BY dm").fetchall()
            for r in rows:
                c.execute("INSERT INTO game_products (game_code, label, dm, harga) VALUES (?,?,?,?)",
                          ("FF", f"{r['dm']} Diamond", r["dm"], r["harga"]))
            conn.commit()
        except Exception as e:
            print(f"[ML] Migrasi ff_products: {e}")
    if c.execute("SELECT COUNT(*) FROM game_products WHERE game_code='WDP'").fetchone()[0] == 0:
        try:
            rows = c.execute("SELECT qty, label, harga FROM wdp_products ORDER BY qty").fetchall()
            for r in rows:
                c.execute("INSERT INTO game_products (game_code, label, dm, harga) VALUES (?,?,?,?)",
                          ("WDP", r["label"], r["qty"], r["harga"]))
            conn.commit()
        except Exception as e:
            print(f"[ML] Migrasi wdp_products: {e}")
    conn.close()


def _load_games():
    conn = get_conn()
    rows = conn.execute(
        "SELECT code, name, color, needs_server, id_label FROM games WHERE active=1 ORDER BY id"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def _load_products(game_code):
    conn = get_conn()
    rows = conn.execute(
        "SELECT id, label, dm, harga FROM game_products WHERE game_code=? AND active=1 ORDER BY dm, id",
        (game_code,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def _get_game(code):
    conn = get_conn()
    row = conn.execute(
        "SELECT code, name, color, needs_server, id_label FROM games WHERE code=?", (code,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


# ─── ML Ticket DB ─────────────────────────────────────────────────────────────

def load_ml_tickets():
    conn = get_conn()
    c = conn.cursor()
    try:
        c.execute("ALTER TABLE ml_tickets ADD COLUMN item_label TEXT")
        conn.commit()
    except Exception:
        pass
    c.execute("SELECT * FROM ml_tickets")
    rows = c.fetchall()
    conn.close()
    tickets = {}
    for row in rows:
        tickets[row["channel_id"]] = {
            "channel_id": row["channel_id"],
            "user_id": row["user_id"],
            "id_ml": row["id_ml"],
            "server_id": row["server_id"],
            "dm": row["dm"],
            "harga": row["harga"],
            "opened_at": row["opened_at"],
            "last_activity": row["opened_at"],
            "game": row["game"] if row["game"] else "ML",
            "warned": bool(row["warned"]) if row["warned"] is not None else False,
            "item_label": (row["item_label"] if "item_label" in row.keys() and row["item_label"] else f"{row['dm']} Diamond"),
        }
    return tickets


def save_ml_ticket(ticket):
    conn = get_conn()
    c = conn.cursor()
    try:
        c.execute("ALTER TABLE ml_tickets ADD COLUMN item_label TEXT")
        conn.commit()
    except Exception:
        pass
    c.execute("""
        INSERT OR REPLACE INTO ml_tickets
        (channel_id, user_id, id_ml, server_id, dm, harga, opened_at, game, warned, item_label)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        ticket["channel_id"], ticket["user_id"], ticket["id_ml"], ticket["server_id"],
        ticket["dm"], ticket["harga"], ticket["opened_at"], ticket.get("game", "ML"),
        1 if ticket.get("warned") else 0,
        ticket.get("item_label", f"{ticket['dm']} Diamond"),
    ))
    conn.commit()
    conn.close()


def delete_ml_ticket(channel_id):
    conn = get_conn()
    conn.execute("DELETE FROM ml_tickets WHERE channel_id = ?", (channel_id,))
    conn.commit()
    conn.close()


# ─── Views & Modals ───────────────────────────────────────────────────────────

class GameFormModal(discord.ui.Modal):
    player_id = discord.ui.TextInput(
        label="Player ID", placeholder="Masukkan ID kamu", required=True, max_length=30
    )
    server_id_input = discord.ui.TextInput(
        label="Server ID", placeholder="Contoh: 1234", required=False, max_length=10
    )

    def __init__(self, game: dict, product: dict):
        super().__init__(title=f"Topup {game['name']}")
        self.game = game
        self.product = product
        self.player_id.label = game.get("id_label", "Player ID")
        self.player_id.placeholder = f"Masukkan {game.get('id_label', 'Player ID')}"
        if not game.get("needs_server"):
            self.remove_item(self.server_id_input)

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        user = interaction.user
        game = self.game
        product = self.product
        cog = interaction.client.cogs.get("MLStore")
        for ch_id, t in cog.active_tickets.items():
            if t["user_id"] == user.id:
                existing = guild.get_channel(ch_id)
                if existing:
                    await interaction.response.send_message(
                        f"Kamu masih punya tiket aktif di {existing.mention}!", ephemeral=True
                    )
                    return
        admin_role = guild.get_role(ADMIN_ROLE_ID)
        category = guild.get_channel(TICKET_CATEGORY_ID)
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        }
        if admin_role:
            overwrites[admin_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
        game_slug = game["code"].lower().replace(" ", "")
        channel = await guild.create_text_channel(
            name=f"{game_slug}-{user.name}", category=category, overwrites=overwrites
        )
        server_val = self.server_id_input.value.strip() if game.get("needs_server") else "-"
        ticket = {
            "channel_id": channel.id, "user_id": user.id,
            "id_ml": self.player_id.value.strip(), "server_id": server_val,
            "dm": product["dm"], "item_label": product["label"], "harga": product["harga"],
            "opened_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "last_activity": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "game": game["code"],
        }
        cog.active_tickets[channel.id] = ticket
        save_ml_ticket(ticket)
        color = game.get("color", 0x3498DB)
        embed = discord.Embed(
            title=f"TOPUP {game['name'].upper()} — {STORE_NAME}",
            color=color,
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        id_label = game.get("id_label", "Player ID")
        info = (
            f"Halo, {user.mention}! Tiket topup kamu sudah dibuat.\n"
            f"──────────────────────────────\n"
            f"Member       : {user.mention}\n"
            f"{id_label:<13}: `{self.player_id.value.strip()}`\n"
        )
        if game.get("needs_server") and server_val != "-":
            info += f"Server ID    : `{server_val}`\n"
        info += (
            f"Item         : {product['label']}\n"
            f"Total        : Rp {product['harga']:,}\n"
            f"Metode       : QRIS\n"
            f"Status       : Menunggu proses\n"
            f"──────────────────────────────\n"
            f"**!mlselesai** — konfirmasi topup selesai\n"
            f"**!mlbatal [alasan]** — batalkan tiket\n"
            f"──────────────────────────────\n"
            f"Tiket yang tidak aktif selama 2 jam akan otomatis ditutup."
        )
        embed.add_field(name="\u200b", value=info, inline=False)
        embed.set_footer(text=STORE_NAME)
        if admin_role:
            await channel.send(content=admin_role.mention, embed=embed)
        else:
            await channel.send(embed=embed)
        await interaction.response.send_message(
            f"Tiket berhasil dibuat di {channel.mention}!", ephemeral=True
        )


class MLConfirmView(discord.ui.View):
    """Ditampilkan setelah member pilih produk — berisi info layanan + tombol Lanjutkan/Batal."""
    def __init__(self, game: dict, product: dict):
        super().__init__(timeout=120)
        self.game = game
        self.product = product

    @discord.ui.button(label="✅ Lanjutkan", style=discord.ButtonStyle.success, custom_id="ml_confirm_lanjut")
    async def lanjutkan(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(GameFormModal(game=self.game, product=self.product))

    @discord.ui.button(label="❌ Batal", style=discord.ButtonStyle.danger, custom_id="ml_confirm_batal")
    async def batal(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="Order dibatalkan.", embed=None, view=None)


class ProductSelect(discord.ui.Select):
    def __init__(self, game: dict):
        self.game = game
        products = _load_products(game["code"])
        options = [
            discord.SelectOption(
                label=p["label"][:100], description=f"Rp {p['harga']:,}", value=str(p["id"])
            ) for p in products[:25]
        ] or [discord.SelectOption(label="Tidak ada produk aktif", value="none")]
        super().__init__(
            placeholder=f"Pilih produk {game['name']}...",
            options=options,
            custom_id=f"ml_product_{game['code']}"
        )

    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "none":
            await interaction.response.send_message("Tidak ada produk tersedia.", ephemeral=True)
            return
        pid = int(self.values[0])
        conn = get_conn()
        row = conn.execute(
            "SELECT id, label, dm, harga FROM game_products WHERE id=? AND active=1", (pid,)
        ).fetchone()
        conn.close()
        if not row:
            await interaction.response.send_message("Produk tidak ditemukan.", ephemeral=True)
            return
        product = dict(row)
        from utils.service_info import get_service_info, build_info_embed
        info = get_service_info("ml")
        color = self.game.get("color", 0x3498DB)
        has_info = any([info["description"], info["terms"], info["payment_info"]])
        if has_info:
            embed = build_info_embed(f"Topup {self.game['name']}", info, color)
            embed.add_field(
                name="🛒 Produk Dipilih",
                value=f"**{product['label']}** — Rp {product['harga']:,}",
                inline=False
            )
            view = MLConfirmView(game=self.game, product=product)
            await interaction.response.edit_message(content=None, embed=embed, view=view)
        else:
            await interaction.response.send_modal(GameFormModal(game=self.game, product=product))


class GameSelect(discord.ui.Select):
    def __init__(self):
        games = _load_games()
        options = [
            discord.SelectOption(label=g["name"], value=g["code"], description=f"Topup {g['name']}")
            for g in games[:25]
        ] or [discord.SelectOption(label="Tidak ada game aktif", value="none")]
        super().__init__(
            placeholder="Pilih game untuk topup...", options=options, custom_id="ml_game_select"
        )

    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "none":
            await interaction.response.send_message("Tidak ada game tersedia.", ephemeral=True)
            return
        game = _get_game(self.values[0])
        if not game:
            await interaction.response.send_message("Game tidak ditemukan.", ephemeral=True)
            return
        view = discord.ui.View(timeout=60)
        view.add_item(ProductSelect(game))
        await interaction.response.send_message(
            f"Pilih produk **{game['name']}**:", view=view, ephemeral=True
        )


class MLBuyView(discord.ui.View):
    def __init__(self, store_open: bool | None = None):
        super().__init__(timeout=None)
        self.add_item(GameSelect())
        store_open = is_store_open() if store_open is None else store_open
        if not store_open:
            for child in self.children:
                child.disabled = True


# ─── Cog ─────────────────────────────────────────────────────────────────────

class MLStore(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        _migrate_db()
        self.active_tickets = load_ml_tickets()
        self.catalog_message_id = None
        self.auto_close_task.start()

    def cog_unload(self):
        self.auto_close_task.cancel()

    @tasks.loop(minutes=10)
    async def auto_close_task(self):
        now = datetime.datetime.now(datetime.timezone.utc)
        guild = self.bot.get_guild(GUILD_ID)
        if not guild:
            return
        for ch_id, ticket in list(self.active_tickets.items()):
            last = ticket.get("last_activity") or ticket.get("opened_at")
            if not last:
                continue
            last_dt = datetime.datetime.fromisoformat(last)
            if last_dt.tzinfo is None:
                last_dt = last_dt.replace(tzinfo=datetime.timezone.utc)
            elapsed = (now - last_dt).total_seconds()
            channel = guild.get_channel(ch_id)
            if elapsed >= 7200:
                delete_ml_ticket(ch_id)
                self.active_tickets.pop(ch_id, None)
                if channel:
                    try:
                        await channel.send(
                            "Tiket ini otomatis ditutup karena tidak ada aktivitas selama 2 jam. "
                            "Transaksi dianggap batal. Channel akan dihapus dalam 10 detik."
                        )
                        await asyncio.sleep(10)
                        await channel.delete()
                    except Exception:
                        pass
            elif elapsed >= 3600 and not ticket.get("warned"):
                if channel:
                    try:
                        old_warn_id = ticket.get("warn_message_id")
                        if old_warn_id:
                            try:
                                old_msg = await channel.fetch_message(old_warn_id)
                                await old_msg.delete()
                            except Exception:
                                pass
                        warn_embed = discord.Embed(title="PERINGATAN TIKET", color=0xFFA500)
                        warn_embed.add_field(name="\u200b", value=(
                            "Tiket tidak ada aktivitas selama **1 jam**.\n\n"
                            "Segera ketik `!mlselesai` jika selesai, atau `!mlbatal` jika dibatalkan.\n\n"
                            "Tiket akan otomatis ditutup dalam **1 jam lagi** (<t:" + str(int(time.time()) + 3600) + ":R>)."
                        ), inline=False)
                        warn_embed.set_footer(text=STORE_NAME)
                        _user = guild.get_member(ticket["user_id"])
                        _mn = _user.mention if _user else ""
                        warn_msg = await channel.send(content=_mn, embed=warn_embed)
                        ticket["warn_message_id"] = warn_msg.id
                    except Exception:
                        pass
                ticket["warned"] = True
                save_ml_ticket(ticket)

    @auto_close_task.before_loop
    async def before_auto_close(self):
        await self.bot.wait_until_ready()

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        if message.channel.id in self.active_tickets:
            self.active_tickets[message.channel.id]["last_activity"] = (
                datetime.datetime.now(datetime.timezone.utc).isoformat()
            )
            save_ml_ticket(self.active_tickets[message.channel.id])

    @commands.command(name="mlcatalog")
    async def mlcatalog(self, ctx):
        if not any(r.id == ADMIN_ROLE_ID for r in ctx.author.roles):
            return
        await ctx.message.delete()
        from utils.config import ML_CATALOG_CHANNEL_ID
        ch = ctx.guild.get_channel(ML_CATALOG_CHANNEL_ID)
        if not ch:
            await ctx.send("Channel ML catalog tidak ditemukan!", delete_after=5)
            return
        games = _load_games()
        game_list = "\n".join(f"• **{g['name']}**" for g in games) or "Belum ada game aktif."
        embed = discord.Embed(
            title="TOPUP DIAMOND GAME",
            description=(
                f"Sekarang tersedia di **{STORE_NAME}**\n"
                f"Topup diamond dengan harga terjangkau, proses cepat, amanah dan transparan!\n\n"
                f"**Game tersedia:**\n{game_list}\n\n"
                f"Pilih game di dropdown di bawah untuk melihat produk dan melakukan pemesanan.\n\n"
                f"Metode Pembayaran: **QRIS**"
            ),
            color=0x3498DB
        )
        embed.set_footer(text=STORE_NAME)
        if self.catalog_message_id:
            try:
                msg = await ch.fetch_message(self.catalog_message_id)
                await msg.edit(embed=embed, view=MLBuyView(store_open=is_store_open()))
                await ctx.send(f"Catalog ML diperbarui di {ch.mention}", delete_after=5)
                return
            except Exception:
                pass
        async for msg in ch.history(limit=20):
            if msg.author == ctx.guild.me:
                try:
                    await msg.delete()
                except Exception:
                    pass
        sent = await ch.send(embed=embed, view=MLBuyView(store_open=is_store_open()))
        self.catalog_message_id = sent.id
        await ctx.send(f"Catalog ML dikirim ke {ch.mention}", delete_after=5)

    async def refresh_catalog(self):
        """Refresh view catalog ML (enable/disable tombol) based on store open/close."""
        guild = self.bot.get_guild(GUILD_ID)
        if not guild:
            return
        from utils.config import ML_CATALOG_CHANNEL_ID
        ch = guild.get_channel(ML_CATALOG_CHANNEL_ID)
        if not ch:
            return
        if not self.catalog_message_id:
            # Try to find the last bot message in the catalog channel.
            async for msg in ch.history(limit=20):
                if msg.author == guild.me and msg.embeds:
                    self.catalog_message_id = msg.id
                    break
        if not self.catalog_message_id:
            return
        try:
            msg = await ch.fetch_message(self.catalog_message_id)
        except Exception:
            return
        games = _load_games()
        game_list = "\n".join(f"• **{g['name']}**" for g in games) or "Belum ada game aktif."
        embed = discord.Embed(
            title="TOPUP DIAMOND GAME",
            description=(
                f"Sekarang tersedia di **{STORE_NAME}**\n"
                f"Topup diamond dengan harga terjangkau, proses cepat, amanah dan transparan!\n\n"
                f"**Game tersedia:**\n{game_list}\n\n"
                f"Pilih game di dropdown di bawah untuk melihat produk dan melakukan pemesanan.\n\n"
                f"Metode Pembayaran: **QRIS**"
            ),
            color=0x3498DB
        )
        embed.set_footer(text=STORE_NAME)
        await msg.edit(embed=embed, view=MLBuyView(store_open=is_store_open()))

    @commands.command(name="mlselesai")
    async def mlselesai(self, ctx):
        if not any(r.id == ADMIN_ROLE_ID for r in ctx.author.roles):
            return
        channel_id = ctx.channel.id
        if channel_id not in self.active_tickets:
            await ctx.send("Channel ini bukan tiket ML aktif.", delete_after=5)
            return
        ticket = self.active_tickets[channel_id]
        member = ctx.guild.get_member(ticket["user_id"])
        nomor = next_ticket_number()
        closed_at = datetime.datetime.now(datetime.timezone.utc)
        await ctx.send(
            f"{member.mention if member else ''}\n"
            f"Topup berhasil diproses. Terima kasih telah berbelanja di {STORE_NAME}! "
            f"Tiket ditutup dalam 5 detik."
        )
        await asyncio.sleep(5)
        transcript_file = await generate_transcript(ctx.channel, STORE_NAME)
        transcript_ch = ctx.guild.get_channel(TRANSCRIPT_CHANNEL_ID)
        if transcript_ch:
            try:
                await transcript_ch.send(
                    content=f"Transcript {ticket.get('game','ML')} — {ctx.channel.name}",
                    file=transcript_file
                )
            except Exception as e:
                print(f"[WARNING] Gagal kirim transcript ML: {e}")
        log_ch = ctx.guild.get_channel(LOG_CHANNEL_ID)
        game_info = _get_game(ticket.get("game", "ML")) or {}
        game_name = game_info.get("name", ticket.get("game", "ML"))
        if log_ch:
            log_embed = discord.Embed(
                title=f"TOPUP {game_name.upper()} SUKSES — #{nomor:04d}",
                description="Topup berhasil. Terima kasih telah berbelanja di Cellyn Store!",
                color=game_info.get("color", 0x3498DB),
                timestamp=closed_at
            )
            log_embed.add_field(name="Admin", value=f"{ctx.author.mention}\n`{ctx.author.id}`", inline=False)
            log_embed.add_field(
                name="Member",
                value=f"{member.mention if member else ticket['user_id']}\n`{ticket['user_id']}`",
                inline=False
            )
            id_label = game_info.get("id_label", "Player ID")
            log_embed.add_field(name=id_label, value=f"`{ticket['id_ml']}`", inline=False)
            if game_info.get("needs_server") and ticket.get("server_id", "-") != "-":
                log_embed.add_field(name="Server ID", value=f"`{ticket['server_id']}`", inline=False)
            log_embed.add_field(name="Item", value=ticket.get("item_label", f"{ticket['dm']} Diamond"), inline=False)
            log_embed.add_field(name="Total", value=f"Rp {ticket['harga']:,}", inline=False)
            log_embed.add_field(name="Metode Pembayaran", value="QRIS", inline=False)
            log_embed.set_footer(text=STORE_NAME)
            await log_ch.send(embed=log_embed)
        try:
            from utils.db import log_transaction
            opened_at_dt = datetime.datetime.fromisoformat(ticket["opened_at"]) if ticket.get("opened_at") else None
            durasi = int((closed_at - opened_at_dt).total_seconds()) if opened_at_dt else 0
            layanan = ticket.get("game", "ML").lower()
            log_transaction(
                layanan=layanan, nominal=ticket.get("harga", 0) or 0,
                item=ticket.get("item_label", f"{ticket.get('dm', 0)} Diamond"),
                admin_id=ctx.author.id, user_id=ticket.get("user_id"),
                closed_at=closed_at, durasi_detik=durasi
            )
        except Exception as e:
            print(f"[LOG] Gagal log transaksi ml: {e}")
        try:
            royal_role = discord.utils.get(ctx.guild.roles, name="Royal Customer")
            if royal_role and member:
                m = ctx.guild.get_member(ticket.get("user_id"))
                if m and royal_role not in m.roles:
                    await m.add_roles(royal_role)
        except Exception as e:
            print(f"[ROLE] Gagal assign Royal Customer: {e}")
        delete_ml_ticket(channel_id)
        del self.active_tickets[channel_id]
        await ctx.channel.delete()

    @commands.command(name="mlbatal")
    async def mlbatal(self, ctx, *, alasan: str = "Tidak ada alasan diberikan."):
        if not any(r.id == ADMIN_ROLE_ID for r in ctx.author.roles):
            return
        channel_id = ctx.channel.id
        if channel_id not in self.active_tickets:
            await ctx.send("Channel ini bukan tiket ML aktif.", delete_after=5)
            return
        embed = discord.Embed(title="TOPUP DIBATALKAN", color=0x3498DB)
        embed.add_field(name="Dibatalkan oleh", value=ctx.author.mention, inline=True)
        embed.add_field(name="Alasan", value=alasan, inline=False)
        embed.add_field(name="", value="Tiket akan ditutup dalam 5 detik.", inline=False)
        await ctx.send(embed=embed)
        await asyncio.sleep(5)
        delete_ml_ticket(channel_id)
        del self.active_tickets[channel_id]
        await ctx.channel.delete()


async def setup(bot):
    await bot.add_cog(MLStore(bot))
    bot.add_view(MLBuyView())
    print("Cog MLStore siap.")
