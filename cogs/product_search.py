"""Pencarian produk lintas-toko via auto-reply di satu channel khusus.

Member cukup mengetik nama produk/kategori di channel pencarian, bot akan
membalas dengan daftar produk + harga (+ stok untuk Robux) dari SEMUA toko:
  - Topup Game (ml.py)        : game_products
  - Robux Store (robux.py)    : robux_products x rate, + stok global
  - Layanan Lainnya (lainnya) : lainnya_products

Fitur:
  - Fuzzy match + normalisasi + alias/sinonim (tahan typo & singkatan).
  - "Mungkin maksud kamu …" saat tidak ada yang cocok persis.
  - Tombol: Buka Tiket (produk Lainnya teratas) + link ke katalog tiap toko.
  - Diam total bila tidak ada yang relevan (channel ini juga dipakai community).

Catatan: menggantikan auto-reply lama (Fase 2) yang sebelumnya ada di lainnya.py.
"""

import re
import time
import difflib
from collections import OrderedDict

import discord
from discord.ext import commands

from utils.config import (
    STORE_NAME,
    GUILD_ID,
    LAINNYA_AUTOREPLY_CHANNEL_ID,
    ML_CATALOG_CHANNEL_ID,
    ROBUX_CATALOG_CHANNEL_ID,
)

# Channel katalog interaktif "Lainnya" (konstanta modul di cogs/lainnya.py).
from cogs.lainnya import CATALOG_CHANNEL_ID as LAINNYA_CATALOG_CHANNEL_ID


# ── Konstanta perilaku ─────────────────────────────────────────────────────────
SEARCH_CHANNEL_ID = LAINNYA_AUTOREPLY_CHANNEL_ID
COOLDOWN = 4                # detik per user, cegah spam
MIN_LEN = 2                 # query minimal (huruf, setelah normalisasi)
MAX_RESULTS = 8             # batas produk yang ditampilkan
MAX_SUGGEST = 5             # batas saran "did you mean"
STRONG_THRESHOLD = 0.78     # skor minimal dianggap cocok kuat
SUGGEST_THRESHOLD = 0.68    # skor minimal untuk masuk saran
TOKEN_FUZZY_FLOOR = 0.6     # rasio fuzzy di bawah ini dianggap tidak cocok (0)
VIEW_TIMEOUT = 180          # detik tombol aktif
CACHE_TTL = 60              # detik cache indeks produk

COLOR_RESULT = 0x8B5CF6     # ungu lembut
COLOR_SUGGEST = 0x64748B    # abu kebiruan

# Emoji estetik (sengaja bukan emoji standar keyboard) — tampil sebagai glyph rapi.
EM_TITLE = "\u2726"     # ✦
EM_BULLET = "\u2727"    # ✧
EM_PRICE = "\u21B3"     # ↳
EM_STOCK = "\u274F"     # ❏
EM_ML = "\u27E1"        # ⟡
EM_ROBUX = "\u25C8"     # ◈
EM_LAINNYA = "\u2756"   # ❖
EM_SUGGEST = "\u2727"   # ✧
EM_FOOT = "\u2727"      # ✧

STORE_META = {
    "ml": {"label": "Topup Game", "emoji": EM_ML, "catalog": ML_CATALOG_CHANNEL_ID},
    "robux": {"label": "Robux Store", "emoji": EM_ROBUX, "catalog": ROBUX_CATALOG_CHANNEL_ID},
    "lainnya": {"label": "Layanan Lainnya", "emoji": EM_LAINNYA, "catalog": LAINNYA_CATALOG_CHANNEL_ID},
}

# Alias/sinonim umum: token kiri di-expand jadi kata kanan saat mencocokkan.
_ALIASES = {
    "yt": "youtube", "ytb": "youtube", "yutub": "youtube",
    "ig": "instagram", "tt": "tiktok", "fb": "facebook", "wa": "whatsapp",
    "ml": "mobile legends", "mlbb": "mobile legends", "mobalegen": "mobile legends",
    "ff": "free fire", "freefire": "free fire",
    "dm": "diamond", "dms": "diamond", "diamon": "diamond", "dimond": "diamond",
    "rbx": "robux", "rbux": "robux", "robex": "robux",
    "gp": "gamepass", "gamepas": "gamepass",
    "nitro": "discord nitro",
    "sub": "subscriber", "subs": "subscriber",
    "spotif": "spotify", "spotfy": "spotify",
    "redfinger": "redfinger cloud phone", "cloudphone": "cloud phone",
}

