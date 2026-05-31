import time
import asyncio
import discord
import datetime
from discord.ext import commands, tasks
from utils.config import ADMIN_ROLE_ID, ROBUX_CATALOG_CHANNEL_ID, LOG_CHANNEL_ID, STORE_NAME, TICKET_CATEGORY_ID, GUILD_ID
from utils.db import get_conn
from utils.robux_db import load_robux_tickets, save_robux_ticket, delete_robux_ticket
from utils.robux_stock import (
    get_available as get_robux_stock_available,
    get_out_total as get_robux_out_total,
    add_out_total as add_robux_out_total,
    record_outgoing as record_robux_outgoing,
    set_available as set_robux_stock_available,
    add_available as add_robux_stock_available,
)
from utils.store_hours import is_store_open
from utils.paginator import PaginatedSelectView, with_price
from utils.counter import next_ticket_number
from utils import ticket_ui
from utils import reviews as reviews_data

THUMBNAIL = "https://i.imgur.com/CWtUCzj.png"


async def send_qris_payment(channel, ticket: dict):
    """Kirim embed pembayaran QRIS ke channel tiket dan tandai ticket.

    Dipakai saat tiket dibuat — pembayaran kini QRIS otomatis (tanpa pilih 1/2/3).
    """
    qris_url = None
    try:
        conn = get_conn()
        c = conn.cursor()
        c.execute("SELECT value FROM settings WHERE key = 'qris_url'")
        row = c.fetchone()
        conn.close()
        if row:
            qris_url = row["value"]
    except Exception:
        pass

    embed = discord.Embed(
        title="QRIS PAYMENT",
        description=(
            f"Scan QR Code di bawah untuk membayar.\n\n"
            f"Item: **{ticket['item_name']}**\n"
            f"Rate: **Rp {ticket['rate']:,}/Robux**\n"
            f"Total: **Rp {ticket['total']:,}**\n\n"
            f"Setelah transfer, kirim bukti pembayaran di sini. Admin akan konfirmasi manual."
        ),
        color=0xE91E63,
    )
    if qris_url:
        embed.set_image(url=qris_url)
    embed.set_footer(text=f"{STORE_NAME} • Pastikan nominal sesuai")

    ticket["payment_method"] = "QRIS"
    payment_embed_msg = await channel.send(embed=embed)
    ticket["payment_embed_msg_id"] = payment_embed_msg.id
    ticket["payment_embed_method"] = "QRIS"
    save_robux_ticket(ticket)


def load_robux_products():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT id, category, name, robux FROM robux_products WHERE active = 1 ORDER BY category, id")
    rows = c.fetchall()
    conn.close()
    return [{"id": r["id"], "category": r["category"], "name": r["name"], "robux": r["robux"]} for r in rows]


def get_robux_product(item_id: int):
    """Ambil 1 produk Robux aktif langsung dari DB (selalu fresh, tanpa cache).

    Dipakai saat member memilih item agar produk yang baru ditambah lewat admin
    panel langsung bisa dipilih tanpa perlu refresh cache (mis. command !rate).
    """
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "SELECT id, category, name, robux FROM robux_products WHERE id = ? AND active = 1",
        (item_id,),
    )
    row = c.fetchone()
    conn.close()
    if not row:
        return None
    return {"id": row["id"], "category": row["category"], "name": row["name"], "robux": row["robux"]}


# Cache ringan untuk catalog; pemilihan item kini dibaca live via get_robux_product().
PRODUCTS = load_robux_products()

def load_categories():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT DISTINCT category FROM robux_products WHERE active = 1 ORDER BY category")
    rows = c.fetchall()
    conn.close()
    return [r["category"] for r in rows]

CATEGORY_COLORS = {
    "GAMEPASS": 0x5865F2,
    "CRATE":    0x2ECC71,
    "BOOST":    0xE91E63,
    "LIMITED":  0xF1C40F,
}
DEFAULT_COLOR = 0x99AAB5

def get_rate():
    conn = get_conn()
    c = conn.cursor()
    c.execute('SELECT rate FROM robux_rate WHERE id = 1')
    row = c.fetchone()
    conn.close()
    return row['rate'] if row else 0

def set_rate(rate):
    conn = get_conn()
    c = conn.cursor()
    c.execute('UPDATE robux_rate SET rate = ? WHERE id = 1', (rate,))
    conn.commit()
    conn.close()

def harga(robux, rate):
    if rate == 0:
        return "Belum diset"
    total = robux * rate
    return f"Rp {total:,}"

ROBUX_EMOJI = "<:Robux:1480480351611654224>"


