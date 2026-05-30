import time

import asyncio

import datetime

import discord
from discord.ext import commands, tasks
from utils.config import (

    ADMIN_ROLE_ID, LOG_CHANNEL_ID, STORE_NAME,

    TICKET_CATEGORY_ID, TRANSCRIPT_CHANNEL_ID, GUILD_ID

)

from utils.db import get_conn
from utils.store_hours import is_store_open
from utils.paginator import PaginatedSelectView
from utils.counter import next_ticket_number

from utils.transcript import generate as generate_transcript



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

    conn.commit()

    conn.close()





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





# ── CATALOG EMBED & VIEW ───────────────────────────────────────────────────────

def build_catalog_embed(products):

    categories = list(dict.fromkeys(p["category"] for p in products))

    cat_list = "\n".join(f"{CATEGORY_EMOJIS.get(cat, DEFAULT_CAT_EMOJI)} {cat}" for cat in categories)

    

    embed = discord.Embed(

        title=f"🛒 LAYANAN — {STORE_NAME}",

        description=(

            "Pilih kategori untuk melihat produk.\n"

            f"Atau klik custom order untuk pesanan khusus.\n\n"

            f"**Kategori tersedia:**\n{cat_list}\n\n"

            "💳 Pembayaran: QRIS • DANA • Bank Transfer"

        ),

        color=COLOR_LAINNYA,

    )

    embed.set_footer(text=f"{STORE_NAME}")

    return embed





class CategoryButton(discord.ui.Button):

    def __init__(self, category):

        super().__init__(

            label=category,

            style=discord.ButtonStyle.primary,

            custom_id=f"lainnya_cat_{category.replace(' ', '_')}"

        )

        self.category = category



    async def callback(self, interaction: discord.Interaction):

        products = load_lainnya_products()

        items = [p for p in products if p["category"] == self.category]

        if not items:

            await interaction.response.send_message("Tidak ada produk aktif di kategori ini.", ephemeral=True)

            return

        options = [

            discord.SelectOption(label=p["name"], description=f"Rp {p['harga']:,}", value=str(p["id"]))

            for p in items

        ]

        view = PaginatedSelectView(
            options,
            select_factory=lambda opts: ItemSelect(opts, self.category),
            placeholder=f"Pilih item {self.category}",
            owner_id=interaction.user.id,
        )

        await interaction.response.send_message(f"Pilih item **{self.category}**:", view=view, ephemeral=True)





class CatalogView(discord.ui.View):

    def __init__(self, store_open: bool | None = None, guild=None):

        super().__init__(timeout=None)

        self._store_open = is_store_open() if store_open is None else store_open

        self._guild = guild



    def rebuild(self, products):

        self.clear_items()

        self.add_item(CategorySelect(products, self._guild))

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



class CategorySelect(discord.ui.Select):

    def __init__(self, products, guild=None):

        by_category = {}

        for p in products:

            if p["category"] not in by_category:

                by_category[p["category"]] = []

            by_category[p["category"]].append(p)

        

        options = []

        for cat, items in by_category.items():

            options.append(

                discord.SelectOption(label=cat, description=f"{len(items)} produk", value=cat)

            )

        

        super().__init__(

            placeholder="Pilih kategori...",

            min_values=1,

            max_values=1,

            options=options,

            custom_id="lainnya_category"

        )

        self.products = products



    async def callback(self, interaction: discord.Interaction):

        selected_cat = self.values[0]

        items = [p for p in self.products if p["category"] == selected_cat]

        

        if not items:

            await interaction.response.send_message("Tidak ada produk.", ephemeral=True)

            return

        

        product_options = [

            discord.SelectOption(label=p["name"], description=f"Rp {p['harga']:,}", value=str(p["id"]))

            for p in items

        ]

        

        view = PaginatedSelectView(
            product_options,
            select_factory=lambda opts: ProdukSelect(opts, selected_cat),
            placeholder=f"Pilih produk {selected_cat}",
            owner_id=interaction.user.id,
        )

        await interaction.response.send_message(

            f"📦 **{selected_cat}** — Pilih produk:",

            view=view,

            ephemeral=True

        )





