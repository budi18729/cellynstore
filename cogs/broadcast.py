import asyncio
import time
import datetime
import discord
from discord import app_commands
from discord.ext import commands
from utils.config import ADMIN_ROLE_ID, STORE_NAME, LOG_CHANNEL_ID
from utils.db import get_conn

THUMBNAIL = "https://i.imgur.com/CWtUCzj.png"


def _get_cooldown(user_id: str) -> float:
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT value FROM bot_state WHERE key=?", (f"broadcast_cd_{user_id}",))
    row = c.fetchone()
    conn.close()
    return float(row['value']) if row else 0.0


def _set_cooldown(user_id: str, t: float):
    conn = get_conn()
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO bot_state (key, value) VALUES (?,?)",
              (f"broadcast_cd_{user_id}", str(t)))
    conn.commit()
    conn.close()


class BroadcastCog(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="broadcast", description="[ADMIN] Kirim pengumuman ke semua member via DM")
    @app_commands.describe(image_url="URL gambar opsional (opsional)")
    async def broadcast(self, interaction: discord.Interaction, image_url: str = None):
        if not any(r.id == ADMIN_ROLE_ID for r in interaction.user.roles):
            await interaction.response.send_message("Admin only!", ephemeral=True)
            return

        user_id = str(interaction.user.id)
        now = time.time()
        last = _get_cooldown(user_id)
        if now - last < 86400:
            remaining = 86400 - (now - last)
            jam = int(remaining // 3600)
            menit = int((remaining % 3600) // 60)
            await interaction.response.send_message(
                f"⏱️ Broadcast cuma bisa sekali per hari!\n🕐 Sisa: **{jam} jam {menit} menit**",
                ephemeral=True
            )
            return

        admin = interaction.user
        cog_self = self

        class BroadcastModal(discord.ui.Modal, title="Broadcast Pesan"):
            pesan = discord.ui.TextInput(
                label="Pesan",
                style=discord.TextStyle.paragraph,
                placeholder="Tulis pesan broadcast di sini...\nBisa multiline dan pakai **bold**",
                max_length=2000,
            )

            async def on_submit(modal_self, modal_interaction: discord.Interaction):
                pesan_text = str(modal_self.pesan)
                embed = discord.Embed(
                    title=f"📢 Pengumuman {STORE_NAME}",
                    description=pesan_text,
                    color=0x00BFFF,
                    timestamp=datetime.datetime.now(datetime.timezone.utc),
                )
                embed.set_author(name=f"Dari: {admin.display_name}", icon_url=admin.display_avatar.url)
                if image_url:
                    embed.set_image(url=image_url)
                embed.set_footer(text=f"{STORE_NAME} • Pengumuman", icon_url=THUMBNAIL)

                view = discord.ui.View(timeout=60)
                kirim_btn = discord.ui.Button(label="Kirim", style=discord.ButtonStyle.success, emoji="📢")
                batal_btn = discord.ui.Button(label="Batal", style=discord.ButtonStyle.danger, emoji="❌")

                async def kirim_callback(btn: discord.Interaction):
                    if btn.user.id != admin.id:
                        await btn.response.send_message("Bukan hakmu!", ephemeral=True)
                        return
                    await btn.response.edit_message(content="📢 Mengirim broadcast...", embed=None, view=None)
                    _set_cooldown(user_id, now)
                    success = failed = 0
                    for member in btn.guild.members:
                        if member.bot:
                            continue
                        try:
                            await member.send(embed=embed)
                            success += 1
                            await asyncio.sleep(0.5)
                        except Exception:
                            failed += 1
                    await btn.edit_original_response(
                        content=f"✓Broadcast selesai!\nTerkirim: **{success}** | Gagal: **{failed}**"
                    )
                    log_ch = btn.guild.get_channel(LOG_CHANNEL_ID)
                    if log_ch:
                        log_embed = discord.Embed(title="LOG BROADCAST", color=0x00BFFF,
                                                  timestamp=datetime.datetime.now(datetime.timezone.utc))
                        log_embed.add_field(name="Admin", value=admin.mention, inline=True)
                        log_embed.add_field(name="Terkirim", value=str(success), inline=True)
                        log_embed.add_field(name="Gagal", value=str(failed), inline=True)
                        log_embed.add_field(name="Pesan", value=pesan_text[:500], inline=False)
                        log_embed.set_footer(text=STORE_NAME)
                        await log_ch.send(embed=log_embed)

                async def batal_callback(btn: discord.Interaction):
                    if btn.user.id != admin.id:
                        await btn.response.send_message("Bukan hakmu!", ephemeral=True)
                        return
                    await btn.response.edit_message(content="Broadcast dibatalkan.", embed=None, view=None)

                kirim_btn.callback = kirim_callback
                batal_btn.callback = batal_callback
                view.add_item(kirim_btn)
                view.add_item(batal_btn)

                await modal_interaction.response.send_message(
                    content="**Preview broadcast — cek dulu sebelum kirim:**",
                    embed=embed, view=view, ephemeral=True,
                )

        await interaction.response.send_modal(BroadcastModal())


async def setup(bot: commands.Bot):
    await bot.add_cog(BroadcastCog(bot))
