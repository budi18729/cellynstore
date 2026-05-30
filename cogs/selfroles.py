import discord
from discord.ext import commands
from utils.config import ADMIN_ROLE_ID, SELFROLES_CHANNEL_ID, STORE_NAME

THUMBNAIL = "https://i.imgur.com/CWtUCzj.png"

ROLES = [
    {"emoji": "<a:fish_dance:1478904201202634855>", "label": "Fish It",          "role_id": 1478902226616582144},
    {"emoji": "<:vd:1478903981895057579>",          "label": "Violens District",  "role_id": 1478902150586302495},
    {"emoji": "<:ml1:1478904312779247870>",         "label": "Mobile Legends",    "role_id": 1478902297147867317},
    {"emoji": "🍀",                                 "label": "INFO PT PT",             "role_id": 1478607256437260388},
    {"emoji": "🎉",                                 "label": "Giveaway",          "role_id": 1479146345620181043},
    {"emoji": "<:RobloxVerifiedBadge:1479498873641762837>", "label": "Roblox", "role_id": 1479455170520682530},
    {"emoji": "<:pubg:1479458873641762838>",        "label": "PUBG",             "role_id": 1479458873641762838},
]

class SelfRolesView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        for r in ROLES:
            self.add_item(SelfRoleButton(r["emoji"], r["label"], r["role_id"]))

class SelfRoleButton(discord.ui.Button):
    def __init__(self, emoji, label, role_id):
        super().__init__(
            style=discord.ButtonStyle.secondary,
            label="\u200b",
            emoji=emoji,
            custom_id=f"selfrole_{role_id}"
        )
        self.role_id = role_id
        self.role_label = label

    async def callback(self, interaction: discord.Interaction):
        role = interaction.guild.get_role(self.role_id)
        if not role:
            await interaction.response.send_message("Role tidak ditemukan!", ephemeral=True)
            return

        if role in interaction.user.roles:
            await interaction.user.remove_roles(role)
            await interaction.response.send_message(f"Role **{self.role_label}** berhasil dilepas.", ephemeral=True)
        else:
            await interaction.user.add_roles(role)
            await interaction.response.send_message(f"Role **{self.role_label}** berhasil ditambahkan!", ephemeral=True)

class SelfRoles(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="selfroles")
    async def selfroles_cmd(self, ctx):
        if not any(r.id == ADMIN_ROLE_ID for r in ctx.author.roles):
            return
        await ctx.message.delete()

        ch = ctx.guild.get_channel(SELFROLES_CHANNEL_ID)
        if not ch:
            await ctx.send("Channel self roles tidak ditemukan!", delete_after=5)
            return

        async for msg in ch.history(limit=50):
            if msg.author == self.bot.user:
                try:
                    await msg.delete()
                except Exception:
                    pass

        embed = discord.Embed(
            title="PILIH ROLE KAMU",
            description=(
                "Ambil role game kamu, biar gampang cari teman mabar!\n"
                "Bisa ambil lebih dari satu. Klik tombol untuk toggle role.\n\n"
                "<a:fish_dance:1478904201202634855> **Fish It** — Main FishIt\n"
                "<:vd:1478903981895057579> **Violens District** — Main Violens District\n"
                "<:ml1:1478904312779247870> **Mobile Legends** — Main Mobile Legends\n"
                "🍀 **INFO PT PT** — PT PT PING!\n"
                "🎉 **Giveaway** — Notifikasi Giveaway\n"
                "<:RobloxVerifiedBadge:1479498873641762837> **Roblox** — Role Roblox Player\n"
                "<:pubg:1479458873641762838> **PUBG** — Role PUBG Player"
            ),
            color=0x00FF00
        )
        embed.set_footer(text=STORE_NAME)
        await ch.send(embed=embed, view=SelfRolesView())
        await ctx.send(f"Embed self roles dikirim ke {ch.mention}", delete_after=5)

async def setup(bot):
    await bot.add_cog(SelfRoles(bot))
    bot.add_view(SelfRolesView())
    print("Cog SelfRoles siap.")
