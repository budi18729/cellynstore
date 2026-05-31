import time

import datetime

import discord
from discord.ext import commands
from utils.config import (

    ADMIN_ROLE_ID, STORE_NAME,

    TICKET_CATEGORY_ID, GUILD_ID,

    LAINNYA_AUTOREPLY_CHANNEL_ID

)

from utils.db import get_conn
from utils.store_hours import is_store_open
from utils.paginator import PaginatedSelectView, with_price
from utils.counter import next_ticket_number
from utils import ticket_ui


# Data katalog produk "lainnya" (PRODUCTS, CATEGORY_INFO, grup, dst).
from cogs import lainnya_catalog
from cogs.lainnya_catalog import GROUP_ORDER, GROUP_EMOJI, group_of, get_category_info

# Kunci bot_state untuk menandai katalog sudah di-seed sekali-jalan.
SEED_GUARD_KEY = "lainnya_seed_catalog_v1"



THUMBNAIL = "https://i.imgur.com/CWtUCzj.png"

CATALOG_CHANNEL_ID = 1476349829113315489

COLOR_LAINNYA = 0x5865F2

DEFAULT_CAT_EMOJI = "•"





# ── DATABASE ───────────────────────────────────────────────────────────────────

def _init_db():

    conn = get_conn()

    c = conn.cursor()

    c.execute('''

        CREATE TABLE IF NOT EXISTS lainnya_products (

            id       INTEGER PRIMARY KEY AUTOINCREMENT,

            category TEXT NOT NULL,

            name     TEXT NOT NULL,

            harga    INTEGER NOT NULL,

            active   INTEGER DEFAULT 1

        )

    ''')

    c.execute('''

        CREATE TABLE IF NOT EXISTS lainnya_tickets (

            channel_id      INTEGER PRIMARY KEY,

            user_id         INTEGER,

            item_id         INTEGER,

            item_name       TEXT,

            category        TEXT,

            harga           INTEGER,

            payment_method  TEXT,

            admin_id        INTEGER,

            embed_message_id INTEGER,

            opened_at       TEXT,

            warned          INTEGER DEFAULT 0,

            warn_message_id INTEGER,

            last_activity   TEXT

        )

    ''')

    # Migration

    try:

        c.execute("ALTER TABLE lainnya_tickets ADD COLUMN embed_message_id INTEGER")

        conn.commit()

    except Exception:

        pass

    DEFAULT_PRODUCTS = [

        (1, "CLOUD PHONE", "REDFINGER VIP 7DAY",   20500),

        (2, "CLOUD PHONE", "REDFINGER KVIP 7DAY",  37500),

        (3, "CLOUD PHONE", "REDFINGER SVIP 7DAY",  42000),

        (4, "CLOUD PHONE", "REDFINGER XVIP 7DAY",  102000),

        (5, "CLOUD PHONE", "REDFINGER VIP 30DAY",  62000),

        (6, "CLOUD PHONE", "REDFINGER KVIP 30DAY", 95500),

        (7, "CLOUD PHONE", "REDFINGER SVIP 30DAY", 102000),

        (8, "CLOUD PHONE", "REDFINGER XVIP 30DAY", 318000),

        (9, "DISCORD NITRO", "NITRO BOOST 1 MONTH", 25000),

        (10,"DISCORD NITRO", "NITRO BOOST 3 MONTH", 50000),

    ]

    c.execute("SELECT COUNT(*) as cnt FROM lainnya_products")

    if c.fetchone()["cnt"] == 0:

        for pid, cat, name, harga in DEFAULT_PRODUCTS:

            c.execute("INSERT INTO lainnya_products (id,category,name,harga,active) VALUES (?,?,?,?,1)",

                      (pid, cat, name, harga))

    # Tabel info kategori (deskripsi + S&K) untuk embed tiket & auto-reply.
    c.execute('''
        CREATE TABLE IF NOT EXISTS lainnya_category_info (
            category    TEXT PRIMARY KEY,
            description TEXT,
            terms       TEXT
        )
    ''')

    # Seed katalog (PRODUCTS + CATEGORY_INFO) sekali-jalan, dijaga bot_state.
    _seed_catalog_once(conn, c)

    conn.commit()

    conn.close()


