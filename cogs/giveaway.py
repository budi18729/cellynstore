import asyncio
import random
import sqlite3
import datetime
import discord
from discord import app_commands
from discord.ext import commands
from utils.config import ADMIN_ROLE_ID, STORE_NAME, LOG_CHANNEL_ID
from utils.db import get_conn

THUMBNAIL = "https://i.imgur.com/CWtUCzj.png"


def _init_giveaway_table():
    conn = get_conn()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS giveaways (
            message_id  INTEGER PRIMARY KEY,
            channel_id  INTEGER,
            guild_id    INTEGER,
            prize       TEXT,
            end_time    TEXT,
            winners     INTEGER DEFAULT 1,
            host_id     INTEGER,
            participants TEXT DEFAULT '',
            ended       INTEGER DEFAULT 0,
            sponsor     TEXT,
            image_url   TEXT
        )
    ''')
    for col, defval in [('sponsor', 'TEXT'), ('image_url', 'TEXT')]:
        try:
            c.execute(f'ALTER TABLE giveaways ADD COLUMN {col} {defval}')
        except Exception as e:
            if 'duplicate column' not in str(e).lower():
                print(f'[Giveaway] Migration {col}: {e}')
    conn.commit()
    conn.close()


def _save_giveaway(msg_id, channel_id, guild_id, prize, end_time, winners, host_id, participants, sponsor=None, image_url=None):
    conn = get_conn()
    c = conn.cursor()
    parts_str = ','.join(str(p) for p in participants)
    c.execute('''
        INSERT OR REPLACE INTO giveaways
        (message_id, channel_id, guild_id, prize, end_time, winners, host_id, participants, ended, sponsor, image_url)
        VALUES (?,?,?,?,?,?,?,?,0,?,?)
    ''', (msg_id, channel_id, guild_id, prize, end_time.isoformat(), winners, host_id, parts_str, sponsor, image_url))
    conn.commit()
    conn.close()


def _update_participants(msg_id, participants):
    conn = get_conn()
    c = conn.cursor()
    parts_str = ','.join(str(p) for p in participants)
    c.execute('UPDATE giveaways SET participants=? WHERE message_id=?', (parts_str, msg_id))
    conn.commit()
    conn.close()


def _delete_giveaway(msg_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute('DELETE FROM giveaways WHERE message_id=?', (msg_id,))
    conn.commit()
    conn.close()


def _load_giveaways():
    conn = get_conn()
    c = conn.cursor()
    c.execute('SELECT * FROM giveaways WHERE ended=0')
    rows = c.fetchall()
    conn.close()
    result = {}
    for row in rows:
        parts = set(int(p) for p in row['participants'].split(',') if p.strip())
        result[row['message_id']] = {
            'channel_id': row['channel_id'],
            'guild_id': row['guild_id'],
            'prize': row['prize'],
            'end_time': datetime.datetime.fromisoformat(row['end_time']),
            'winners': row['winners'],
            'host_id': row['host_id'],
            'participants': parts,
            'sponsor': row['sponsor'],
            'image_url': row['image_url'],
        }
    return result


def parse_duration(s: str) -> int:
    s = s.strip().lower()
    units = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}
    if s and s[-1] in units:
        try:
            return int(s[:-1]) * units[s[-1]]
        except ValueError:
            return 0
    return 0


class GiveawayCog(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.active_giveaways = {}
        _init_giveaway_table()

    async def cog_load(self):
        self.bot.loop.create_task(self._restore_giveaways())

    async def _restore_giveaways(self):
        await self.bot.wait_until_ready()
        try:
            giveaways = _load_giveaways()
            now = datetime.datetime.now(datetime.timezone.utc)
            restored = 0
            for msg_id, data in giveaways.items():
                self.active_giveaways[msg_id] = data
                remaining = (data['end_time'] - now).total_seconds()
                if remaining > 0:
                    self.bot.loop.create_task(self._resume_giveaway(msg_id, remaining, data))
                    restored += 1
                else:
                    self.bot.loop.create_task(
                        self._end_giveaway(msg_id, data['channel_id'], data['guild_id'],
                                           data['prize'], data['winners'], data['host_id'])
                    )
            if restored:
                print(f"[Giveaway] Restored {restored} active giveaway(s)")
        except Exception as e:
            print(f"[Giveaway] Restore error: {e}")

    async def _resume_giveaway(self, msg_id, remaining, data):
        await asyncio.sleep(remaining)
        if msg_id in self.active_giveaways:
            await self._end_giveaway(msg_id, data['channel_id'], data['guild_id'],
                                     data['prize'], data['winners'], data['host_id'])

    def _build_embed(self, prize, end_time, winner_count, host, participants=0, ended=False, winner_mentions=None, sponsor=None, image_url=None):
        color = 0x95a5a6 if ended else 0xFF6B6B
        embed = discord.Embed(
            title=f"🎉 GIVEAWAY — {prize}",
            color=color,
            timestamp=end_time,
        )
        embed.add_field(name="Hadiah", value=prize, inline=True)
        embed.add_field(name="Pemenang", value=f"{winner_count} orang", inline=True)
        embed.add_field(name="Host", value=host.mention if hasattr(host, 'mention') else str(host), inline=True)
        if sponsor:
            embed.add_field(name="Sponsor", value=sponsor, inline=True)
        embed.add_field(name="Peserta", value=str(participants), inline=True)
        if ended:
            embed.add_field(name="Status", value="SELESAI", inline=True)
            if winner_mentions:
                embed.add_field(name="Pemenang 🎊", value="\n".join(winner_mentions), inline=False)
                embed.description = f"Selamat kepada {', '.join(winner_mentions)}! 🎉"
        else:
            embed.add_field(name="Berakhir", value=f"<t:{int(end_time.timestamp())}:R>", inline=True)
            embed.description = f"Klik tombol **IKUTAN** di bawah untuk ikut!\nBerakhir: <t:{int(end_time.timestamp())}:F>"
        if image_url:
            embed.set_image(url=image_url)
        embed.set_footer(text=f"{STORE_NAME} • Giveaway" + (" • Selesai" if ended else ""))
        return embed

    def _build_view(self, message_id, ended=False):
        view = discord.ui.View(timeout=None)
        btn = discord.ui.Button(
            label="IKUTAN" if not ended else "SELESAI",
            style=discord.ButtonStyle.success if not ended else discord.ButtonStyle.secondary,
            emoji="🎉",
            custom_id=f"giveaway_join_{message_id}",
            disabled=ended,
        )
        view.add_item(btn)
        return view

    async def _end_giveaway(self, message_id, channel_id, guild_id, prize, winner_count, host_id):
        try:
            guild = self.bot.get_guild(guild_id)
            if not guild:
                return
            channel = guild.get_channel(channel_id)
            if not channel:
                return
            try:
                message = await channel.fetch_message(message_id)
            except Exception:
                self.active_giveaways.pop(message_id, None)
                _delete_giveaway(message_id)
                return

            host = guild.get_member(host_id)
            data = self.active_giveaways.get(message_id, {})
            participants = list(data.get('participants', set()))
            end_time = data.get('end_time', datetime.datetime.now(datetime.timezone.utc))

            if not participants:
                await channel.send("Tidak ada peserta giveaway!")
                embed = self._build_embed(prize, end_time, winner_count, host, participants=0, ended=True)
                await message.edit(embed=embed, view=self._build_view(message_id, ended=True))
                self.active_giveaways.pop(message_id, None)
                _delete_giveaway(message_id)
                return

            actual_winners = min(winner_count, len(participants))
            winner_ids = random.sample(participants, actual_winners)
            winners = [guild.get_member(uid) for uid in winner_ids if guild.get_member(uid)]
            winner_mentions = [w.mention for w in winners if w]

            embed = self._build_embed(prize, end_time, winner_count, host,
                                      participants=len(participants), ended=True,
                                      winner_mentions=winner_mentions)
            await message.edit(embed=embed, view=self._build_view(message_id, ended=True))
            await channel.send(
                f"🎉 **GIVEAWAY SELESAI!**\n"
                f"Hadiah: **{prize}**\n"
                f"Pemenang: {' '.join(winner_mentions) if winner_mentions else 'Tidak ada'}\n"
                f"Hubungi {host.mention if host else 'admin'} untuk klaim hadiah!"
            )

            # Log ke channel
            log_ch = guild.get_channel(LOG_CHANNEL_ID)
            if log_ch:
                log_embed = discord.Embed(title="GIVEAWAY SELESAI", color=0xFF6B6B,
                                          timestamp=datetime.datetime.now(datetime.timezone.utc))
                log_embed.add_field(name="Hadiah", value=prize, inline=True)
                log_embed.add_field(name="Peserta", value=str(len(participants)), inline=True)
                log_embed.add_field(name="Pemenang", value="\n".join(winner_mentions) or "-", inline=False)
                log_embed.set_footer(text=STORE_NAME)
                await log_ch.send(embed=log_embed)

            self.active_giveaways.pop(message_id, None)
            _delete_giveaway(message_id)
        except Exception as e:
            print(f"[Giveaway] End error: {e}")

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        custom_id = interaction.data.get('custom_id', '')
        if not custom_id.startswith('giveaway_join_'):
            return
        message_id = int(custom_id.replace('giveaway_join_', ''))
        user_id = interaction.user.id
        if message_id not in self.active_giveaways:
            await interaction.response.send_message("Giveaway ini sudah selesai!", ephemeral=True)
            return
        data = self.active_giveaways[message_id]
        participants = data.setdefault('participants', set())
        if user_id in participants:
            participants.discard(user_id)
            await interaction.response.send_message("Kamu keluar dari giveaway.", ephemeral=True)
        else:
            participants.add(user_id)
            await interaction.response.send_message("Kamu sudah terdaftar! Semoga menang 🎉", ephemeral=True)
        _update_participants(message_id, participants)
        try:
            host = interaction.guild.get_member(data['host_id'])
            embed = self._build_embed(data['prize'], data['end_time'], data['winners'],
                                      host, participants=len(participants),
                                      sponsor=data.get('sponsor'), image_url=data.get('image_url'))
            await interaction.message.edit(embed=embed)
        except Exception:
            pass

    @app_commands.command(name="giveaway", description="[ADMIN] Mulai giveaway baru")
    @app_commands.describe(hadiah="Hadiah yang akan diberikan", durasi="Durasi: 10m / 2h / 1d", pemenang="Jumlah pemenang", sponsor="Nama sponsor (opsional)", image="URL banner/gambar hadiah (opsional)")
    async def giveaway(self, interaction: discord.Interaction, hadiah: str, durasi: str, pemenang: int = 1, sponsor: str = None, image: str = None):
        if not any(r.id == ADMIN_ROLE_ID for r in interaction.user.roles):
            await interaction.response.send_message("Admin only!", ephemeral=True)
            return
        seconds = parse_duration(durasi)
        if seconds <= 0:
            await interaction.response.send_message("Format durasi salah! Contoh: `10m`, `2h`, `1d`", ephemeral=True)
            return
        if pemenang < 1:
            await interaction.response.send_message("Jumlah pemenang minimal 1!", ephemeral=True)
            return
        end_time = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=seconds)
        embed = self._build_embed(hadiah, end_time, pemenang, interaction.user, participants=0, sponsor=sponsor, image_url=image)
        await interaction.response.send_message("Giveaway dimulai!", ephemeral=True)
        msg = await interaction.channel.send(embed=embed)
        giveaway_data = {
            'prize': hadiah, 'end_time': end_time, 'winners': pemenang,
            'host_id': interaction.user.id, 'channel_id': interaction.channel.id,
            'guild_id': interaction.guild.id, 'participants': set(),
            'sponsor': sponsor, 'image_url': image,
        }
        self.active_giveaways[msg.id] = giveaway_data
        _save_giveaway(msg.id, interaction.channel.id, interaction.guild.id,
                       hadiah, end_time, pemenang, interaction.user.id, set(), sponsor=sponsor, image_url=image)
        await msg.edit(view=self._build_view(msg.id))
        async def auto_end():
            await asyncio.sleep(seconds)
            if msg.id in self.active_giveaways:
                await self._end_giveaway(msg.id, interaction.channel.id, interaction.guild.id,
                                         hadiah, pemenang, interaction.user.id)
        self.bot.loop.create_task(auto_end())

    @app_commands.command(name="giveaway_end", description="[ADMIN] Akhiri giveaway lebih awal")
    @app_commands.describe(message_id="ID pesan giveaway")
    async def giveaway_end(self, interaction: discord.Interaction, message_id: str):
        if not any(r.id == ADMIN_ROLE_ID for r in interaction.user.roles):
            await interaction.response.send_message("Admin only!", ephemeral=True)
            return
        msg_id = int(message_id)
        if msg_id not in self.active_giveaways:
            await interaction.response.send_message("Giveaway tidak ditemukan!", ephemeral=True)
            return
        data = self.active_giveaways[msg_id]
        await interaction.response.send_message("Mengakhiri giveaway...", ephemeral=True)
        await self._end_giveaway(msg_id, data['channel_id'], data['guild_id'],
                                 data['prize'], data['winners'], data['host_id'])

    @app_commands.command(name="giveaway_reroll", description="[ADMIN] Reroll pemenang giveaway")
    @app_commands.describe(message_id="ID pesan giveaway")
    async def giveaway_reroll(self, interaction: discord.Interaction, message_id: str):
        if not any(r.id == ADMIN_ROLE_ID for r in interaction.user.roles):
            await interaction.response.send_message("Admin only!", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        try:
            msg_id = int(message_id)
            data = self.active_giveaways.get(msg_id)
            if not data:
                # Cek dari DB (giveaway sudah selesai)
                conn = get_conn()
                c = conn.cursor()
                c.execute('SELECT participants FROM giveaways WHERE message_id=?', (msg_id,))
                row = c.fetchone()
                conn.close()
                if row and row['participants']:
                    parts = [int(p) for p in row['participants'].split(',') if p.strip()]
                    data = {'participants': set(parts)}
            if data and data.get('participants'):
                winner_id = random.choice(list(data['participants']))
                winner = interaction.guild.get_member(winner_id)
                if winner:
                    await interaction.channel.send(f"🎉 **REROLL!** Pemenang baru: {winner.mention}\nSelamat! Hubungi admin untuk klaim hadiah.")
                    await interaction.followup.send("Reroll selesai!", ephemeral=True)
                else:
                    await interaction.followup.send("Pemenang tidak ditemukan di server.", ephemeral=True)
            else:
                await interaction.followup.send("Data peserta tidak ditemukan!", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"Error: {e}", ephemeral=True)

    @app_commands.command(name="giveaway_list", description="[ADMIN] Lihat giveaway aktif")
    async def giveaway_list(self, interaction: discord.Interaction):
        if not any(r.id == ADMIN_ROLE_ID for r in interaction.user.roles):
            await interaction.response.send_message("Admin only!", ephemeral=True)
            return
        if not self.active_giveaways:
            await interaction.response.send_message("📝 Tidak ada giveaway aktif.", ephemeral=True)
            return
        embed = discord.Embed(title="GIVEAWAY AKTIF", color=0xFF6B6B)
        for msg_id, data in self.active_giveaways.items():
            embed.add_field(
                name=data['prize'],
                value=f"ID: `{msg_id}`\nBerakhir: <t:{int(data['end_time'].timestamp())}:R>\nPemenang: {data['winners']} orang\nPeserta: {len(data.get('participants', set()))}",
                inline=False,
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(GiveawayCog(bot))