# Kata pengisi (filler) yang diabaikan saat scoring agar obrolan biasa tak memicu balasan.
_STOPWORDS = {
    "ada", "ga", "gak", "ngga", "nggak", "engga", "kak", "ka", "min", "admin",
    "bang", "bro", "sis", "gan", "halo", "hai", "hi", "hello", "ya", "yaa",
    "yg", "yang", "ini", "itu", "dong", "kah", "mau", "pengen", "pengin",
    "beli", "order", "tanya", "nanya", "brp", "berapa", "harga", "price",
    "ready", "stock", "stok", "open", "ok", "oke", "sip", "thx", "makasih",
    "tq", "no", "yes", "dr", "ke", "di", "dan", "atau", "buat", "tolong",
    "kak,", "info", "list", "menu", "kak.", "p", "pap",
}


# ── Normalisasi & tokenisasi ────────────────────────────────────────────────────
def _normalize(text: str) -> str:
    """Lowercase, samakan pola durasi, buang simbol, rapikan spasi."""
    text = (text or "").lower()
    text = re.sub(r"(\d+)\s*(bln|bulan|month|months|mo)\b", r"\1 bulan", text)
    text = re.sub(r"(\d+)\s*(hr|hari|day|days|d)\b", r"\1 hari", text)
    text = re.sub(r"(\d+)\s*(thn|tahun|year|years|yr)\b", r"\1 tahun", text)
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _expand_tokens(tokens):
    """Ganti token singkatan dengan ekspansi alias-nya (dedupe, jaga urutan).

    Token alias DIGANTI (bukan ditambah) supaya bentuk singkat yang tak ada di
    katalog—mis. "yt"—tidak ikut menyeret turun skor kecocokan.
    """
    out = []
    for t in tokens:
        if t in _ALIASES:
            out.extend(_ALIASES[t].split())
        else:
            out.append(t)
    return list(dict.fromkeys(out))


# ── Pembentukan indeks produk (cache ringan) ────────────────────────────────────
_index_cache = {"data": None, "ts": 0.0}


def _make_entry(store, name, category, price, price_text, extra, blob_text, product_id=None, robux_stock=None):
    blob = _normalize(blob_text)
    return {
        "store": store,
        "name": name,
        "category": category,
        "price": price if isinstance(price, int) else 0,
        "price_text": price_text,
        "extra": extra,
        "product_id": product_id,
        "robux_stock": robux_stock,
        "name_norm": _normalize(name),
        "blob_tokens": blob.split(),
        "blob": blob,
    }


def _build_index():
    """Gabungkan semua produk dari ML + Robux + Lainnya jadi satu indeks pencarian."""
    entries = []

    # Lazy import agar tidak bergantung pada urutan load cog.
    from cogs.lainnya import load_lainnya_products
    from cogs.lainnya_catalog import group_of
    from cogs.ml import _load_games, _load_products
    from cogs.robux import load_robux_products, get_rate
    from utils.robux_stock import get_available as robux_available

    # — Layanan Lainnya —
    try:
        for p in load_lainnya_products():
            cat = p["category"]
            entries.append(_make_entry(
                "lainnya", p["name"], cat, p["harga"], f"Rp {p['harga']:,}",
                "", f"{p['name']} {cat} {group_of(cat)}", product_id=p["id"],
            ))
    except Exception as e:
        print(f"[ProductSearch] index lainnya error: {e}")

    # — Topup Game (ML/FF/WDP/dst) —
    try:
        for g in _load_games():
            gname, code = g["name"], g["code"]
            for pr in _load_products(code):
                disp = f"{gname} \u2014 {pr['label']}"
                entries.append(_make_entry(
                    "ml", disp, gname, pr["harga"], f"Rp {pr['harga']:,}",
                    "", f"{gname} {code} {pr['label']} diamond topup",
                ))
    except Exception as e:
        print(f"[ProductSearch] index ml error: {e}")

    # — Robux Store —
    try:
        rate = get_rate()
        avail = robux_available()
        for p in load_robux_products():
            robux = p["robux"]
            total = robux * rate if rate else 0
            price_text = f"Rp {total:,}" if rate else "Rate belum diset"
            entries.append(_make_entry(
                "robux", p["name"], p["category"], total, price_text,
                f"{robux:,} R$", f"{p['name']} {p['category']} robux {robux}",
                robux_stock=avail,
            ))
    except Exception as e:
        print(f"[ProductSearch] index robux error: {e}")

    return entries