def _seed_catalog_once(conn, c):
    """Seed produk & info kategori dari cogs/lainnya_catalog.py SATU KALI.

    - Dijaga oleh bot_state[SEED_GUARD_KEY]; bila sudah ada, langsung berhenti.
    - Produk: anti-duplikat berdasarkan (category, name). Harga yang sudah ada
      (mis. sudah diubah admin) TIDAK ditimpa karena baris existing dilewati.
    - Info kategori: INSERT OR IGNORE -> tidak menimpa baris yang sudah ada.
    """
    c.execute("SELECT value FROM bot_state WHERE key=?", (SEED_GUARD_KEY,))
    if c.fetchone():
        return  # sudah pernah di-seed

    c.execute("SELECT category, name FROM lainnya_products")
    existing = {(r["category"], r["name"]) for r in c.fetchall()}

    inserted = 0
    for cat, name, harga in lainnya_catalog.PRODUCTS:
        if (cat, name) in existing:
            continue
        c.execute(
            "INSERT INTO lainnya_products (category, name, harga, active) VALUES (?,?,?,1)",
            (cat, name, harga),
        )
        existing.add((cat, name))
        inserted += 1

    info_rows = 0
    for cat, info in lainnya_catalog.CATEGORY_INFO.items():
        c.execute(
            "INSERT OR IGNORE INTO lainnya_category_info (category, description, terms) VALUES (?,?,?)",
            (cat, info.get("description", ""), info.get("terms", "")),
        )
        if c.rowcount and c.rowcount > 0:
            info_rows += 1

    c.execute(
        "INSERT OR REPLACE INTO bot_state (key, value) VALUES (?, ?)",
        (SEED_GUARD_KEY, str(inserted)),
    )
    print(f"[LainnyaStore] Seed katalog: +{inserted} produk baru, {info_rows} info kategori.")





def load_lainnya_products():

    conn = get_conn()

    c = conn.cursor()

    c.execute("SELECT id, category, name, harga FROM lainnya_products WHERE active=1 ORDER BY category, id")

    rows = c.fetchall()

    conn.close()

    return [{"id": r["id"], "category": r["category"], "name": r["name"], "harga": r["harga"]} for r in rows]





def save_lainnya_ticket(ticket: dict):

    conn = get_conn()

    c = conn.cursor()

    c.execute('''

        INSERT OR REPLACE INTO lainnya_tickets

        (channel_id, user_id, item_id, item_name, category, harga, payment_method,

         admin_id, embed_message_id, opened_at, warned, warn_message_id, last_activity)

        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)

    ''', (

        ticket["channel_id"], ticket["user_id"], ticket.get("item_id"),

        ticket.get("item_name"), ticket.get("category"), ticket.get("harga"),

        ticket.get("payment_method"), ticket.get("admin_id"),

        ticket.get("embed_message_id"),

        ticket.get("opened_at"), ticket.get("warned", 0),

        ticket.get("warn_message_id"), ticket.get("last_activity"),

    ))

    conn.commit()

    conn.close()





def delete_lainnya_ticket(channel_id: int):

    conn = get_conn()

    c = conn.cursor()

    c.execute("DELETE FROM lainnya_tickets WHERE channel_id=?", (channel_id,))

    conn.commit()

    conn.close()





def load_lainnya_tickets():

    conn = get_conn()

    c = conn.cursor()

    c.execute("SELECT * FROM lainnya_tickets")

    rows = c.fetchall()

    conn.close()

    return {row["channel_id"]: dict(row) for row in rows}





def _get_catalog_msg_id():

    conn = get_conn()

    c = conn.cursor()

    c.execute("SELECT value FROM bot_state WHERE key='lainnya_catalog_msg_id'")

    row = c.fetchone()

    conn.close()

    return int(row["value"]) if row and row["value"] else None





def _set_catalog_msg_id(msg_id):

    conn = get_conn()

    c = conn.cursor()

    c.execute("INSERT OR REPLACE INTO bot_state (key,value) VALUES ('lainnya_catalog_msg_id',?)",

              (str(msg_id),))

    conn.commit()

    conn.close()





# ── CATALOG HELPERS ────────────────────────────────────────────────────────────
def load_category_info(category: str) -> dict:
    """Ambil deskripsi + S&K kategori dari DB (lainnya_category_info).

    Fallback ke data statis lainnya_catalog.get_category_info bila belum ada di DB.
    """
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT description, terms FROM lainnya_category_info WHERE category=?", (category,))
    row = c.fetchone()
    conn.close()
    if row and (row["description"] or row["terms"]):
        return {"description": row["description"] or "", "terms": row["terms"] or ""}
    return get_category_info(category)


