content = open('cogs/midman.py').read()
old = '        ch = ctx.guild.get_channel(MIDMAN_CHANNEL_ID)\n        embed = discord.Embed('
new = '        ch = ctx.guild.get_channel(MIDMAN_CHANNEL_ID)\n\n        # Hapus semua pesan bot lama di channel\n        async for msg in ch.history(limit=50):\n            if msg.author == self.bot.user:\n                try:\n                    await msg.delete()\n                except:\n                    pass\n\n        embed = discord.Embed('
open('cogs/midman.py', 'w').write(content.replace(old, new))
print("Done!")