def _get_index():
    now = time.monotonic()
    if _index_cache["data"] is None or now - _index_cache["ts"] > CACHE_TTL:
        try:
            _index_cache["data"] = _build_index()
            _index_cache["ts"] = now
        except Exception as e:
            print(f"[ProductSearch] build index error: {e}")
    return _index_cache["data"] or []


# ── Scoring ─────────────────────────────────────────────────────────────────────
def _token_match(qt: str, bt: str) -> float:
    if qt == bt:
        return 1.0
    if len(qt) >= 3 and (qt in bt or bt in qt):
        return 0.9
    r = difflib.SequenceMatcher(None, qt, bt).ratio()
    return r if r >= TOKEN_FUZZY_FLOOR else 0.0


def _score(q_norm: str, core_tokens, entry) -> float:
    score = 0.0
    name = entry["name_norm"]
    blob = entry["blob"]
    btokens = entry["blob_tokens"]

    # Bonus substring keseluruhan query.
    if q_norm and q_norm in name:
        score = 1.0
    elif q_norm and q_norm in blob:
        score = 0.86

    # Rata-rata kecocokan terbaik tiap token query terhadap token blob.
    if core_tokens:
        total = 0.0
        for qt in core_tokens:
            best = 0.0
            for bt in btokens:
                r = _token_match(qt, bt)
                if r > best:
                    best = r
                if best >= 1.0:
                    break
            total += best
        score = max(score, total / len(core_tokens))

    return score


def search(raw_query: str):
    """Kembalikan (results, suggestions) berdasarkan query bebas dari member."""
    q_norm = _normalize(raw_query)
    if len(q_norm) < MIN_LEN:
        return [], []

    tokens = _expand_tokens(q_norm.split())
    core_tokens = [t for t in tokens if t not in _STOPWORDS and len(t) >= 2]
    if not core_tokens:
        return [], []  # query cuma berisi kata pengisi → diam

    index = _get_index()
    scored = []
    for e in index:
        s = _score(q_norm, core_tokens, e)
        if s > 0:
            scored.append((s, e))
    scored.sort(key=lambda x: (-x[0], x[1]["price"]))

    strong = [e for s, e in scored if s >= STRONG_THRESHOLD]
    if strong:
        return strong[:MAX_RESULTS], []

    suggestions = [e for s, e in scored if s >= SUGGEST_THRESHOLD]
    return [], suggestions[:MAX_SUGGEST]


# ── Embed ─────────────────────────────────────────────────────────────────────--
def _clip(query: str, n: int = 80) -> str:
    q = " ".join((query or "").split())
    return q[:n]


def build_results_embed(results, query: str) -> discord.Embed:
    by_store = OrderedDict()
    for e in results:
        by_store.setdefault(e["store"], []).append(e)

    embed = discord.Embed(
        title=f"{EM_TITLE}  Hasil pencarian \u201c{_clip(query)}\u201d",
        color=COLOR_RESULT,
    )
    for store, items in by_store.items():
        meta = STORE_META.get(store, {"label": store, "emoji": EM_BULLET})
        lines = []
        for e in items:
            line = f"{EM_BULLET} **{e['name']}**\n{EM_PRICE} {e['price_text']}"
            if e.get("extra"):
                line += f"  \u00b7  {e['extra']}"
            lines.append(line)
        field_name = f"{meta['emoji']}  {meta['label'].upper()}"
        if store == "robux" and items[0].get("robux_stock") is not None:
            field_name += f"   {EM_STOCK} stok {items[0]['robux_stock']:,} R$"
        embed.add_field(name=field_name, value="\n".join(lines)[:1024], inline=False)

    embed.set_footer(text=f"{EM_FOOT} {STORE_NAME} \u00b7 klik tombol di bawah untuk lanjut order")
    return embed