def _groups_with_products(products):
    """Daftar (grup, jumlah_produk) yang punya >=1 produk aktif, urut GROUP_ORDER.

    Grup di luar GROUP_ORDER (mis. LAINNYA) diletakkan paling akhir.
    """
    from collections import Counter
    counts = Counter(group_of(p["category"]) for p in products)
    ordered = [(g, counts[g]) for g in GROUP_ORDER if counts.get(g)]
    extras = sorted((g, n) for g, n in counts.items() if g not in GROUP_ORDER)
    return ordered + extras


def _categories_in_group(products, group):
    """Daftar (kategori, jumlah_produk) di sebuah grup, urut nama kategori."""
    from collections import Counter
    counts = Counter()
    for p in products:
        if group_of(p["category"]) == group:
            counts[p["category"]] += 1
    return sorted(counts.items())


# ── AUTO-REPLY (FASE 2) ────────────────────────────────────────────────────────
AUTOREPLY_COOLDOWN = 5          # detik per user, cegah spam
AUTOREPLY_MIN_LEN = 3           # abaikan query terlalu pendek
AUTOREPLY_MAX_PRODUCTS = 10     # batasi jumlah produk yang ditampilkan


def _autoreply_search(query: str):
    """Cari kategori/produk dari katalog (DB live) berdasarkan kata kunci.

    Mengembalikan (kind, data):
      - ("category", {"category", "items"})  bila query cocok sebuah kategori
      - ("products", [items...])              bila query cocok nama produk
      - (None, None)                          bila tidak ada yang cocok
    Prioritas: exact category > substring category > substring nama produk.
    """
    q = " ".join(query.lower().split())
    if len(q) < AUTOREPLY_MIN_LEN:
        return None, None

    products = load_lainnya_products()
    if not products:
        return None, None

    categories = list(dict.fromkeys(p["category"] for p in products))

    # 1) exact match nama kategori
    for cat in categories:
        if cat.lower() == q:
            items = [p for p in products if p["category"] == cat]
            return "category", {"category": cat, "items": items}

    # 2) substring match nama kategori (ambil kategori pertama yang cocok)
    cat_hits = [cat for cat in categories if q in cat.lower()]
    if cat_hits:
        cat = cat_hits[0]
        items = [p for p in products if p["category"] == cat]
        return "category", {"category": cat, "items": items}

    # 3) substring match nama produk
    prod_hits = [p for p in products if q in p["name"].lower()]
    if prod_hits:
        return "products", prod_hits

    return None, None


def _build_autoreply_embed(kind: str, data) -> discord.Embed:
    """Bangun embed balasan auto-reply: item + harga + deskripsi + S&K."""
    if kind == "category":
        category = data["category"]
        items = data["items"]
        info = load_category_info(category)

        embed = discord.Embed(
            title=f"📦 {category} — {STORE_NAME}",
            color=COLOR_LAINNYA,
        )
        shown = items[:AUTOREPLY_MAX_PRODUCTS]
        lines = "\n".join(f"• **{p['name']}** — Rp {p['harga']:,}" for p in shown)
        if len(items) > len(shown):
            lines += f"\n… dan {len(items) - len(shown)} produk lain."
        embed.add_field(name="Daftar Produk", value=lines[:1024], inline=False)

        if info.get("description"):
            embed.add_field(name="📋 Deskripsi", value=info["description"][:1024], inline=False)
        if info.get("terms"):
            embed.add_field(name="📜 Syarat & Ketentuan", value=info["terms"][:1024], inline=False)
        embed.set_footer(text="Ketik nama kategori/produk lain untuk info • atau buka tiket di katalog")
        return embed

    # kind == "products"
    items = data[:AUTOREPLY_MAX_PRODUCTS]
    # kelompokkan per kategori untuk inject deskripsi/S&K yang relevan
    from collections import OrderedDict
    by_cat = OrderedDict()
    for p in items:
        by_cat.setdefault(p["category"], []).append(p)

    if len(by_cat) == 1:
        category = next(iter(by_cat))
        embed = _build_autoreply_embed("category", {"category": category, "items": by_cat[category]})
        return embed

    # hasil tersebar di beberapa kategori: tampilkan ringkas dengan label kategori
    embed = discord.Embed(
        title=f"🔎 Hasil pencarian — {STORE_NAME}",
        color=COLOR_LAINNYA,
    )
    for category, plist in by_cat.items():
        lines = "\n".join(f"• **{p['name']}** — Rp {p['harga']:,}" for p in plist)
        embed.add_field(name=category, value=lines[:1024], inline=False)
    embed.set_footer(text="Ketik nama kategori spesifik untuk lihat deskripsi & S&K lengkap")
    return embed


