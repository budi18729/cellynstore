import asyncio
import datetime
import sqlite3
import discord
from discord import app_commands
from discord.ext import commands
from utils.config import ADMIN_ROLE_ID, STORE_NAME, LOG_CHANNEL_ID
from utils.db import get_conn

THUMBNAIL = "https://i.imgur.com/CWtUCzj.png"
MAX_OPTIONS = 5


# ─── DB HELPERS ───────────────────────────────────────────────────────────────

def _init_poll_table():
    conn = get_conn()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS polls (
            message_id  INTEGER PRIMARY KEY,
            channel_id  INTEGER,
            guild_id    INTEGER,
            question    TEXT,
            options     TEXT,
            end_time    TEXT,
            host_id     INTEGER,
            votes       TEXT DEFAULT '',
            multiple    INTEGER DEFAULT 0,
            ended       INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()


def _save_poll(msg_id, channel_id, guild_id, question, options, end_time, host_id, multiple):
    conn = get_conn()
    c = conn.cursor()
    options_str = '||'.join(options)
    votes_str = '|'.join([''] * len(options))
    end_str = end_time.isoformat() if end_time else ''
    c.execute('''
        INSERT OR REPLACE INTO polls
        (message_id, channel_id, guild_id, question, options, end_time, host_id, votes, multiple, ended)
        VALUES (?,?,?,?,?,?,?,?,?,0)
    ''', (msg_id, channel_id, guild_id, question, options_str, end_str, host_id, votes_str, int(multiple)))
    conn.commit()
    conn.close()


def _update_votes(msg_id, votes):
    conn = get_conn()
    c = conn.cursor()
    votes_str = '|'.join(','.join(str(u) for u in uids) for uids in votes)
    c.execute('UPDATE polls SET votes=? WHERE message_id=?', (votes_str, msg_id))
    conn.commit()
    conn.close()


def _mark_ended(msg_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute('UPDATE polls SET ended=1 WHERE message_id=?', (msg_id,))
    conn.commit()
    conn.close()


def _delete_poll(msg_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute('DELETE FROM polls WHERE message_id=?', (msg_id,))
    conn.commit()
    conn.close()


def _load_polls():
    conn = get_conn()
    c = conn.cursor()
    c.execute('SELECT * FROM polls WHERE ended=0')
    rows = c.fetchall()
    conn.close()
    result = {}
    for row in rows:
        options = row['options'].split('||')
        raw_votes = row['votes'].split('|')
        votes = []
        for seg in raw_votes:
            uids = set(int(x) for x in seg.split(',') if x.strip())
            votes.append(uids)
        end_time = datetime.datetime.fromisoformat(row['end_time']) if row['end_time'] else None
        result[row['message_id']] = {
            'channel_id': row['channel_id'],
            'guild_id': row['guild_id'],
            'question': row['question'],
            'options': options,
            'end_time': end_time,
            'host_id': row['host_id'],
            'votes': votes,
            'multiple': bool(row['multiple']),
        }
    return result


# ─── DURATION PARSER ──────────────────────────────────────────────────────────

def parse_duration(s: str) -> int:
    s = s.strip().lower()
    units = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}
    if s and s[-1] in units:
        try:
            return int(s[:-1]) * units[s[-1]]
        except ValueError:
            return 0
    return 0


# ─── PROGRESS BAR ─────────────────────────────────────────────────────────────

def _progress_bar(count, total, length=10):
    if total == 0:
        filled = 0
    else:
        filled = round(count / total * length)
    bar = '█' * filled + '░' * (length - filled)
    pct = f"{count / total * 100:.1f}%" if total > 0 else "0%"
    return f"`{bar}` {pct}"


# ─── COG ──────────────────────────────────────────────────────────────────────

class PollCog(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.active_polls = {}
        _init_poll_table()

    async def cog_load(self):
        self.bot.loop.create_task(self._restore_polls())

    async def _restore_polls(self):
        await self.bot.wait_until_ready()
        try:
            polls = _load_polls()
            now = datetime.datetime.now(datetime.timezone.utc)
            restored = 0
            for msg_id, data in polls.items():
                self.active_polls[msg_id] = data
                if data['end_time']:
                    remaining = (data['end_time'] - now).total_seconds()
                    if remaining > 0:
                        self.bot.loop.create_task(self._resume_poll(msg_id, remaining, data))
                        restored += 1
                    else:
                        self.bot.loop.create_task(
                            self._end_poll(msg_id, data['channel_id'], data['guild_id'])
                        )
                else:
                    restored += 1
            if restored:
                print(f"[Poll] Restored {restored} active poll(s)")
        except Exception as e:
            print(f"[Poll] Restore error: {e}")

    async def _resume_poll(self, msg_id, remaining, data):
        await asyncio.sleep(remaining)
        if msg_id in self.active_polls:
            await self._end_poll(msg_id, data['channel_id'], data['guild_id'])

    def _build_embed(self, data, ended=False):
        question = data['question']
        options = data['options']
        votes = data['votes']
        end_time = data.get('end_time')
        host_id = data.get('host_id')
        multiple = data.get('multiple', False)

        total_votes = sum(len(v) for v in votes)
        color = 0x95a5a6 if ended else 0x3498DB

        embed = discord.Embed(
            title=f"📊 {'[SELESAI] ' if ended else ''}POLL",
            description=f"**{question}**",
            color=color,
            timestamp=datetime.datetime.now(datetime.timezone.utc),
        )

        emojis = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣']
        option_lines = []
        for i, (opt, v) in enumerate(zip(options, votes)):
            bar = _progress_bar(len(v), total_votes)
            option_lines.append(f"{emojis[i]} **{opt}**\n{bar} ({len(v)} vote)")

        embed.add_field(name="Pilihan", value='\n\n'.join(option_lines), inline=False)
        embed.add_field(name="Total Vote", value=str(total_votes), inline=True)
        embed.add_field(name="Mode", value="Multi pilih" if multiple else "1 pilihan", inline=True)

        if ended:
            embed.add_field(name="Status", value="✅ SELESAI", inline=True)
            if total_votes > 0:
                max_votes = max(len(v) for v in votes)
                winners = [options[i] for i, v in enumerate(votes) if len(v) == max_votes]
                embed.add_field(
                    name="🏆 Hasil Terbanyak",
                    value='\n'.join(f"**{w}** ({max_votes} vote)" for w in winners),
                    inline=False
                )
        else:
            if end_time:
                embed.add_field(
                    name="Berakhir",
                    value=f"<t:{int(end_time.timestamp())}:R>",
                    inline=True
                )
            else:
                embed.add_field(name="Berakhir", value="Manual (admin)", inline=True)

        if host_id:
            embed.set_footer(text=f"{STORE_NAME} • Poll" + (" • Selesai" if ended else ""))

        return embed

    def _build_view(self, message_id, options, ended=False):
        view = discord.ui.View(timeout=None)
        emojis = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣']
        for i, opt in enumerate(options):
            btn = discord.ui.Button(
                label=opt[:50],
                emoji=emojis[i],
                style=discord.ButtonStyle.primary if not ended else discord.ButtonStyle.secondary,
                custom_id=f"poll_vote_{message_id}_{i}",
                disabled=ended,
                row=i // 3,
            )
            view.add_item(btn)
        return view

    async def _end_poll(self, message_id, channel_id, guild_id):
        try:
            data = self.active_polls.get(message_id)
            if not data:
                return
            guild = self.bot.get_guild(guild_id)
            channel = self.bot.get_channel(channel_id)
            if not channel:
                return
            try:
                message = await channel.fetch_message(message_id)
            except Exception:
                self.active_polls.pop(message_id, None)
                _mark_ended(message_id)
                return

            embed = self._build_embed(data, ended=True)
            await message.edit(embed=embed, view=self._build_view(message_id, data['options'], ended=True))

            total_votes = sum(len(v) for v in data['votes'])
            result_lines = []
            for i, (opt, v) in enumerate(zip(data['options'], data['votes'])):
                result_lines.append(f"**{opt}**: {len(v)} vote")

            await channel.send(
                f"📊 **POLL SELESAI!**\n"
                f"Pertanyaan: **{data['question']}**\n"
                f"Total vote: **{total_votes}**\n" +
                '\n'.join(result_lines)
            )

            # Log
            if guild:
                log_ch = guild.get_channel(LOG_CHANNEL_ID)
                if log_ch:
                    log_embed = discord.Embed(
                        title="POLL SELESAI",
                        description=f"**{data['question']}**",
                        color=0x3498DB,
                        timestamp=datetime.datetime.now(datetime.timezone.utc)
                    )
                    log_embed.add_field(name="Total Vote", value=str(total_votes), inline=True)
                    log_embed.set_footer(text=STORE_NAME)
                    await log_ch.send(embed=log_embed)

            self.active_polls.pop(message_id, None)
            _mark_ended(message_id)
        except Exception as e:
            print(f"[Poll] End error: {e}")

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        custom_id = interaction.data.get('custom_id', '')
        if not custom_id.startswith('poll_vote_'):
            return

        parts = custom_id.split('_')
        if len(parts) < 4:
            return

        message_id = int(parts[2])
        option_idx = int(parts[3])
        user_id = interaction.user.id

        if message_id not in self.active_polls:
            await interaction.response.send_message("Poll ini sudah selesai!", ephemeral=True)
            return

        data = self.active_polls[message_id]
        votes = data['votes']
        multiple = data['multiple']
        option_name = data['options'][option_idx]

        if multiple:
            # Toggle pilihan
            if user_id in votes[option_idx]:
                votes[option_idx].discard(user_id)
                msg = f"Kamu membatalkan pilihan **{option_name}**."
            else:
                votes[option_idx].add(user_id)
                msg = f"Kamu memilih **{option_name}**! ✅"
        else:
            # Cek apakah sudah vote opsi ini
            if user_id in votes[option_idx]:
                votes[option_idx].discard(user_id)
                msg = f"Kamu membatalkan pilihan **{option_name}**."
            else:
                # Hapus vote lama dari opsi lain
                for i, v in enumerate(votes):
                    v.discard(user_id)
                votes[option_idx].add(user_id)
                msg = f"Kamu memilih **{option_name}**! ✅"

        _update_votes(message_id, votes)

        await interaction.response.send_message(msg, ephemeral=True)

        try:
            embed = self._build_embed(data)
            await interaction.message.edit(embed=embed)
        except Exception:
            pass

    # ─── SLASH COMMANDS ───────────────────────────────────────────────────────

    @app_commands.command(name="poll", description="Buat poll baru")
    @app_commands.describe(
        pertanyaan="Pertanyaan poll",
        opsi="Opsi dipisah koma, maks 5 (contoh: Opsi A, Opsi B, Opsi C)",
        durasi="Durasi opsional: 10m / 2h / 1d (kosongkan = manual)",
        multiple="Boleh pilih lebih dari 1 opsi?"
    )
    @app_commands.choices(multiple=[
        app_commands.Choice(name="Ya (multi pilih)", value="ya"),
        app_commands.Choice(name="Tidak (1 pilihan)", value="tidak"),
    ])
    async def poll(self, interaction: discord.Interaction, pertanyaan: str, opsi: str,
                   durasi: str = None, multiple: str = "tidak"):

        options = [o.strip() for o in opsi.split(',') if o.strip()]
        if len(options) < 2:
            await interaction.response.send_message("Minimal 2 opsi!", ephemeral=True)
            return
        if len(options) > MAX_OPTIONS:
            await interaction.response.send_message(f"Maksimal {MAX_OPTIONS} opsi!", ephemeral=True)
            return

        end_time = None
        seconds = 0
        if durasi:
            seconds = parse_duration(durasi)
            if seconds <= 0:
                await interaction.response.send_message(
                    "Format durasi salah! Contoh: `10m`, `2h`, `1d`", ephemeral=True)
                return
            end_time = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=seconds)

        is_multiple = multiple == "ya"

        data = {
            'question': pertanyaan,
            'options': options,
            'end_time': end_time,
            'host_id': interaction.user.id,
            'channel_id': interaction.channel.id,
            'guild_id': interaction.guild.id,
            'votes': [set() for _ in options],
            'multiple': is_multiple,
        }

        await interaction.response.send_message("Poll dibuat!", ephemeral=True)
        msg = await interaction.channel.send(
            embed=self._build_embed(data),
        )
        data['channel_id'] = interaction.channel.id
        self.active_polls[msg.id] = data
        _save_poll(msg.id, interaction.channel.id, interaction.guild.id,
                   pertanyaan, options, end_time, interaction.user.id, is_multiple)
        await msg.edit(view=self._build_view(msg.id, options))

        if seconds > 0:
            async def auto_end():
                await asyncio.sleep(seconds)
                if msg.id in self.active_polls:
                    await self._end_poll(msg.id, interaction.channel.id, interaction.guild.id)
            self.bot.loop.create_task(auto_end())

    @app_commands.command(name="poll_end", description="[ADMIN] Akhiri poll lebih awal")
    @app_commands.describe(message_id="ID pesan poll")
    async def poll_end(self, interaction: discord.Interaction, message_id: str):
        if not any(r.id == ADMIN_ROLE_ID for r in interaction.user.roles):
            await interaction.response.send_message("Admin only!", ephemeral=True)
            return
        msg_id = int(message_id)
        if msg_id not in self.active_polls:
            await interaction.response.send_message("Poll tidak ditemukan!", ephemeral=True)
            return
        data = self.active_polls[msg_id]
        await interaction.response.send_message("Mengakhiri poll...", ephemeral=True)
        await self._end_poll(msg_id, data['channel_id'], data['guild_id'])

    @app_commands.command(name="poll_list", description="[ADMIN] Lihat poll aktif")
    async def poll_list(self, interaction: discord.Interaction):
        if not any(r.id == ADMIN_ROLE_ID for r in interaction.user.roles):
            await interaction.response.send_message("Admin only!", ephemeral=True)
            return
        if not self.active_polls:
            await interaction.response.send_message("📝 Tidak ada poll aktif.", ephemeral=True)
            return
        embed = discord.Embed(title="POLL AKTIF", color=0x3498DB)
        for msg_id, data in self.active_polls.items():
            total = sum(len(v) for v in data['votes'])
            end_str = f"<t:{int(data['end_time'].timestamp())}:R>" if data['end_time'] else "Manual"
            embed.add_field(
                name=data['question'][:50],
                value=f"ID: `{msg_id}`\nBerakhir: {end_str}\nTotal vote: {total}\nMode: {'Multi' if data['multiple'] else 'Single'}",
                inline=False,
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(PollCog(bot))
