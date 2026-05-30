import discord
import random
from discord.ext import commands
import os
from dotenv import load_dotenv
load_dotenv()

try:
    TESTIMONI_CHANNEL_ID = int(os.getenv("TESTIMONI_CHANNEL_ID", 0))
except Exception:
    TESTIMONI_CHANNEL_ID = 0

REPLIES = [
    "Makasih testimoninyaa, beneran berarti banget buat kita!",
    "Wah seneng banget bacanya, terima kasih udah mau nulis ini~",
    "Appreciate banget ya, makasih udah percaya Cellyn Store!",
    "Makasih banyak! Semoga next order makin lancar juga.",
    "Hehe makasih testimoninyaa, jadi semangat nih!",
    "Seneng banget deh, terima kasih udah mau share pengalamannya!",
    "Makasih ya, ini jadi motivasi kita buat terus improve!",
    "Terima kasih banyak! Ditunggu order berikutnya ya.",
    "Wah makasih udah nulis testimoni, beneran berarti!",
    "Seneng banget bisa bantu, makasih testimoninyaa!",
    "Makasih udah percaya kita, semoga puas terus ya!",
    "Terima kasih! Jangan lupa rekomendasiin ke temen-temen juga ya.",
    "Makasih banyak ya sudah mau berbagi, kita jadi makin semangat!",
    "Wah ini bikin happy banget, makasih testimoninyaa!",
    "Terima kasih udah luangin waktu buat kasih testimoni, means a lot!",
    "Makasih ya! Semoga next transaksi makin cepet dan lancar.",
    "Beneran makasih, testimoni kayak gini yang bikin kita terus mau berkembang.",
    "Hehe makasih sudah mau nulis, seneng banget bacanya!",
    "Terima kasih banyak! Kalau ada yang perlu dibantu lagi, langsung aja.",
    "Makasih testimoninyaa, semoga bisa terus melayani dengan baik!",
    "Wah terima kasih, ini jadi pengingat buat kita terus jaga kualitas!",
    "Makasih ya udah mau share, sangat diapresiasi!",
    "Seneng banget deh dengernya, makasih banyak!",
    "Terima kasih sudah mempercayakan transaksinya ke Cellyn Store!",
    "Makasih testimoninyaa! Semoga bisa ketemu lagi di order berikutnya.",
]

class Testimoni(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        if not TESTIMONI_CHANNEL_ID:
            return
        if message.channel.id != TESTIMONI_CHANNEL_ID:
            return
        reply = random.choice(REPLIES)
        await message.reply(reply)

async def setup(bot: commands.Bot):
    await bot.add_cog(Testimoni(bot))
    print("Cog Testimoni siap.")