# ── CATALOG EMBED & VIEW ───────────────────────────────────────────────────────

def build_catalog_embed(products):

    groups = _groups_with_products(products)

    grp_list = "\n".join(
        f"{GROUP_EMOJI.get(g, DEFAULT_CAT_EMOJI)} **{g}** — {n} produk" for g, n in groups
    ) or "_Belum ada produk tersedia._"

    embed = discord.Embed(

        title=f"🛒 LAYANAN — {STORE_NAME}",

        description=(

            "Pilih **grup layanan** di bawah, lalu pilih kategori & produk.\n"

            "Atau klik **Custom Order** untuk pesanan khusus.\n\n"

            f"**Grup tersedia:**\n{grp_list}\n\n"

            "💳 Pembayaran: QRIS • DANA • Bank Transfer"

        ),

        color=COLOR_LAINNYA,

    )

    embed.set_footer(text=f"{STORE_NAME}")

    return embed





class CatalogView(discord.ui.View):

    def __init__(self, store_open: bool | None = None, guild=None):

        super().__init__(timeout=None)

        self._store_open = is_store_open() if store_open is None else store_open

        self._guild = guild



    def rebuild(self, products):

        self.clear_items()

        self.add_item(GroupSelect(products))

        self.add_item(CustomOrderButton())

        if not self._store_open:

            for child in self.children:

                child.disabled = True

        return self





CATEGORY_EMOJIS = {

    "CLOUD PHONE": "•",

    "DISCORD NITRO": "•",

    "NETFLIX": "•",

    "SPOTIFY": "•",

    "CAPCUT": "•",

    "YOUTUBE": "•",

    "SOSMED": "•",

    "TIKTOK": "•",

}



class GroupSelect(discord.ui.Select):
    """Level 1 navigasi: pilih GRUP layanan (maks 8 grup, jauh di bawah batas 25)."""

    def __init__(self, products):
        groups = _groups_with_products(products)
        options = [
            discord.SelectOption(
                label=g,
                emoji=GROUP_EMOJI.get(g),
                description=f"{n} produk",
                value=g,
            )
            for g, n in groups
        ]
        if not options:
            options = [discord.SelectOption(label="Belum ada produk", value="__none__")]
        super().__init__(
            placeholder="Pilih grup layanan...",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="lainnya_group",
        )

    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "__none__":
            await interaction.response.send_message("Belum ada produk tersedia.", ephemeral=True)
            return
        await _show_categories(interaction, self.values[0])


async def _show_categories(interaction: discord.Interaction, group: str):
    """Level 2 navigasi: tampilkan KATEGORI dalam grup (paginated)."""
    products = load_lainnya_products()
    cats = _categories_in_group(products, group)
    if not cats:
        await interaction.response.send_message(
            f"Belum ada kategori aktif di grup **{group}**.", ephemeral=True
        )
        return

    options = [
        discord.SelectOption(label=cat[:100], description=f"{cnt} produk", value=cat)
        for cat, cnt in cats
    ]

    async def on_category(inter: discord.Interaction, value: str):
        await _show_products(inter, value)

    emoji = GROUP_EMOJI.get(group, "")
    view = PaginatedSelectView(
        options,
        on_select=on_category,
        placeholder=f"Pilih kategori {group}..."[:150],
        owner_id=interaction.user.id,
    )
    await interaction.response.send_message(
        f"{emoji} **{group}** — pilih kategori:", view=view, ephemeral=True
    )


async def _show_products(interaction: discord.Interaction, category: str):
    """Level 3 navigasi: tampilkan PRODUK dalam kategori (paginated)."""
    products = load_lainnya_products()
    items = [p for p in products if p["category"] == category]
    if not items:
        await interaction.response.send_message(
            f"Belum ada produk aktif di kategori **{category}**.", ephemeral=True
        )
        return

    options = [
        discord.SelectOption(
            label=with_price(p["name"], f"Rp {p['harga']:,}"),
            description=category[:100],
            value=str(p["id"]),
        )
        for p in items
    ]

    async def on_product(inter: discord.Interaction, value: str):
        await open_product_ticket(inter, int(value))

    view = PaginatedSelectView(
        options,
        on_select=on_product,
        placeholder=f"Pilih produk {category}..."[:150],
        owner_id=interaction.user.id,
    )
    await interaction.response.send_message(
        f"📦 **{category}** — pilih produk:", view=view, ephemeral=True
    )