def build_catalog_embed(rate):
    rate_str = f"Rp {rate:,}/Robux" if rate > 0 else "Belum diset"
    stock_available = get_robux_stock_available()
    stock_out_total = get_robux_out_total()
    categories = load_categories()
    cat_list = "\n".join(f"{ROBUX_EMOJI} **{cat}**" for cat in categories) if categories else "Belum ada produk aktif."
    embed = discord.Embed(
        title=f"{ROBUX_EMOJI} ROBUX STORE — {STORE_NAME}",
        description=(
            f"Harga dihitung otomatis berdasarkan rate Robux terkini.\n"
            f"Rate: **{rate_str}**\n\n"
            f"**Kategori tersedia:**\n{cat_list}\n\n"
            f"Klik tombol kategori di bawah untuk lihat item & order."
        ),
        color=0xE91E63,
        timestamp=datetime.datetime.now(datetime.timezone.utc)
    )
    embed.add_field(name="Stock Tersedia", value=f"**{stock_available:,} Robux**", inline=True)
    embed.add_field(name="Robux Keluar (Total)", value=f"**{stock_out_total:,} Robux**", inline=True)
    _rating = reviews_data.rating_line("robux")
    if _rating:
        embed.add_field(name="⭐ Rating Pembeli", value=_rating, inline=False)
    embed.set_footer(text=f"{STORE_NAME} • Harga dapat berubah sewaktu-waktu")
    return embed

class CategoryView(discord.ui.View):
    def __init__(self, store_open: bool | None = None):
        super().__init__(timeout=None)
        categories = load_categories()
        for cat in categories:
            color = CATEGORY_COLORS.get(cat, DEFAULT_COLOR)
            self.add_item(CategoryButton(cat, color))
        self.add_item(CustomOrderButton())
        store_open = is_store_open() if store_open is None else store_open
        if not store_open:
            for child in self.children:
                child.disabled = True

class CategoryButton(discord.ui.Button):
    def __init__(self, category, color):
        super().__init__(
            label=category,
            emoji=ROBUX_EMOJI,
            style=discord.ButtonStyle.secondary,
            custom_id=f"robux_cat_{category}"
        )
        self.category = category

    async def callback(self, interaction: discord.Interaction):
        fresh = load_robux_products()
        items = [p for p in fresh if p["category"] == self.category]
        rate = get_rate()
        options = []
        for item in items:
            harga_str = harga(item["robux"], rate)
            options.append(discord.SelectOption(
                label=with_price(item["name"], harga_str),
                emoji=ROBUX_EMOJI,
                description=f"{item['robux']} Robux",
                value=str(item["id"]),
            ))
        if not options:
            await interaction.response.send_message(
                f"Belum ada item aktif di kategori **{self.category}**.", ephemeral=True
            )
            return
        view = PaginatedSelectView(
            options,
            on_select=_robux_handle_item,
            placeholder=f"Pilih item {self.category}",
            owner_id=interaction.user.id,
        )
        await interaction.response.send_message(
            f"Pilih item **{self.category}**:",
            view=view,
            ephemeral=True
        )

def _build_cart_embed(cart_items: list, rate: int) -> discord.Embed:
    total_robux = sum(i["robux"] for i in cart_items)
    total_harga = total_robux * rate
    embed = discord.Embed(title="🛒 Keranjang Belanja — Robux Store", color=0xE91E63)
    items_text = "\n".join(
        f"`{idx+1}.` **{i['name']}** — {i['robux']} Robux — Rp {i['robux']*rate:,}"
        for idx, i in enumerate(cart_items)
    )
    embed.add_field(name="Item Dipilih", value=items_text, inline=False)
    embed.add_field(name="Total Robux", value=f"**{total_robux} Robux**", inline=True)
    embed.add_field(name="Total Harga", value=f"**Rp {total_harga:,}**", inline=True)
    embed.add_field(name="Rate", value=f"Rp {rate:,}/Robux", inline=True)
    embed.set_footer(text="Tambah item lagi atau langsung buat tiket")
    return embed


