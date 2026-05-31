"""Auto follow-up langganan habis (#3).

Banyak produk di toko bersifat langganan (Spotify/Netflix/Nitro/Canva "1 Bulan",
dst). Cog ini memantau transaction_log, dan beberapa hari SEBELUM langganan
seorang member habis, mengirim DM ramah berisi ajakan perpanjang + tombol
"Order Lagi" ke channel katalog. Ini mesin repeat-order otomatis dari data
transaksimu sendiri.

Alur:
- Loop tiap 6 jam (cek seharian, idempoten).
- Ambil transaksi yang belum di-follow-up (fetch_followup_candidates).
- Saring yang langganannya tinggal <= SUB_FOLLOWUP_LEAD_DAYS hari
  (utils.subscription.needs_followup) — logika murni & teruji.
- DM member (fallback channel testimoni), lalu tandai mark_followup_sent.
"""

import discord
from discord.ext import commands, tasks

from utils.config import STORE_NAME, GUILD_ID, SUB_FOLLOWUP_LEAD_DAYS, TESTIMONI_CHANNEL_ID
from utils.db import fetch_followup_candidates, mark_followup_sent
from utils import subscription as sub

# Channel katalog "Layanan Lainnya" (sama dengan cogs/lainnya.py CATALOG_CHANNEL_ID).
LAINNYA_CATALOG_CHANNEL_ID = 1476349829113315489
COLOR_FOLLOWUP = 0x00BFFF


def build_followup_embed(item: str, sisa_hari: int) -> discord.Embed:
    """Embed DM follow-up langganan yang ramah (bukan spam)."""
    if sisa_hari <= 0:
        waktu = "hari ini"
    elif sisa_hari == 1:
        waktu = "besok"
    else:
        waktu = f"dalam {sisa_hari} hari lagi"
    embed = discord.Embed(
        title="🔔 Langgananmu Sebentar Lagi Habis",
        description=(
            f"Halo! Langgananmu di **{STORE_NAME}** akan berakhir **{waktu}**.\n\n"
            f"**Produk:** {item}\n\n"
            "Mau perpanjang biar nggak putus di tengah jalan? Tinggal klik tombol "
            "di bawah ya. Makasih sudah jadi pelanggan setia kami 🤍"
        ),
        color=COLOR_FOLLOWUP,
    )
    embed.set_footer(text=f"{STORE_NAME} · pengingat perpanjangan")
    return embed


def _order_again_view() -> discord.ui.View:
    view = discord.ui.View(timeout=None)
    url = f"https://discord.com/channels/{GUILD_ID}/{LAINNYA_CATALOG_CHANNEL_ID}"
    view.add_item(discord.ui.Button(
        label="🛒 Perpanjang / Order Lagi",
        style=discord.ButtonStyle.link,
        url=url,
    ))
    return view


class SubFollowup(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self):
        self.followup_loop.start()

    def cog_unload(self):
        self.followup_loop.cancel()

    @tasks.loop(hours=6)
    async def followup_loop(self):
        try:
            await self._run_once()
        except Exception as e:
            print(f"[SubFollowup] loop error: {e}")

    @followup_loop.before_loop
    async def _before(self):
        await self.bot.wait_until_ready()

    async def _run_once(self):
        candidates = fetch_followup_candidates()
        for tx in candidates:
            item = tx.get("item")
            if not sub.needs_followup(tx.get("closed_at"), item, lead_days=SUB_FOLLOWUP_LEAD_DAYS):
                continue
            # Klaim baris dulu (idempoten) supaya tak dobel meski loop tumpang tindih.
            if not mark_followup_sent(tx["id"]):
                continue
            sisa = sub.days_remaining(tx.get("closed_at"), item)
            await self._notify(tx["user_id"], item, sisa if sisa is not None else 0)

    async def _notify(self, user_id: int, item: str, sisa_hari: int):
        embed = build_followup_embed(item, sisa_hari)
        view = _order_again_view()

        user = self.bot.get_user(user_id)
        if user is None:
            try:
                user = await self.bot.fetch_user(user_id)
            except Exception:
                user = None
        if user is not None:
            try:
                await user.send(embed=embed, view=view)
                return
            except discord.Forbidden:
                pass
            except Exception as e:
                print(f"[SubFollowup] DM error {user_id}: {e}")
        # Fallback: mention di channel testimoni (best-effort).
        if TESTIMONI_CHANNEL_ID:
            channel = self.bot.get_channel(TESTIMONI_CHANNEL_ID)
            if channel is not None:
                try:
                    await channel.send(content=f"<@{user_id}>", embed=embed, view=view)
                except Exception as e:
                    print(f"[SubFollowup] channel fallback error: {e}")


async def setup(bot: commands.Bot):
    await bot.add_cog(SubFollowup(bot))
    print("Cog SubFollowup siap.")