async def open_product_ticket(interaction: discord.Interaction, product_id: int):
    """Buat tiket order 1 produk + tampilkan deskripsi & S&K kategori di embed tiket."""
    products = load_lainnya_products()
    product = next((p for p in products if p["id"] == product_id), None)
    if not product:
        await interaction.response.send_message("Produk tidak ditemukan.", ephemeral=True)
        return

    cog = interaction.client.cogs.get("LainnyaStore")
    if not cog:
        return

    member = interaction.user
    guild = interaction.guild

    for ch_id, t in cog.active_tickets.items():
        if t["user_id"] == member.id:
            existing = guild.get_channel(ch_id)
            if existing:
                await interaction.response.send_message(
                    f"Kamu masih punya tiket aktif di {existing.mention}!", ephemeral=True
                )
                return

    await interaction.response.defer(ephemeral=True)

    cat_channel = guild.get_channel(TICKET_CATEGORY_ID)
    admin_role = guild.get_role(ADMIN_ROLE_ID)
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        member: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True),
    }
    if admin_role:
        overwrites[admin_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

    ticket_number = next_ticket_number()
    channel = await guild.create_text_channel(
        name=ticket_ui.channel_name("lainnya", ticket_number, member.name),
        category=cat_channel,
        overwrites=overwrites,
    )

    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    ticket = {
        "channel_id": channel.id,
        "user_id": member.id,
        "item_id": product["id"],
        "item_name": product["name"],
        "category": product["category"],
        "harga": product["harga"],
        "payment_method": "QRIS",
        "ticket_number": ticket_number,
        "admin_id": None,
        "embed_message_id": None,
        "opened_at": now,
        "last_activity": now,
        "warned": 0,
        "warn_message_id": None,
    }
    cog.active_tickets[channel.id] = ticket
    save_lainnya_ticket(ticket)

    info = load_category_info(product["category"])
    embed = ticket_ui.open_ticket_embed(
        "lainnya", ticket_number, member,
        item=product["name"],
        total=f"Rp {product['harga']:,}",
        payment="QRIS",
        description=info.get("description") or None,
        terms=info.get("terms") or None,
    )

    admin_mention = admin_role.mention if admin_role else ""
    msg = await channel.send(
        content=f"{member.mention} {admin_mention}\nPesanan baru!",
        embed=embed,
    )
    ticket["embed_message_id"] = msg.id
    save_lainnya_ticket(ticket)
    await interaction.followup.send(
        f"Pesanan dibuat di {channel.mention}!\n{product['name']} - Rp {product['harga']:,}",
        ephemeral=True,
    )


class CustomOrderButton(discord.ui.Button):
    def __init__(self):

        super().__init__(

            label="📝 Custom Order",

            style=discord.ButtonStyle.success,

            custom_id="lainnya_custom_order"

        )



    async def callback(self, interaction: discord.Interaction):

        await interaction.response.send_modal(CustomOrderModal())





class ConfirmOrderView(discord.ui.View):
    """View konfirmasi nominal sebelum tiket custom order dibuat."""

    def __init__(self, cog, member, guild, item_name, qty_int, budget_int, notes_value):
        super().__init__(timeout=60)
        self.cog         = cog
        self.member      = member
        self.guild       = guild
        self.item_name   = item_name
        self.qty_int     = qty_int
        self.budget_int  = budget_int
        self.notes_value = notes_value

    @discord.ui.button(label="✅ Ya, nominal sudah benar", style=discord.ButtonStyle.success)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.member.id:
            await interaction.response.send_message("Bukan tiket kamu!", ephemeral=True)
            return
        self.stop()
        await interaction.response.defer(ephemeral=True)
        await _create_custom_ticket(interaction, self.cog, self.member, self.guild,
                                    self.item_name, self.qty_int, self.budget_int, self.notes_value)

    @discord.ui.button(label="❌ Batalkan", style=discord.ButtonStyle.danger)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.member.id:
            await interaction.response.send_message("Bukan tiket kamu!", ephemeral=True)
            return
        self.stop()
        await interaction.response.edit_message(
            content="❌ Custom order dibatalkan. Kamu bisa coba lagi kapanpun.",
            embed=None, view=None
        )


async def _create_custom_ticket(interaction, cog, member, guild, item_name, qty_int, budget_int, notes_value):
    """Buat tiket custom order setelah dikonfirmasi member."""
    cat_channel = guild.get_channel(TICKET_CATEGORY_ID)
    admin_role  = guild.get_role(ADMIN_ROLE_ID)
    overwrites  = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        member: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True),
    }
    if admin_role:
        overwrites[admin_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

    ticket_number = next_ticket_number()
    channel = await guild.create_text_channel(
        name=ticket_ui.channel_name("lainnya", ticket_number, member.name),
        category=cat_channel,
        overwrites=overwrites
    )

    now    = datetime.datetime.now(datetime.timezone.utc).isoformat()
    ticket = {
        "channel_id": channel.id, "user_id": member.id, "item_id": None,
        "item_name": f"{item_name} (Qty: {qty_int})", "category": "Custom Order",
        "harga": budget_int, "payment_method": "QRIS", "admin_id": None,
        "ticket_number": ticket_number,
        "embed_message_id": None, "opened_at": now, "last_activity": now,
        "warned": 0, "warn_message_id": None,
    }
    cog.active_tickets[channel.id] = ticket
    save_lainnya_ticket(ticket)

    _extra = [("Quantity", str(qty_int), True)]
    if notes_value:
        _extra.append(("Catatan", notes_value, False))
    _extra.append(("Status", "Admin akan mengkonfirmasi ketersediaan & harga. Pembayaran via QRIS.", False))
    embed = ticket_ui.open_ticket_embed(
        "lainnya", ticket_number, member,
        item=item_name,
        total=f"Rp {budget_int:,}",
        payment="QRIS",
        extra_fields=_extra,
    )

    admin_mention = admin_role.mention if admin_role else ""
    msg = await channel.send(
        content=f"{member.mention} {admin_mention}\nCustom order baru! Segera konfirmasi.",
        embed=embed
    )
    ticket["embed_message_id"] = msg.id
    save_lainnya_ticket(ticket)

    await interaction.followup.send(
        f"✅ Custom order kamu dibuat di {channel.mention}!\nBudget: Rp {budget_int:,}",
        ephemeral=True
    )


class CustomOrderModal(discord.ui.Modal, title="Custom Order"):

    item_name = discord.ui.TextInput(

        label="Nama Item / Deskripsi",

        placeholder="contoh: Jasa topup 500 diamond ML",

        style=discord.TextStyle.short,

        required=True

    )

    quantity = discord.ui.TextInput(

        label="Jumlah / Qty",

        placeholder="contoh: 1 atau 500",

        style=discord.TextStyle.short,

        required=True

    )

    budget = discord.ui.TextInput(

        label="Budget / Offer (Rp)",

        placeholder="contoh: 10000 atau 50000",

        style=discord.TextStyle.short,

        required=True

    )

    notes = discord.ui.TextInput(

        label="Catatan (opsional)",

        placeholder="Tambahan info kalau ada",

        style=discord.TextStyle.paragraph,

        required=False

    )



    async def on_submit(self, interaction: discord.Interaction):

        guild = interaction.guild

        member = interaction.user

        cog = interaction.client.cogs.get("LainnyaStore")



        for ch_id, t in cog.active_tickets.items():

            if t["user_id"] == member.id:

                existing = guild.get_channel(ch_id)

                if existing:

                    await interaction.response.send_message(

                        f"Kamu masih punya tiket aktif di {existing.mention}!",

                        ephemeral=True

                    )

                    return



        try:

            budget_int = int(self.budget.value.replace(".", "").replace(",", ""))

        except ValueError:

            await interaction.response.send_message("Budget harus angka.", ephemeral=True)

            return



        try:

            qty_int = int(self.quantity.value)

        except ValueError:

            await interaction.response.send_message("Quantity harus angka.", ephemeral=True)

            return



        if not interaction.response.is_done():

            try:

                await interaction.response.defer(ephemeral=True)

            except Exception:

                pass



        # Kirim warning + konfirmasi nominal dulu
        confirm_embed = discord.Embed(
            title="⚠️ Konfirmasi Nominal Custom Order",
            description=(
                f"Pastikan nominal yang kamu masukkan **sudah benar** sebelum melanjutkan!\n\n"
                f"**Salah input nominal = tiket tetap diproses dengan nominal tersebut.**\n"
                f"Cellyn Store tidak bertanggung jawab atas kesalahan input dari member.\n\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"🛒 **Item:** {self.item_name.value}\n"
                f"📦 **Qty:** {qty_int}\n"
                f"💰 **Budget/Nominal:** Rp {budget_int:,}\n"
                + (f"📝 **Catatan:** {self.notes.value}\n" if self.notes.value else "") +
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
                f"Apakah nominal **Rp {budget_int:,}** sudah benar?"
            ),
            color=0xFF8C00,
        )
        confirm_embed.set_footer(text="Konfirmasi dalam 60 detik atau order otomatis dibatalkan.")

        view = ConfirmOrderView(
            cog=cog, member=member, guild=guild,
            item_name=self.item_name.value, qty_int=qty_int,
            budget_int=budget_int, notes_value=self.notes.value
        )
        await interaction.followup.send(embed=confirm_embed, view=view, ephemeral=True)





async def _create_lainnya_ticket(interaction: discord.Interaction, cart: list):
    guild = interaction.guild
    member = interaction.user
    cog = interaction.client.cogs.get("LainnyaStore")


    for ch_id, t in cog.active_tickets.items():

        if t["user_id"] == member.id:

            existing = guild.get_channel(ch_id)

            if existing:

                await interaction.response.edit_message(

                    content=f"Kamu masih punya tiket aktif di {existing.mention}!",

                    embed=None, view=None

                )

                return



    # Always ack interaction to avoid "interaction failed"
    if not interaction.response.is_done():
        try:
            await interaction.response.defer(ephemeral=True)
        except Exception:
            pass


    total = sum(i["harga"] for i in cart)

    items_label = ", ".join(i["name"] for i in cart)

    categories_label = ", ".join(dict.fromkeys(i["category"] for i in cart))



    cat_channel = guild.get_channel(TICKET_CATEGORY_ID)

    admin_role = guild.get_role(ADMIN_ROLE_ID)

    overwrites = {

        guild.default_role: discord.PermissionOverwrite(read_messages=False),

        member: discord.PermissionOverwrite(read_messages=True, send_messages=True),

        guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True),

    }

    if admin_role:

        overwrites[admin_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)



    ticket_number = next_ticket_number()

    channel = await guild.create_text_channel(

        name=ticket_ui.channel_name("lainnya", ticket_number, member.name), category=cat_channel, overwrites=overwrites

    )



    now = datetime.datetime.now(datetime.timezone.utc).isoformat()

    ticket = {

        "channel_id": channel.id, "user_id": member.id,

        "item_id": cart[0]["id"], "item_name": items_label,

        "category": categories_label, "harga": total,

        "payment_method": "QRIS", "admin_id": None,

        "ticket_number": ticket_number,

        "embed_message_id": None,

        "opened_at": now, "last_activity": now, "warned": 0, "warn_message_id": None,

    }

    cog.active_tickets[channel.id] = ticket

    save_lainnya_ticket(ticket)

    cog.carts.pop(member.id, None)



    items_text = "\n".join(

        f"• **{i['name']}** ({i['category']}) — Rp {i['harga']:,}" for i in cart

    )

    embed = ticket_ui.open_ticket_embed(
        "lainnya", ticket_number, member,
        item=items_text,
        total=f"Rp {total:,}",
        payment="QRIS",
        extra_fields=[("Catatan", "Setelah pembayaran dikonfirmasi, admin akan memproses pesanan.", False)],
    )



    admin_mention = admin_role.mention if admin_role else ""

    msg = await channel.send(

        content=f"{member.mention} {admin_mention}\nPesanan baru! Segera konfirmasi metode pembayaran.",

        embed=embed

    )

    ticket["embed_message_id"] = msg.id

    save_lainnya_ticket(ticket)

    try:
        await interaction.followup.send(f"Tiket order kamu dibuat di {channel.mention}!", ephemeral=True)
    except Exception:
        pass