async def _create_robux_ticket(interaction: discord.Interaction, cart: list, rate: int):
    """Buat tiket robux dari cart."""
    guild = interaction.guild
    member = interaction.user
    cog = interaction.client.cogs.get("RobuxStore")

    from utils.config import MAX_TICKETS_PER_SERVICE
    _user_active = sum(
        1 for _cid, _t in cog.active_tickets.items()
        if _t.get("user_id") == member.id and guild.get_channel(_cid)
    )
    if _user_active >= MAX_TICKETS_PER_SERVICE:
        await interaction.response.edit_message(
            content=f"Kamu sudah punya {_user_active} tiket aktif di layanan ini (maks {MAX_TICKETS_PER_SERVICE}). Selesaikan salah satunya dulu.",
            embed=None, view=None
        )
        return

    await interaction.response.edit_message(content="Membuat tiket...", embed=None, view=None)

    total_robux = sum(i["robux"] for i in cart)
    total_harga = total_robux * rate
    ticket_number = next_ticket_number()

    ticket_category = guild.get_channel(TICKET_CATEGORY_ID)
    admin_role = guild.get_role(ADMIN_ROLE_ID)
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        member: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True),
    }
    if admin_role:
        overwrites[admin_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

    channel = await guild.create_text_channel(
        name=ticket_ui.channel_name("robux", ticket_number, member.name),
        category=ticket_category, overwrites=overwrites
    )

    items_label = ", ".join(i["name"] for i in cart)
    ticket = {
        "user_id": member.id,
        "item_id": cart[0]["id"],
        "item_name": items_label,
        "robux": total_robux,
        "rate": rate,
        "total": total_harga,
        "channel_id": channel.id,
        "ticket_number": ticket_number,
        "opened_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "last_activity": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    cog.active_tickets[channel.id] = ticket
    save_robux_ticket(ticket)
    cog.carts.pop(member.id, None)

    items_text = "\n".join(
        f"• **{i['name']}** — {i['robux']} Robux — Rp {i['robux']*rate:,}"
        for i in cart
    )
    embed = ticket_ui.open_ticket_embed(
        "robux", ticket_number, member,
        item=items_text,
        total=f"Rp {total_harga:,}",
        payment="QRIS",
        extra_fields=[
            ("Total Robux", f"{total_robux} Robux", True),
            ("Rate", f"Rp {rate:,}/Robux", True),
            ("Catatan", "Setelah pembayaran dikonfirmasi, admin dan member masuk game untuk proses gift item.", False),
            ("Peringatan", "Tiket yang tidak aktif selama 2 jam akan otomatis ditutup dan transaksi dianggap batal.", False),
        ],
    )

    await channel.send(
        content=f"Halo {member.mention}! Tiket pembelian item Robux telah dibuat.{' ' + admin_role.mention if admin_role else ''}",
        embed=embed
    )
    await send_qris_payment(channel, ticket)
    from utils.customer_insight import send_insight
    await send_insight(interaction.client, channel, member)
    await interaction.followup.send(f"Tiket dibuat! {channel.mention}", ephemeral=True)


class CartView(discord.ui.View):
    """Tampil setelah member pilih item — bisa tambah item lagi atau langsung checkout."""
    def __init__(self, user_id: int):
        super().__init__(timeout=120)
        self.user_id = user_id

    @discord.ui.button(label="➕ Tambah Item", style=discord.ButtonStyle.secondary, custom_id="robux_cart_add")
    async def tambah(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Ini bukan keranjang kamu!", ephemeral=True)
            return
        cats = load_categories()
        view = discord.ui.View(timeout=60)
        for cat in cats:
            color = CATEGORY_COLORS.get(cat, DEFAULT_COLOR)
            view.add_item(CategoryButton(cat, color))
        await interaction.response.edit_message(content="Pilih kategori:", embed=None, view=view)

    @discord.ui.button(label="🛒 Buat Tiket", style=discord.ButtonStyle.success, custom_id="robux_cart_checkout")
    async def checkout(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Ini bukan keranjang kamu!", ephemeral=True)
            return
        cog = interaction.client.cogs.get("RobuxStore")
        cart = cog.carts.get(self.user_id, [])
        if not cart:
            await interaction.response.edit_message(content="Keranjang kosong!", embed=None, view=None)
            return
        rate = get_rate()
        if rate == 0:
            await interaction.response.edit_message(content="Rate belum diset admin!", embed=None, view=None)
            return
        from utils.service_info import get_service_info, build_info_embed
        info = get_service_info("robux")
        has_info = any([info["description"], info["terms"], info["payment_info"]])
        if has_info:
            embed = build_info_embed("Robux Store", info, 0xE91E63)
            await interaction.response.edit_message(embed=embed, view=RobuxInfoView(cart, rate), content=None)
        else:
            await _create_robux_ticket(interaction, cart, rate)

    @discord.ui.button(label="❌ Batalkan", style=discord.ButtonStyle.danger, custom_id="robux_cart_cancel")
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Ini bukan keranjang kamu!", ephemeral=True)
            return
        cog = interaction.client.cogs.get("RobuxStore")
        cog.carts.pop(self.user_id, None)
        await interaction.response.edit_message(content="Keranjang dibatalkan.", embed=None, view=None)


async def _robux_handle_item(interaction: discord.Interaction, value: str):
    """Tambahkan item terpilih ke keranjang lalu tampilkan CartView."""
    item_id = int(value)
    item = get_robux_product(item_id)
    if not item:
        await interaction.response.send_message("Item tidak ditemukan!", ephemeral=True)
        return

    rate = get_rate()
    if rate == 0:
        await interaction.response.send_message("Rate belum diset oleh admin!", ephemeral=True)
        return

    cog = interaction.client.cogs.get("RobuxStore")
    user_id = interaction.user.id

    # Tambah item ke cart
    if user_id not in cog.carts:
        cog.carts[user_id] = []
    cog.carts[user_id].append(item)

    cart = cog.carts[user_id]
    embed = _build_cart_embed(cart, rate)
    view = CartView(user_id=user_id)
    await interaction.response.edit_message(content=None, embed=embed, view=view)


class ItemSelect(discord.ui.Select):
    def __init__(self, options, category):
        super().__init__(
            placeholder=f"Pilih item {category}...",
            options=options,
            custom_id=f"robux_select_{category}"
        )

    async def callback(self, interaction: discord.Interaction):
        await _robux_handle_item(interaction, self.values[0])


class CustomOrderModal(discord.ui.Modal, title="Custom Order Robux"):
    game = discord.ui.TextInput(
        label="Nama Game / Map",
        placeholder="Contoh: Fish It, Sawah Indo, Abyss, dsb.",
        max_length=100,
    )
    username = discord.ui.TextInput(
        label="Username (Roblox)",
        placeholder="Masukkan username Roblox @Username",
        max_length=100,
    )
    item = discord.ui.TextInput(
        label="Nama Item yang Dibeli",
        placeholder="Contoh: Boost, Skin Rod, Gamepass, dll",
        max_length=100,
    )
    robux_amount = discord.ui.TextInput(
        label="Jumlah Robux",
        placeholder="Contoh: 500, 1000",
        max_length=10,
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            robux = int(self.robux_amount.value.strip())
        except ValueError:
            await interaction.response.send_message("Jumlah Robux harus berupa angka!", ephemeral=True)
            return

        rate = get_rate()
        if rate == 0:
            await interaction.response.send_message("Rate belum diset oleh admin. Coba lagi nanti.", ephemeral=True)
            return

        total = robux * rate
        guild = interaction.guild
        member = interaction.user
        cog = interaction.client.cogs.get("RobuxStore")

        # Cek tiket aktif (maks per layanan)
        from utils.config import MAX_TICKETS_PER_SERVICE
        _user_active = sum(
            1 for _cid, _t in cog.active_tickets.items()
            if _t.get("user_id") == member.id and guild.get_channel(_cid)
        )
        if _user_active >= MAX_TICKETS_PER_SERVICE:
            await interaction.response.send_message(
                f"Kamu sudah punya {_user_active} tiket aktif di layanan ini (maks {MAX_TICKETS_PER_SERVICE}). Selesaikan salah satunya dulu.",
                ephemeral=True
            )
            return

        await interaction.response.send_message("Membuat tiket...", ephemeral=True)

        ticket_number = next_ticket_number()
        ticket_category = guild.get_channel(TICKET_CATEGORY_ID)
        admin_role = guild.get_role(ADMIN_ROLE_ID)
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            member: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        }
        if admin_role:
            overwrites[admin_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        channel = await guild.create_text_channel(
            name=ticket_ui.channel_name("robux", ticket_number, member.name),
            category=ticket_category, overwrites=overwrites
        )

        item_label = f"[Custom] {self.item.value.strip()}"
        ticket = {
            "user_id": member.id,
            "item_id": 0,
            "item_name": item_label,
            "robux": robux,
            "rate": rate,
            "total": total,
            "channel_id": channel.id,
            "ticket_number": ticket_number,
            "opened_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "last_activity": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
        cog.active_tickets[channel.id] = ticket
        save_robux_ticket(ticket)

        embed = ticket_ui.open_ticket_embed(
            "robux", ticket_number, member,
            item=f"[Custom] {self.item.value.strip()}",
            total=f"Rp {total:,}",
            payment="QRIS",
            extra_fields=[
                ("Game / Map", self.game.value.strip(), True),
                ("Username Roblox", self.username.value.strip(), True),
                ("Jumlah Robux", f"{robux} Robux", True),
                ("Rate", f"Rp {rate:,}/Robux", True),
                ("Peringatan", "Tiket yang tidak aktif selama 2 jam akan otomatis ditutup.", False),
            ],
        )

        await channel.send(
            content=f"Halo {member.mention}! Custom order kamu telah dibuat.{' ' + admin_role.mention if admin_role else ''}",
            embed=embed
        )
        await send_qris_payment(channel, ticket)
        from utils.customer_insight import send_insight
        await send_insight(interaction.client, channel, member)
        await interaction.edit_original_response(content=f"Tiket dibuat! {channel.mention}")


class CustomOrderButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="✏️ Custom Order",
            style=discord.ButtonStyle.primary,
            custom_id="robux_custom_order"
        )

    async def callback(self, interaction: discord.Interaction):
        from utils.service_info import get_service_info, build_info_embed
        info = get_service_info("robux")
        has_info = any([info["description"], info["terms"], info["payment_info"]])
        if has_info:
            embed = build_info_embed("Robux Store", info, 0xE91E63)
            await interaction.response.send_message(
                embed=embed,
                view=RobuxCustomInfoView(),
                ephemeral=True
            )
        else:
            await interaction.response.send_modal(CustomOrderModal())


class RobuxInfoView(discord.ui.View):
    def __init__(self, cart, rate):
        super().__init__(timeout=120)
        self.cart = cart
        self.rate = rate

    @discord.ui.button(label="✅ Lanjutkan", style=discord.ButtonStyle.success, custom_id="robux_info_lanjut")
    async def lanjut(self, interaction: discord.Interaction, button: discord.ui.Button):
        await _create_robux_ticket(interaction, self.cart, self.rate)

    @discord.ui.button(label="❌ Batal", style=discord.ButtonStyle.danger, custom_id="robux_info_batal")
    async def batal(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="Dibatalkan.", embed=None, view=None)


class RobuxCustomInfoView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=120)

    @discord.ui.button(label="✅ Lanjutkan", style=discord.ButtonStyle.success, custom_id="robux_custom_info_lanjut")
    async def lanjut(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(CustomOrderModal())

    @discord.ui.button(label="❌ Batal", style=discord.ButtonStyle.danger, custom_id="robux_custom_info_batal")
    async def batal(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="Dibatalkan.", embed=None, view=None)


class RobuxStore(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.catalog_message_id = None
        self.carts = {}  # user_id -> list of items
        self.active_tickets = load_robux_tickets()
        self.auto_close_task.start()

    def cog_unload(self):
        self.auto_close_task.cancel()

    @tasks.loop(minutes=10)
    async def auto_close_task(self):
        now = datetime.datetime.now(datetime.timezone.utc)
        for ch_id, ticket in list(self.active_tickets.items()):
            if ticket.get("paid"):
                continue
            last = ticket.get("last_activity") or ticket.get("opened_at")
            if not last:
                continue
            last_dt = datetime.datetime.fromisoformat(last)
            if last_dt.tzinfo is None:
                last_dt = last_dt.replace(tzinfo=datetime.timezone.utc)
            elapsed = (now - last_dt).total_seconds()
            guild = self.bot.get_guild(GUILD_ID)
            if not guild:
                continue
            channel = guild.get_channel(ch_id)
            if elapsed >= 7200:
                delete_robux_ticket(ch_id)
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
                            "Segera selesaikan pembayaran atau hubungi admin.\n\n"
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
                save_robux_ticket(ticket)

    @auto_close_task.before_loop
    async def before_auto_close(self):
        await self.bot.wait_until_ready()

    async def reload_products(self):
        global PRODUCTS
        PRODUCTS = load_robux_products()

    async def refresh_catalog(self):
        await self.reload_products()
        guild = self.bot.get_guild(GUILD_ID)
        if not guild:
            return
        ch = guild.get_channel(ROBUX_CATALOG_CHANNEL_ID)
        if not ch:
            return
        rate = get_rate()
        embed = build_catalog_embed(rate)
        if self.catalog_message_id:
            try:
                msg = await ch.fetch_message(self.catalog_message_id)
                await msg.edit(embed=embed, view=CategoryView(store_open=is_store_open()))
                return
            except Exception:
                pass
        async for msg in ch.history(limit=20):
            if msg.author == self.bot.user:
                try:
                    await msg.delete()
                except Exception:
                    pass
        sent = await ch.send(embed=embed, view=CategoryView(store_open=is_store_open()))
        self.catalog_message_id = sent.id

    async def refresh_active_tickets(self, guild, rate):
        for ch_id, ticket in list(self.active_tickets.items()):
            channel = guild.get_channel(ch_id)
            if not channel:
                self.active_tickets.pop(ch_id, None)
                continue
            if ticket.get("paid"):
                continue
            ticket["rate"] = rate
            ticket["total"] = ticket["robux"] * rate
            # Update embed payment jika sudah dipilih
            payment_msg_id = ticket.get("payment_embed_msg_id")
            method = ticket.get("payment_embed_method")
            if payment_msg_id and method:
                try:
                    from utils.config import DANA_NUMBER, BCA_NUMBER
                    pmsg = await channel.fetch_message(payment_msg_id)
                    if method == "QRIS":
                        desc = (
                            f"Scan QR Code di bawah untuk membayar.\n\n"
                            f"Item: **{ticket['item_name']}**\n"
                            f"Rate: **Rp {rate:,}/Robux**\n"
                            f"Total: **Rp {ticket['total']:,}**\n\n"
                            f"Setelah transfer, kirim bukti pembayaran di sini. Admin akan konfirmasi manual."
                        )
                    elif method == "DANA":
                        desc = (
                            f"Transfer ke nomor DANA berikut:\n\n"
                            f"**`{DANA_NUMBER}`**\n\n"
                            f"Item: **{ticket['item_name']}**\n"
                            f"Rate: **Rp {rate:,}/Robux**\n"
                            f"Total: **Rp {ticket['total']:,}**\n\n"
                            f"Setelah transfer, kirim bukti pembayaran di sini. Admin akan konfirmasi manual."
                        )
                    elif method == "BCA":
                        desc = (
                            f"Transfer ke rekening BCA berikut:\n\n"
                            f"**`{BCA_NUMBER}`**\n\n"
                            f"Item: **{ticket['item_name']}**\n"
                            f"Rate: **Rp {rate:,}/Robux**\n"
                            f"Total: **Rp {ticket['total']:,}**\n\n"
                            f"Setelah transfer, kirim bukti pembayaran di sini. Admin akan konfirmasi manual."
                        )
                    new_embed = discord.Embed(title=f"{method} PAYMENT", description=desc, color=0xE91E63)
                    new_embed.set_footer(text=f"{STORE_NAME} • Pastikan nominal sesuai")
                    await pmsg.edit(embed=new_embed)
                except Exception as e:
                    print(f"[WARNING] Gagal update embed payment: {e}")
            # Update embed di tiket
            try:
                async for msg in channel.history(limit=10, oldest_first=True):
                    if msg.author == guild.me and msg.embeds:
                        embed = msg.embeds[0]
                        new_embed = discord.Embed(
                            title=embed.title,
                            color=embed.color,
                            timestamp=embed.timestamp
                        )
                        for field in embed.fields:
                            if field.name == "Rate":
                                new_embed.add_field(name="Rate", value=f"Rp {rate:,}/Robux", inline=True)
                            elif field.name == "Total Tagihan":
                                new_embed.add_field(name="Total Tagihan", value=f"Rp {ticket['total']:,}", inline=True)
                            else:
                                new_embed.add_field(name=field.name, value=field.value, inline=field.inline)
                        if embed.footer:
                            new_embed.set_footer(text=embed.footer.text)
                        await msg.edit(embed=new_embed)
                        break
            except Exception as e:
                print(f"[WARNING] Gagal update embed tiket robux: {e}")

    @commands.command(name="rate")
    async def set_rate_cmd(self, ctx, *, nilai: str = None):
        if not any(r.id == ADMIN_ROLE_ID for r in ctx.author.roles):
            return
        await ctx.message.delete()
        if not nilai:
            rate = get_rate()
            rate_str = f"Rp {rate:,}/Robux" if rate > 0 else "Belum diset"
            await ctx.send(f"Rate saat ini: **{rate_str}**", delete_after=10)
            return
        try:
            rate = int(nilai.replace(".", "").replace(",", ""))
        except ValueError:
            await ctx.send("Format salah! Contoh: `!rate 90`", delete_after=5)
            return
        set_rate(rate)
        await ctx.send(f"Rate diupdate: **Rp {rate:,}/Robux**. Catalog sedang diperbarui...", delete_after=5)
        await self.refresh_catalog()
        guild = ctx.guild
        await self.refresh_active_tickets(guild, rate)
        # Refresh embed vilog
        vilog_cog = self.bot.cogs.get("Vilog")
        if vilog_cog and hasattr(vilog_cog, "refresh_embed"):
            await vilog_cog.refresh_embed(guild)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        if message.guild is None:
            return

        channel_id = message.channel.id
        if channel_id not in self.active_tickets:
            return

        ticket = self.active_tickets[channel_id]
        # Hanya update last_activity; pembayaran sekarang QRIS otomatis saat tiket dibuat.
        ticket["last_activity"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        save_robux_ticket(ticket)

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        custom_id = ""
        try:
            custom_id = (interaction.data or {}).get("custom_id", "")
        except Exception:
            custom_id = ""

        # Backward-compat: old tickets might still have PAID/VERIFY buttons.
        if custom_id.startswith("robux_paid_") or custom_id.startswith("robux_verify_"):
            try:
                await interaction.response.send_message(
                    "Fitur tombol pembayaran sudah dinonaktifkan. Kirim bukti pembayaran di chat, admin akan konfirmasi manual.",
                    ephemeral=True,
                )
            except Exception:
                pass

    @commands.command(name="gift")
    async def gift_cmd(self, ctx):
        if not any(r.id == ADMIN_ROLE_ID for r in ctx.author.roles):
            return
        await ctx.message.delete()
        channel_id = ctx.channel.id
        if channel_id not in self.active_tickets:
            await ctx.send("Channel ini bukan tiket robux aktif.", delete_after=5)
            return
        ticket = self.active_tickets[channel_id]

        member = ctx.guild.get_member(ticket["user_id"])
        now = datetime.datetime.now(datetime.timezone.utc)
        now.strftime("%d %b %Y, %H:%M UTC")
        opened_at = datetime.datetime.fromisoformat(ticket["opened_at"])
        durasi_secs = int((now - opened_at).total_seconds())
        f"{durasi_secs // 3600}j {(durasi_secs % 3600) // 60}m {durasi_secs % 60}d"

        # Transcript
        from utils.transcript import generate as generate_transcript
        from utils.config import TRANSCRIPT_CHANNEL_ID
        transcript_ch = ctx.guild.get_channel(TRANSCRIPT_CHANNEL_ID)
        if transcript_ch:
            try:
                transcript_file = await generate_transcript(ctx.channel, STORE_NAME)
                await transcript_ch.send(
                    content=f"Transcript Robux Store — {ctx.channel.name}",
                    file=transcript_file
                )
            except Exception as e:
                print(f"[WARNING] Gagal kirim transcript robux: {e}")

        # Log transaksi (flat text + auto-update garansi setelah rating)
        from utils.db import log_transaction, set_transaction_log_message
        from utils.config import TESTIMONI_CHANNEL_ID
        item_str = f"{ticket.get('item_name','-')} ({ticket.get('robux',0)} Robux)"
        tx_id = None
        try:
            tx_id = log_transaction(
                layanan="robux",
                nominal=ticket.get("total", 0) or 0,
                item=item_str,
                admin_id=ctx.author.id,
                user_id=ticket.get("user_id"),
                closed_at=now,
                durasi_detik=durasi_secs,
                qty=1,
            )
        except Exception as e:
            print(f"[LOG] Gagal log transaksi robux: {e}")

        log_ch = ctx.guild.get_channel(LOG_CHANNEL_ID)
        if log_ch:
            text = ticket_ui.success_log_text(
                seller=ctx.author.mention,
                buyer=member.mention if member else f"<@{ticket['user_id']}>",
                product=item_str,
                qty=1,
                harga=ticket.get("total", 0) or 0,
                rating=None,
                rating_channel_id=TESTIMONI_CHANNEL_ID,
            )
            try:
                msg = await log_ch.send(text)
                if tx_id:
                    set_transaction_log_message(tx_id, log_ch.id, msg.id)
            except Exception as e:
                print(f"[Robux] Gagal kirim log: {e}")

        await ctx.channel.send(
            f"Item berhasil diberikan. Terima kasih telah berbelanja di {STORE_NAME}!\n"
            f"Tiket ditutup dalam 5 detik."
        )

        # Stock Robux (global across Robux-related services)
        try:
            record_robux_outgoing(int(ticket.get("robux", 0) or 0))
            await self.refresh_catalog()
            gp_cog = self.bot.cogs.get("GPStore")
            if gp_cog and hasattr(gp_cog, "refresh_catalog"):
                await gp_cog.refresh_catalog()
            vilog_cog = self.bot.cogs.get("Vilog")
            if vilog_cog and hasattr(vilog_cog, "refresh_embed"):
                await vilog_cog.refresh_embed(ctx.guild)
        except Exception as e:
            print(f"[Stock] Gagal update stock robux: {e}")
        # Assign Royal Customer
        try:
            royal_role = discord.utils.get(ctx.guild.roles, name="Royal Customer")
            if royal_role:
                for uid in [ticket.get("user_id")]:
                    if uid:
                        member = ctx.guild.get_member(uid)
                        if member and royal_role not in member.roles:
                            await member.add_roles(royal_role)
        except Exception as e:
            print(f"[ROLE] Gagal assign Royal Customer: {e}")
        delete_robux_ticket(channel_id)
        del self.active_tickets[channel_id]
        await asyncio.sleep(5)
        await ctx.channel.delete()

    @commands.command(name="tolak")
    async def tolak_cmd(self, ctx, *, alasan: str = None):
        if not any(r.id == ADMIN_ROLE_ID for r in ctx.author.roles):
            return
        await ctx.message.delete()
        channel_id = ctx.channel.id
        if channel_id not in self.active_tickets:
            await ctx.send("Channel ini bukan tiket robux aktif.", delete_after=5)
            return
        ticket = self.active_tickets[channel_id]
        ctx.guild.get_member(ticket["user_id"])
        alasan_str = alasan if alasan else "Tidak ada alasan"
        await ctx.channel.send(
            f"Tiket dibatalkan oleh {ctx.author.mention}.\n"
            f"Alasan: {alasan_str}\n"
            f"Channel akan dihapus dalam 5 detik."
        )
        delete_robux_ticket(channel_id)
        del self.active_tickets[channel_id]
        await asyncio.sleep(5)
        await ctx.channel.delete()

    @commands.command(name="catalog")
    async def catalog_cmd(self, ctx):
        if not any(r.id == ADMIN_ROLE_ID for r in ctx.author.roles):
            return
        await ctx.message.delete()
        await self.refresh_catalog()
        await ctx.send("Catalog dikirim!", delete_after=5)

    @commands.command(name="stock")
    async def stock_cmd(self, ctx):
        if not any(r.id == ADMIN_ROLE_ID for r in ctx.author.roles):
            return
        await ctx.message.delete()
        available = get_robux_stock_available()
        out_total = get_robux_out_total()
        await ctx.send(
            f"📦 Stock Robux\n"
            f"Stock tersedia: **{available:,} Robux**\n"
            f"Robux keluar (total): **{out_total:,} Robux**",
            delete_after=20
        )

    @commands.command(name="stockset")
    async def stockset_cmd(self, ctx, amount: int = None):
        if not any(r.id == ADMIN_ROLE_ID for r in ctx.author.roles):
            return
        await ctx.message.delete()
        if amount is None or amount < 0:
            await ctx.send("Format: `!stockset <jumlah_robux>`", delete_after=10)
            return
        set_robux_stock_available(int(amount))
        await ctx.send(f"✅ Stock tersedia diset ke **{int(amount):,} Robux**", delete_after=10)
        try:
            await self.refresh_catalog()
            gp_cog = self.bot.cogs.get("GPStore")
            if gp_cog and hasattr(gp_cog, "refresh_catalog"):
                await gp_cog.refresh_catalog()
            vilog_cog = self.bot.cogs.get("Vilog")
            if vilog_cog and hasattr(vilog_cog, "refresh_embed"):
                await vilog_cog.refresh_embed(ctx.guild)
        except Exception:
            pass

    @commands.command(name="stockadd")
    async def stockadd_cmd(self, ctx, amount: int = None):
        if not any(r.id == ADMIN_ROLE_ID for r in ctx.author.roles):
            return
        await ctx.message.delete()
        if amount is None:
            await ctx.send("Format: `!stockadd <jumlah_robux>`", delete_after=10)
            return
        new_value = add_robux_stock_available(int(amount))
        await ctx.send(f"✅ Stock tersedia sekarang: **{new_value:,} Robux**", delete_after=10)
        try:
            await self.refresh_catalog()
            gp_cog = self.bot.cogs.get("GPStore")
            if gp_cog and hasattr(gp_cog, "refresh_catalog"):
                await gp_cog.refresh_catalog()
            vilog_cog = self.bot.cogs.get("Vilog")
            if vilog_cog and hasattr(vilog_cog, "refresh_embed"):
                await vilog_cog.refresh_embed(ctx.guild)
        except Exception:
            pass

    @commands.command(name="stockoutadd")
    async def stockoutadd_cmd(self, ctx, amount: int = None):
        """
        Tambah Robux keluar (total) tanpa mengubah stock tersedia.
        Berguna untuk transaksi di luar bot yang tetap ingin dihitung di statistik.
        """
        if not any(r.id == ADMIN_ROLE_ID for r in ctx.author.roles):
            return
        await ctx.message.delete()
        if amount is None or amount <= 0:
            await ctx.send("Format: `!stockoutadd <jumlah_robux>`", delete_after=10)
            return
        new_out = add_robux_out_total(int(amount))
        await ctx.send(f"✅ Robux keluar (total) sekarang: **{new_out:,} Robux**", delete_after=10)
        try:
            await self.refresh_catalog()
            gp_cog = self.bot.cogs.get("GPStore")
            if gp_cog and hasattr(gp_cog, "refresh_catalog"):
                await gp_cog.refresh_catalog()
            vilog_cog = self.bot.cogs.get("Vilog")
            if vilog_cog and hasattr(vilog_cog, "refresh_embed"):
                await vilog_cog.refresh_embed(ctx.guild)
        except Exception:
            pass

    @commands.command(name="stockoutship")
    async def stockoutship_cmd(self, ctx, amount: int = None):
        """
        Catat Robux keluar dan kurangi stock tersedia (out_total += amount, available -= amount).
        Berguna untuk koreksi manual yang memang mengurangi inventory.
        """
        if not any(r.id == ADMIN_ROLE_ID for r in ctx.author.roles):
            return
        await ctx.message.delete()
        if amount is None or amount <= 0:
            await ctx.send("Format: `!stockoutship <jumlah_robux>`", delete_after=10)
            return
        record_robux_outgoing(int(amount))
        available = get_robux_stock_available()
        out_total = get_robux_out_total()
        await ctx.send(
            f"✅ Stock update\n"
            f"Stock tersedia: **{available:,} Robux**\n"
            f"Robux keluar (total): **{out_total:,} Robux**",
            delete_after=15
        )
        try:
            await self.refresh_catalog()
            gp_cog = self.bot.cogs.get("GPStore")
            if gp_cog and hasattr(gp_cog, "refresh_catalog"):
                await gp_cog.refresh_catalog()
            vilog_cog = self.bot.cogs.get("Vilog")
            if vilog_cog and hasattr(vilog_cog, "refresh_embed"):
                await vilog_cog.refresh_embed(ctx.guild)
        except Exception:
            pass

async def setup(bot):
    await bot.add_cog(RobuxStore(bot))
    bot.add_view(CategoryView())
    print("Cog RobuxStore siap.")
