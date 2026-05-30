import asyncio
import datetime
import discord
from discord import app_commands
from discord.ext import commands, tasks
from utils.config import ADMIN_ROLE_ID
from utils.db import get_conn


def _get_setting(key):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT value FROM bot_state WHERE key=?", (key,))
    row = c.fetchone()
    conn.close()
    return row['value'] if row else None


def _set_setting(key, value):
    conn = get_conn()
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO bot_state (key, value) VALUES (?,?)", (key, value))
    conn.commit()
    conn.close()


class ServerStatsCog(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._stats_channel_id = None
        self.update_stats.start()

    def cog_unload(self):
        self.update_stats.cancel()

    async def cog_load(self):
        self.bot.loop.create_task(self._load_settings())

    async def _load_settings(self):
        await self.bot.wait_until_ready()
        ch_id = _get_setting("stats_channel_id")
        if ch_id:
            self._stats_channel_id = int(ch_id)
            print(f"[Stats] Channel: {self._stats_channel_id}")

    @tasks.loop(minutes=10)
    async def update_stats(self):
        await self.bot.wait_until_ready()
        if not self._stats_channel_id:
            return
        try:
            channel = self.bot.get_channel(self._stats_channel_id)
            if not channel:
                return
            member_count = sum(1 for m in channel.guild.members if not m.bot)
            new_name = f"🌐 Members: {member_count}"
            if channel.name != new_name:
                await channel.edit(name=new_name)
        except Exception as e:
            print(f"[Stats] Update error: {e}")

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        await self._force_update(member.guild)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        await self._force_update(member.guild)

    async def _force_update(self, guild: discord.Guild):
        if not self._stats_channel_id:
            return
        try:
            channel = guild.get_channel(self._stats_channel_id)
            if not channel:
                return
            member_count = sum(1 for m in guild.members if not m.bot)
            new_name = f"🌐 Members: {member_count}"
            if channel.name != new_name:
                await channel.edit(name=new_name)
        except Exception as e:
            print(f"[Stats] Force update error: {e}")

    @app_commands.command(name="setstatschannel", description="[ADMIN] Set voice channel untuk statistik member")
    @app_commands.describe(channel="Voice channel yang akan menampilkan jumlah member")
    async def set_stats_channel(self, interaction: discord.Interaction, channel: discord.VoiceChannel):
        if not any(r.id == ADMIN_ROLE_ID for r in interaction.user.roles):
            await interaction.response.send_message("❌ Admin only!", ephemeral=True)
            return
        self._stats_channel_id = channel.id
        _set_setting("stats_channel_id", str(channel.id))
        member_count = sum(1 for m in interaction.guild.members if not m.bot)
        await channel.edit(name=f"🌐 Members: {member_count}")
        await interaction.response.send_message(
            f"✅ Stats channel diset ke {channel.mention}\nSekarang menampilkan **{member_count} members**.",
            ephemeral=True
        )

    @app_commands.command(name="unsetstatschannel", description="[ADMIN] Matikan fitur stats channel")
    async def unset_stats_channel(self, interaction: discord.Interaction):
        if not any(r.id == ADMIN_ROLE_ID for r in interaction.user.roles):
            await interaction.response.send_message("❌ Admin only!", ephemeral=True)
            return
        self._stats_channel_id = None
        _set_setting("stats_channel_id", "")
        await interaction.response.send_message("✅ Stats channel dinonaktifkan.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(ServerStatsCog(bot))
