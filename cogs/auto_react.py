import asyncio
import random
import datetime
import discord
from discord import app_commands
from discord.ext import commands
from utils.config import ADMIN_ROLE_ID
from utils.db import get_conn


def _init_react_table():
    conn = get_conn()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS auto_react (
            channel_id  INTEGER PRIMARY KEY,
            emojis      TEXT,
            mode        TEXT DEFAULT 'staff'
        )
    ''')
    conn.commit()
    conn.close()


def _load_react():
    conn = get_conn()
    c = conn.cursor()
    c.execute('SELECT channel_id, emojis, mode FROM auto_react')
    rows = c.fetchall()
    conn.close()
    staff = {}
    all_users = {}
    for row in rows:
        emojis = row['emojis'].split(',') if row['emojis'] else []
        if row['mode'] == 'all':
            all_users[row['channel_id']] = emojis
        else:
            staff[row['channel_id']] = emojis
    return staff, all_users


def _save_react(channel_id, emojis, mode='staff'):
    conn = get_conn()
    c = conn.cursor()
    c.execute('INSERT OR REPLACE INTO auto_react (channel_id, emojis, mode) VALUES (?,?,?)',
              (channel_id, ','.join(emojis), mode))
    conn.commit()
    conn.close()


def _delete_react(channel_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute('DELETE FROM auto_react WHERE channel_id=?', (channel_id,))
    conn.commit()
    conn.close()


DEFAULT_EMOJIS = ["❤️", "🔥", "🚀", "👍", "⭐", "🎉", "👏", "💯"]


class AutoReactCog(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.staff_channels = {}   # channel_id: [emojis]  — reaksi khusus pesan admin
        self.all_channels = {}     # channel_id: [emojis]  — reaksi semua pesan
        self._last_react = {}      # cooldown per channel
        _init_react_table()

    async def cog_load(self):
        self.bot.loop.create_task(self._load())

    async def _load(self):
        await self.bot.wait_until_ready()
        self.staff_channels, self.all_channels = _load_react()
        print(f"[AutoReact] Loaded {len(self.staff_channels)} staff + {len(self.all_channels)} all-user channels")

    async def _do_react(self, message, emoji_list=None):
        if message.author.bot:
            return
        channel_id = message.channel.id
        now = datetime.datetime.now().timestamp()
        if now - self._last_react.get(channel_id, 0) < 3:
            return
        self._last_react[channel_id] = now
        if not emoji_list:
            emoji_list = list(DEFAULT_EMOJIS)
        await asyncio.sleep(random.uniform(1, 3))
        random.shuffle(emoji_list)
        for emoji in emoji_list[:10]:
            try:
                await message.add_reaction(emoji)
                await asyncio.sleep(random.uniform(0.5, 1))
            except Exception:
                continue

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        channel_id = message.channel.id
        # All-user react
        if channel_id in self.all_channels:
            await self._do_react(message, list(self.all_channels[channel_id]))
            return
        # Staff-only react
        if channel_id in self.staff_channels:
            is_admin = any(r.id == ADMIN_ROLE_ID for r in message.author.roles)
            if is_admin:
                await self._do_react(message, list(self.staff_channels[channel_id]))

    @app_commands.command(name="setreact", description="[ADMIN] Auto-react di channel ini (khusus pesan admin)")
    @app_commands.describe(emojis="Emoji pisah spasi (kosongkan = default)", disable="Matikan auto-react")
    async def set_react(self, interaction: discord.Interaction, emojis: str = None, disable: bool = False):
        if not any(r.id == ADMIN_ROLE_ID for r in interaction.user.roles):
            await interaction.response.send_message("❌ Admin only!", ephemeral=True)
            return
        channel_id = interaction.channel_id
        if disable:
            self.staff_channels.pop(channel_id, None)
            _delete_react(channel_id)
            await interaction.response.send_message(f"✅ Auto-react dimatikan di {interaction.channel.mention}")
            return
        emoji_list = emojis.split()[:20] if emojis else list(DEFAULT_EMOJIS)
        self.staff_channels[channel_id] = emoji_list
        _save_react(channel_id, emoji_list, 'staff')
        await interaction.response.send_message(
            f"✅ Auto-react aktif di {interaction.channel.mention} (khusus admin)\nEmoji: {' '.join(emoji_list)}"
        )

    @app_commands.command(name="setreactall", description="[ADMIN] Auto-react untuk SEMUA pesan di channel ini")
    @app_commands.describe(emojis="Emoji pisah spasi (kosongkan = default)", disable="Matikan auto-react")
    async def set_react_all(self, interaction: discord.Interaction, emojis: str = None, disable: bool = False):
        if not any(r.id == ADMIN_ROLE_ID for r in interaction.user.roles):
            await interaction.response.send_message("❌ Admin only!", ephemeral=True)
            return
        channel_id = interaction.channel_id
        if disable:
            self.all_channels.pop(channel_id, None)
            _delete_react(channel_id)
            await interaction.response.send_message(f"✅ Auto-react all dimatikan di {interaction.channel.mention}")
            return
        emoji_list = emojis.split()[:20] if emojis else list(DEFAULT_EMOJIS)
        self.all_channels[channel_id] = emoji_list
        _save_react(channel_id, emoji_list, 'all')
        await interaction.response.send_message(
            f"✅ Auto-react aktif di {interaction.channel.mention} (semua user)\nEmoji: {' '.join(emoji_list)}"
        )

    @app_commands.command(name="reactlist", description="[ADMIN] Lihat daftar channel auto-react")
    async def react_list(self, interaction: discord.Interaction):
        if not any(r.id == ADMIN_ROLE_ID for r in interaction.user.roles):
            await interaction.response.send_message("❌ Admin only!", ephemeral=True)
            return
        if not self.staff_channels and not self.all_channels:
            await interaction.response.send_message("📝 Belum ada channel dengan auto-react.", ephemeral=True)
            return
        embed = discord.Embed(title="AUTO-REACT AKTIF", color=0x7c5cbf)
        if self.staff_channels:
            embed.add_field(name="🔹 Khusus Admin (/setreact)", value="​", inline=False)
            for ch_id, emojis in self.staff_channels.items():
                ch = interaction.guild.get_channel(ch_id)
                embed.add_field(name=ch.mention if ch else str(ch_id),
                                value=' '.join(emojis), inline=False)
        if self.all_channels:
            embed.add_field(name="🔸 Semua User (/setreactall)", value="​", inline=False)
            for ch_id, emojis in self.all_channels.items():
                ch = interaction.guild.get_channel(ch_id)
                embed.add_field(name=ch.mention if ch else str(ch_id),
                                value=' '.join(emojis), inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(AutoReactCog(bot))