class ProdukSelect(discord.ui.Select):

    def __init__(self, options, category):

        super().__init__(

            placeholder="Pilih produk...",

            min_values=1,

            max_values=1,

            options=options,

            custom_id=f"lainnya_produk_{category}"

        )

        self.category = category

        self.options = options



    async def callback(self, interaction: discord.Interaction):

        products = load_lainnya_products()

        product_id = int(self.values[0])

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

                        f"Kamu masih punya tiket aktif di {existing.mention}!",

                        ephemeral=True

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



        channel = await guild.create_text_channel(

            name=f"order-{member.name}",

            category=cat_channel,

            overwrites=overwrites

        )



        now = datetime.datetime.now(datetime.timezone.utc).isoformat()

        ticket = {

            "channel_id": channel.id,

            "user_id": member.id,

            "item_id": product["id"],

            "item_name": product["name"],

            "category": product["category"],

            "harga": product["harga"],

            "payment_method": None,

            "admin_id": None,

            "embed_message_id": None,

            "opened_at": now,

            "last_activity": now,

            "warned": 0,

            "warn_message_id": None,

        }

        cog.active_tickets[channel.id] = ticket

        save_lainnya_ticket(ticket)



        embed = discord.Embed(

            title=f"ORDER {product['category']} — {STORE_NAME}",

            color=COLOR_LAINNYA,

            timestamp=datetime.datetime.now(datetime.timezone.utc)

        )

        embed.add_field(name="Member", value=member.mention, inline=True)

        embed.add_field(name="Item", value=product["name"], inline=True)

        embed.add_field(name="Harga", value=f"Rp {product['harga']:,}", inline=True)

        embed.add_field(name="Metode Bayar", value="*Menunggu konfirmasi...*", inline=False)

        embed.set_footer(text=STORE_NAME)



        admin_mention = admin_role.mention if admin_role else ""

        msg = await channel.send(

            content=f"{member.mention} {admin_mention}\nPesanan baru!",

            embed=embed

        )

        ticket["embed_message_id"] = msg.id

        save_lainnya_ticket(ticket)

        await interaction.followup.send(

            f"Pesanan dibuat di {channel.mention}!\n{product['name']} - Rp {product['harga']:,}",

            ephemeral=True

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

    channel = await guild.create_text_channel(
        name=f"custom-{member.name}",
        category=cat_channel,
        overwrites=overwrites
    )

    now    = datetime.datetime.now(datetime.timezone.utc).isoformat()
    ticket = {
        "channel_id": channel.id, "user_id": member.id, "item_id": None,
        "item_name": f"{item_name} (Qty: {qty_int})", "category": "Custom Order",
        "harga": budget_int, "payment_method": None, "admin_id": None,
        "embed_message_id": None, "opened_at": now, "last_activity": now,
        "warned": 0, "warn_message_id": None,
    }
    cog.active_tickets[channel.id] = ticket
    save_lainnya_ticket(ticket)

    notes_text = f"\n**Catatan:** {notes_value}" if notes_value else ""
    embed = discord.Embed(
        title=f"CUSTOM ORDER — {STORE_NAME}",
        color=0x00FF00,
        timestamp=datetime.datetime.now(datetime.timezone.utc)
    )
    embed.add_field(name="Member",    value=member.mention,       inline=True)
    embed.add_field(name="Item",      value=item_name,            inline=True)
    embed.add_field(name="Quantity",  value=str(qty_int),         inline=True)
    embed.add_field(name="Budget",    value=f"Rp {budget_int:,}", inline=True)
    if notes_value:
        embed.add_field(name="Catatan", value=notes_value, inline=False)
    embed.add_field(name="Metode Bayar", value="*Menunggu konfirmasi member...*", inline=False)
    embed.add_field(name="Status", value="Admin akan mengkonfirmasi ketersediaan & metode pembayaran.", inline=False)
    embed.set_footer(text=STORE_NAME)

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





def _build_lainnya_cart_embed(cart_items: list) -> discord.Embed:

    total = sum(i["harga"] for i in cart_items)

    embed = discord.Embed(title="🛒 Keranjang Belanja", color=COLOR_LAINNYA)

    items_text = "\n".join(

        f"`{idx+1}.` **{i['name']}** ({i['category']}) — Rp {i['harga']:,}"

        for idx, i in enumerate(cart_items)

    )

    embed.add_field(name="Item Dipilih", value=items_text, inline=False)

    embed.add_field(name="Total Harga", value=f"**Rp {total:,}**", inline=True)

    embed.set_footer(text="Tambah item lagi atau langsung buat tiket")

    return embed





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



    channel = await guild.create_text_channel(

        name=f"order-{member.name}", category=cat_channel, overwrites=overwrites

    )



    now = datetime.datetime.now(datetime.timezone.utc).isoformat()

    ticket = {

        "channel_id": channel.id, "user_id": member.id,

        "item_id": cart[0]["id"], "item_name": items_label,

        "category": categories_label, "harga": total,

        "payment_method": None, "admin_id": None,

        "embed_message_id": None,

        "opened_at": now, "last_activity": now, "warned": 0, "warn_message_id": None,

    }

    cog.active_tickets[channel.id] = ticket

    save_lainnya_ticket(ticket)

    cog.carts.pop(member.id, None)



    items_text = "\n".join(

        f"• **{i['name']}** ({i['category']}) — Rp {i['harga']:,}" for i in cart

    )

    embed = discord.Embed(

        title=f"ORDER {categories_label} — {STORE_NAME}",

        color=COLOR_LAINNYA,

        timestamp=datetime.datetime.now(datetime.timezone.utc)

    )

    embed.add_field(name="Member", value=member.mention, inline=True)

    embed.add_field(name="Item", value=items_text, inline=False)

    embed.add_field(name="Total Harga", value=f"Rp {total:,}", inline=True)

    embed.add_field(name="Metode Bayar", value="*Menunggu konfirmasi member...*", inline=False)

    embed.add_field(name="Catatan", value="Setelah pembayaran dikonfirmasi, admin akan memproses pesanan.", inline=False)

    embed.set_footer(text=STORE_NAME)



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




class LainnyaCartView(discord.ui.View):
    def __init__(self, user_id: int):

        super().__init__(timeout=120)

        self.user_id = user_id



    @discord.ui.button(label="➕ Tambah Item", style=discord.ButtonStyle.secondary, custom_id="lainnya_cart_add")

    async def tambah(self, interaction: discord.Interaction, button: discord.ui.Button):

        if interaction.user.id != self.user_id:

            await interaction.response.send_message("Ini bukan keranjang kamu!", ephemeral=True)

            return

        products = load_lainnya_products()

        cats = list(dict.fromkeys(p["category"] for p in products))

        view = discord.ui.View(timeout=60)

        for cat in cats:

            view.add_item(CategoryButton(cat))

        await interaction.response.edit_message(content="Pilih kategori:", embed=None, view=view)



    @discord.ui.button(label="🛒 Buat Tiket", style=discord.ButtonStyle.success, custom_id="lainnya_cart_checkout")

    async def checkout(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Ini bukan keranjang kamu!", ephemeral=True)
            return
        cog = interaction.client.cogs.get("LainnyaStore")
        cart = cog.carts.get(self.user_id, [])
        if not cart:
            await interaction.response.edit_message(content="Keranjang kosong!", embed=None, view=None)
            return
        await _create_lainnya_ticket(interaction, cart)


    @discord.ui.button(label="Batalkan", style=discord.ButtonStyle.danger, custom_id="lainnya_cart_cancel")

    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):

        if interaction.user.id != self.user_id:

            await interaction.response.send_message("Ini bukan keranjang kamu!", ephemeral=True)

            return

        cog = interaction.client.cogs.get("LainnyaStore")

        cog.carts.pop(self.user_id, None)

        await interaction.response.edit_message(content="Keranjang dibatalkan.", embed=None, view=None)





class ItemSelect(discord.ui.Select):
    def __init__(self, options, category):

        super().__init__(

            placeholder=f"Pilih item {category}...",

            options=options,

            custom_id=f"lainnya_select_{category.replace(' ', '_')}"

        )

        self.category = category



    async def callback(self, interaction: discord.Interaction):

        item_id = int(self.values[0])

        products = load_lainnya_products()

        item = next((p for p in products if p["id"] == item_id), None)

        if not item:

            await interaction.response.send_message("Item tidak ditemukan!", ephemeral=True)

            return



        cog = interaction.client.cogs.get("LainnyaStore")

        user_id = interaction.user.id

        if user_id not in cog.carts:

            cog.carts[user_id] = []

        cog.carts[user_id].append(item)



        cart = cog.carts[user_id]

        embed = _build_lainnya_cart_embed(cart)
        view = LainnyaCartView(user_id=user_id)
        await interaction.response.edit_message(content=None, embed=embed, view=view)







# ── COG ────────────────────────────────────────────────────────────────────────

class LainnyaStore(commands.Cog):



    def __init__(self, bot: commands.Bot):
        self.bot = bot
        _init_db()
        self.active_tickets = load_lainnya_tickets()
        self.carts = {}  # user_id -> list of items
        self.catalog_message_id = _get_catalog_msg_id()
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

        if ticket.get("payment_method") is None and message.content.strip() in ["1", "2", "3"]:
            methods = {"1": "QRIS", "2": "DANA", "3": "Bank Transfer"}
            ticket["payment_method"] = methods[message.content.strip()]
            save_lainnya_ticket(ticket)
            await self._update_embed(message.channel, ticket)
            await message.channel.send(
                f"✅ Metode pembayaran: **{ticket['payment_method']}**\n"
                f"Silakan lakukan pembayaran sebesar **Rp {ticket['harga']:,}** dan kirim bukti transfer."
            )


    @commands.command(name="lainnya")

    async def kirim_katalog(self, ctx):

        if not any(r.id == ADMIN_ROLE_ID for r in ctx.author.roles):

            return

        await ctx.message.delete()

        await self.refresh_catalog()

        await ctx.send("✅ Katalog berhasil dikirim!", delete_after=5)





async def setup(bot: commands.Bot):

    await bot.add_cog(LainnyaStore(bot))

    # Persistent view — tombol tetap bisa diklik setelah restart

    products = load_lainnya_products()

    view = CatalogView().rebuild(products)

    bot.add_view(view)

    print("Cog LainnyaStore siap.")

