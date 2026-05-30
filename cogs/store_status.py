import datetime

from discord.ext import commands, tasks

from utils.config import GUILD_ID
from utils.store_hours import WIB, is_store_open


STATUS_VOICE_CHANNEL_ID = 1476382504838500362
OPEN_NAME = "🟢 STATUS : OPEN"
CLOSE_NAME = "🔴 STATUS : CLOSE"


class StoreStatusCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._status_loop.start()
        self.bot.loop.create_task(self._initial_sync())

    def cog_unload(self):
        self._status_loop.cancel()

    async def _initial_sync(self):
        await self.bot.wait_until_ready()
        await self._apply_status()

    @tasks.loop(
        time=[
            datetime.time(hour=9, minute=0, tzinfo=WIB),
            datetime.time(hour=23, minute=0, tzinfo=WIB),
        ]
    )
    async def _status_loop(self):
        await self._apply_status()

    @_status_loop.before_loop
    async def _before_status_loop(self):
        await self.bot.wait_until_ready()

    async def _apply_status(self):
        guild = self.bot.get_guild(GUILD_ID)
        if not guild:
            return

        store_open = is_store_open()
        new_name = OPEN_NAME if store_open else CLOSE_NAME
        channel = guild.get_channel(STATUS_VOICE_CHANNEL_ID)
        try:
            if channel and getattr(channel, "name", None) != new_name:
                await channel.edit(name=new_name)
        except Exception as e:
            print(f"[StoreStatus] Update error: {e}")

        await self._refresh_catalogs(guild)

    async def _refresh_catalogs(self, guild):
        # Update catalog messages so their buttons are enabled/disabled based on store status.
        try:
            robux_cog = self.bot.cogs.get("RobuxStore")
            if robux_cog and hasattr(robux_cog, "refresh_catalog"):
                await robux_cog.refresh_catalog()
        except Exception as e:
            print(f"[StoreStatus] Refresh robux catalog error: {e}")

        try:
            gp_cog = self.bot.cogs.get("GPStore")
            if gp_cog and hasattr(gp_cog, "refresh_catalog"):
                await gp_cog.refresh_catalog()
        except Exception as e:
            print(f"[StoreStatus] Refresh GP catalog error: {e}")

        try:
            vilog_cog = self.bot.cogs.get("Vilog")
            if vilog_cog and hasattr(vilog_cog, "refresh_embed"):
                await vilog_cog.refresh_embed(guild)
        except Exception as e:
            print(f"[StoreStatus] Refresh vilog catalog error: {e}")

        try:
            lainnya_cog = self.bot.cogs.get("LainnyaStore")
            if lainnya_cog and hasattr(lainnya_cog, "refresh_catalog"):
                await lainnya_cog.refresh_catalog()
        except Exception as e:
            print(f"[StoreStatus] Refresh lainnya catalog error: {e}")

        try:
            ml_cog = self.bot.cogs.get("MLStore")
            if ml_cog and hasattr(ml_cog, "refresh_catalog"):
                await ml_cog.refresh_catalog()
        except Exception:
            pass

        try:
            midman_cog = self.bot.cogs.get("Midman")
            if midman_cog and hasattr(midman_cog, "refresh_open_embed"):
                await midman_cog.refresh_open_embed()
        except Exception:
            pass


async def setup(bot: commands.Bot):
    await bot.add_cog(StoreStatusCog(bot))