# ── COG ────────────────────────────────────────────────────────────────────────

class LainnyaStore(commands.Cog):



    def __init__(self, bot: commands.Bot):
        self.bot = bot
        _init_db()
        self.active_tickets = load_lainnya_tickets()
        self.carts = {}  # user_id -> list of items
        self.catalog_message_id = _get_catalog_msg_id()
        self._autoreply_cd = {}  # user_id -> last autoreply monotonic timestamp
        # auto_close_loop dinonaktifkan



    def cog_unload(self):

        pass  # auto_close_loop sudah dinonaktifkan



    async def cog_load(self):

        self.bot.loop.create_task(self._restore())



    async def _restore(self):

        await self.bot.wait_until_ready()

        self.active_tickets = load_lainnya_tickets()

        self.catalog_message_id = _get_catalog_msg_id()

        print(f"[LainnyaStore] Restored {len(self.active_tickets)} tiket, catalog_msg={self.catalog_message_id}")



    async def refresh_catalog(self):
        products = load_lainnya_products()

        guild = self.bot.get_guild(GUILD_ID)

        if not guild:

            return

        ch = guild.get_channel(CATALOG_CHANNEL_ID)

        if not ch:

            return

        embed = build_catalog_embed(products)

        view = CatalogView(store_open=is_store_open()).rebuild(products)
        if self.catalog_message_id:
            try:
                msg = await ch.fetch_message(self.catalog_message_id)
                await msg.edit(embed=embed, view=view)
                return
            except Exception:

                pass

        # Hapus embed lama dari bot

        # Hanya hapus embed milik cog ini, bukan semua pesan bot

        if self.catalog_message_id:

            try:

                old_msg = await ch.fetch_message(self.catalog_message_id)

                await old_msg.delete()

            except Exception:

                pass

        sent = await ch.send(embed=embed, view=view)

        self.catalog_message_id = sent.id

        _set_catalog_msg_id(sent.id)



    # auto_close_loop dihapus



    async def _update_embed(self, channel, ticket):

        try:

            guild = channel.guild

            member = guild.get_member(ticket["user_id"])

            embed = discord.Embed(

                title=f"ORDER {ticket.get('category', '')} — {STORE_NAME}",

                color=COLOR_LAINNYA,

                timestamp=datetime.datetime.now(datetime.timezone.utc)

            )

            embed.add_field(name="Member", value=member.mention if member else str(ticket["user_id"]), inline=True)

            embed.add_field(name="Item", value=ticket.get("item_name", "-"), inline=True)

            embed.add_field(name="Harga", value=f"Rp {ticket.get('harga', 0):,}", inline=True)

            _info = load_category_info(ticket.get("category") or "")

            if _info.get("description"):

                embed.add_field(name="📋 Deskripsi", value=_info["description"][:1024], inline=False)

            if _info.get("terms"):

                embed.add_field(name="📜 Syarat & Ketentuan", value=_info["terms"][:1024], inline=False)

            embed.add_field(

                name="Metode Bayar",

                value=ticket.get("payment_method") or "*Menunggu konfirmasi member...*",

                inline=False

            )

            embed.add_field(name="Catatan", value="Setelah pembayaran dikonfirmasi, admin akan memproses pesanan.", inline=False)

            embed.set_footer(text=STORE_NAME)

            if ticket.get("embed_message_id"):

                msg = await channel.fetch_message(ticket["embed_message_id"])

                await msg.edit(embed=embed)

        except Exception as e:

            print(f"[LainnyaStore] Update embed error: {e}")



    @commands.Cog.listener()

    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        if message.guild is None:
            return
        ch_id = message.channel.id
        if ch_id not in self.active_tickets:
            return
        ticket = self.active_tickets[ch_id]

        # Fix 3: simpan last_activity ke DB

        ticket["last_activity"] = datetime.datetime.now(datetime.timezone.utc).isoformat()

        save_lainnya_ticket(ticket)


    @commands.command(name="lainnya")

    async def kirim_katalog(self, ctx):

        if not any(r.id == ADMIN_ROLE_ID for r in ctx.author.roles):

            return

        await ctx.message.delete()

        await self.refresh_catalog()

        await ctx.send("✅ Katalog berhasil dikirim!", delete_after=5)



    @commands.Cog.listener(name="on_message")

    async def autoreply_listener(self, message: discord.Message):
        # Fase 2: auto-reply kata kunci di channel khusus.
        if message.author.bot or message.guild is None:
            return
        if message.channel.id != LAINNYA_AUTOREPLY_CHANNEL_ID:
            return
        content = (message.content or "").strip()
        if not content or content.startswith("!"):
            return

        # cooldown per user
        now = time.monotonic()
        last = self._autoreply_cd.get(message.author.id, 0)
        if now - last < AUTOREPLY_COOLDOWN:
            return

        kind, data = _autoreply_search(content)
        if not kind:
            return  # diam saat tidak ada yang cocok

        self._autoreply_cd[message.author.id] = now
        embed = _build_autoreply_embed(kind, data)
        try:
            await message.reply(embed=embed, mention_author=False)
        except Exception as e:
            print(f"[LainnyaStore] autoreply error: {e}")



async def setup(bot: commands.Bot):

    await bot.add_cog(LainnyaStore(bot))

    # Persistent view — tombol tetap bisa diklik setelah restart

    products = load_lainnya_products()

    view = CatalogView().rebuild(products)

    bot.add_view(view)

    print("Cog LainnyaStore siap.")

