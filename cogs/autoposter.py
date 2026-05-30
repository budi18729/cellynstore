import asyncio
import aiohttp
import discord
from discord.ext import commands, tasks
from utils.autoposter_settings import (
    get_autopost_tasks,
    update_autopost_counter,
    update_autopost_last_post,
    log_autopost_history,
    init_autopost_tables
)
from utils.config import ADMIN_ROLE_ID

LOOP_INTERVAL = 60

class AutoPosterCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        init_autopost_tables()
        print("Cog AutoPoster siap.")
        self.autopost_loop.start()

    def cog_unload(self):
        self.autopost_loop.cancel()

    @tasks.loop(seconds=LOOP_INTERVAL)
    async def autopost_loop(self):
        tasks = get_autopost_tasks()
        for task in tasks:
            if not task.get("is_active"):
                continue

            channel_ids = [c.strip() for c in task["channel_id"].split(",") if c.strip()]
            new_counter = task.get("loop_counter", 0) + LOOP_INTERVAL
            threshold = task["interval_minutes"] * 60

            if new_counter >= threshold:
                all_success = True
                for cid in channel_ids:
                    success = await self._post_to_channel(cid, task["message"], task.get("user_token", ""))
                    if not success:
                        all_success = False
                log_autopost_history(task["id"], task["message"], "success" if all_success else "failed")
                if all_success:
                    update_autopost_last_post(task["id"])
                else:
                    update_autopost_counter(task["id"], 0)
            else:
                update_autopost_counter(task["id"], new_counter)

    @autopost_loop.before_loop
    async def before_autopost_loop(self):
        await self.bot.wait_until_ready()
        print("[AUTOPOST] Loop ready...")

    async def _post_to_channel(self, channel_id: str, message: str, user_token: str):
        try:
            headers = {
                "Authorization": user_token,
                "Content-Type": "application/json"
            }
            payload = {"content": message}
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"https://discord.com/api/v9/channels/{channel_id}/messages",
                    json=payload,
                    headers=headers
                ) as resp:
                    return resp.status in (200, 201)
        except Exception:
            return False

async def setup(bot):
    await bot.add_cog(AutoPosterCog(bot))