def build_suggest_embed(suggestions, query: str) -> discord.Embed:
    names = list(dict.fromkeys(e["name"] for e in suggestions))[:MAX_SUGGEST]
    desc = "\n".join(f"{EM_SUGGEST}  {n}" for n in names)
    embed = discord.Embed(
        title=f"{EM_TITLE}  Belum ketemu yang persis\u2026",
        description=f"Mungkin maksud kamu:\n{desc}",
        color=COLOR_SUGGEST,
    )
    embed.set_footer(text=f"{EM_FOOT} Coba ketik nama produk yang lebih spesifik")
    return embed


# ── View tombol ─────────────────────────────────────────────────────────────────
def _catalog_url(channel_id: int) -> str:
    return f"https://discord.com/channels/{GUILD_ID}/{channel_id}"


class OpenLainnyaTicketButton(discord.ui.Button):
    """Tombol untuk langsung membuka tiket produk Lainnya (reuse alur existing)."""

    def __init__(self, product_id: int):
        super().__init__(label=f"{EM_TITLE} Buka Tiket", style=discord.ButtonStyle.success)
        self.product_id = product_id

    async def callback(self, interaction: discord.Interaction):
        from cogs.lainnya import open_product_ticket
        try:
            await open_product_ticket(interaction, self.product_id)
        except Exception as e:
            print(f"[ProductSearch] open ticket error: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "Maaf, gagal membuka tiket. Coba lewat katalog ya.", ephemeral=True
                )


class SearchResultView(discord.ui.View):
    def __init__(self, results):
        super().__init__(timeout=VIEW_TIMEOUT)
        # Tombol Buka Tiket untuk produk Lainnya teratas (jika ada di hasil).
        top_lainnya = next(
            (e for e in results if e["store"] == "lainnya" and e.get("product_id")),
            None,
        )
        if top_lainnya:
            self.add_item(OpenLainnyaTicketButton(top_lainnya["product_id"]))
        # Tombol link ke katalog tiap toko yang muncul di hasil.
        seen = set()
        for e in results:
            store = e["store"]
            if store in seen:
                continue
            seen.add(store)
            meta = STORE_META.get(store)
            if meta and meta.get("catalog"):
                self.add_item(discord.ui.Button(
                    label=f"Katalog {meta['label']}",
                    url=_catalog_url(meta["catalog"]),
                    style=discord.ButtonStyle.link,
                ))


# ── Cog ──────────────────────────────────────────────────────────────────────--
class ProductSearch(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._cd = {}  # user_id -> last reply monotonic timestamp

    @commands.Cog.listener("on_message")
    async def on_message(self, message: discord.Message):
        if message.author.bot or message.guild is None:
            return
        if message.channel.id != SEARCH_CHANNEL_ID:
            return
        content = (message.content or "").strip()
        if not content or content.startswith("!"):
            return

        now = time.monotonic()
        if now - self._cd.get(message.author.id, 0) < COOLDOWN:
            return

        try:
            results, suggestions = search(content)
        except Exception as e:
            print(f"[ProductSearch] search error: {e}")
            return

        if not results and not suggestions:
            return  # diam saat tak ada yang relevan

        self._cd[message.author.id] = now
        try:
            if results:
                embed = build_results_embed(results, content)
                await message.reply(embed=embed, view=SearchResultView(results), mention_author=False)
            else:
                embed = build_suggest_embed(suggestions, content)
                await message.reply(embed=embed, mention_author=False)
        except Exception as e:
            print(f"[ProductSearch] reply error: {e}")


async def setup(bot: commands.Bot):
    await bot.add_cog(ProductSearch(bot))
