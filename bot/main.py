# ===============================================================
# Script Name: main.py
# Script Location: /opt/RealmQuest/bot/main.py
# Date: 2026-01-26
# Version: 18.51.0 (RollWatcher start fix + channel persistence)
# ===============================================================

import discord
import logging
import os
import asyncio
import redis
import json
import time
import aiohttp
from discord.ext import commands, voice_recv
from discord.ui import Button, View
from core.config import DISCORD_TOKEN, API_URL, SCRIBE_URL
from core.sink import ZeroLatencySink
from core.roll_watcher import RollWatcher

from discord import opus
_orig = opus.Decoder.decode
def _safe(self, *args, **kwargs):
    try: return _orig(self, *args, **kwargs)
    except: return b'\x00' * 3840
opus.Decoder.decode = _safe

# --- PRODUCTION LOGGING ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-8s %(name)s %(message)s")
logging.getLogger("discord").setLevel(logging.WARNING)
logging.getLogger("discord.ext.voice_recv").setLevel(logging.ERROR) # Silent


# --- ROLL WATCHER STATE (persists via Redis) ---
# Canonical text channel is the one used when 'Listen' is activated.
# Stored under key 'rq_text_channel_id' so restarts do not drift.


intents = discord.Intents.default()
intents.message_content = True
intents.members = True   
intents.presences = True 
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# In-memory channel fallback (no drift): set when Listen/buttons is used.
ACTIVE_TEXT_CHANNEL_ID = None

# Redis connect hardening: try multiple hostnames if needed and log status.

def _connect_redis():
    url = os.getenv("REDIS_URL")
    candidates = []
    if url:
        candidates.append(url)
    # Common compose hostnames
    candidates += [
        "redis://rq-redis:6379/0",
        "redis://realmquest-redis:6379/0",
    ]
    for u in candidates:
        try:
            c = redis.from_url(u, decode_responses=True)
            c.ping()
            logging.getLogger("rq.redis").info(f"✅ Redis Connected: {u}")
            return c
        except Exception:
            continue
    logging.getLogger("rq.redis").warning("⚠️ Redis Unavailable - roll announcements will require Listen to set in-memory channel")
    return None

# Override r_client with hardened connect
r_client = _connect_redis()


async def sync_roster_to_redis(guild):
    if not r_client: return
    members = []
    for member in guild.members:
        if member.status == discord.Status.offline: continue
        role = "Player"
        if member.bot: role = "System"
        elif any(r.name.lower() in ["dm", "dungeon master", "gm"] for r in member.roles): role = "Dungeon Master"
        avatar_url = str(member.avatar.url) if member.avatar else "https://cdn.discordapp.com/embed/avatars/0.png"
        members.append({"id": str(member.id), "name": member.display_name, "status": str(member.status), "role": role, "avatar": avatar_url})
    try: r_client.set("discord_roster", json.dumps(members), ex=3600)
    except: pass

class Dashboard(View):
    def __init__(self, bot_sink=None):
        super().__init__(timeout=None)
        self.bot_sink = bot_sink

    @discord.ui.button(label="Roll Call", style=discord.ButtonStyle.secondary, emoji="📜", row=0)
    async def roll_call_btn(self, interaction: discord.Interaction, button: Button):
        if not interaction.guild.voice_client: return await interaction.response.send_message("❌ Not Connected.", delete_after=3)
        members = interaction.guild.voice_client.channel.members
        names = [f"• {m.display_name}" for m in members if not m.bot]
        await interaction.response.send_message(embed=discord.Embed(title=f"📜 Roll Call ({len(names)})", description="\n".join(names) or "None", color=0x95a5a6))

    @discord.ui.button(label="Listen", style=discord.ButtonStyle.success, emoji="🟢", row=0)
    async def listen_btn(self, interaction: discord.Interaction, button: Button):
        if not interaction.user.voice: return await interaction.response.send_message("❌ User not in voice.", delete_after=3)
        vc = interaction.guild.voice_client
        if not vc: vc = await interaction.user.voice.channel.connect(cls=voice_recv.VoiceRecvClient, self_deaf=False)
        elif vc.channel != interaction.user.voice.channel: await vc.move_to(interaction.user.voice.channel)
        
        if not vc.is_listening():
            vc.listen(ZeroLatencySink(bot, source_channel=interaction.channel))
            # Persist active narration/text channel (no drift)
            global ACTIVE_TEXT_CHANNEL_ID
            ACTIVE_TEXT_CHANNEL_ID = interaction.channel.id
            try:
                if r_client: r_client.set('rq_text_channel_id', str(interaction.channel.id))
            except Exception:
                pass
            await interaction.response.send_message("🎧 **Active.**", delete_after=3)
        else: await interaction.response.send_message("⚠️ Active.", delete_after=3)

    @discord.ui.button(label="Stop", style=discord.ButtonStyle.danger, emoji="🛑", row=0)
    async def stop_btn(self, interaction: discord.Interaction, button: Button):
        vc = interaction.guild.voice_client
        if vc: 
            if vc.is_listening(): vc.stop_listening()
            if vc.is_playing(): vc.stop()
            await interaction.response.send_message("🛑 **Stopped.**", delete_after=3)

    @discord.ui.button(label="Mute", style=discord.ButtonStyle.primary, emoji="🔇", row=1)
    async def mute_btn(self, interaction: discord.Interaction, button: Button):
        vc = interaction.guild.voice_client
        if vc and vc.is_listening() and isinstance(vc.sink, ZeroLatencySink):
            is_muted = vc.sink.toggle_mute()
            button.style = discord.ButtonStyle.danger if is_muted else discord.ButtonStyle.primary
            await interaction.response.edit_message(view=self)

    @discord.ui.button(label="Meta Mode", style=discord.ButtonStyle.secondary, emoji="🔮", row=1)
    async def meta_btn(self, interaction: discord.Interaction, button: Button):
        vc = interaction.guild.voice_client
        if vc and vc.is_listening() and isinstance(vc.sink, ZeroLatencySink):
            vc.sink.toggle_meta()
            await interaction.response.send_message("🔮 Mode Toggled", delete_after=2)

    @discord.ui.button(label="Status", style=discord.ButtonStyle.secondary, emoji="📊", row=1)
    async def status_btn(self, interaction: discord.Interaction, button: Button):
        await status_check(interaction)

    @discord.ui.button(label="Leave", style=discord.ButtonStyle.danger, emoji="👋", row=1)
    async def leave_btn(self, interaction: discord.Interaction, button: Button):
        if interaction.guild.voice_client: await interaction.guild.voice_client.disconnect(force=True); await interaction.response.send_message("👋")

async def status_check(ctx):
    # Perform System Verification
    report = []
    
    # 1. API Link
    try:
        start = time.time()
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{API_URL}/") as r:
                lat = int((time.time() - start) * 1000)
                if r.status == 200: report.append(f"✅ **API Core:** Online ({lat}ms)")
                else: report.append(f"❌ **API Core:** Error {r.status}")
    except: report.append("❌ **API Core:** Unreachable")

    # 2. Scribe Link (Guardrails/Audio)
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{SCRIBE_URL}/") as r: # Scribe usually doesn't have root get, but connection test
                pass
        report.append(f"✅ **Scribe (Whisper):** Connected")
    except: report.append("⚠️ **Scribe:** Ping Failed (May behave normally)")

    # 3. ElevenLabs / Voices
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{API_URL}/system/audio/voices") as r:
                if r.status == 200: 
                    v = await r.json()
                    report.append(f"✅ **Voice Matrix:** {len(v)} IDs Loaded")
                else: report.append("⚠️ **Voice Matrix:** Sync Error")
    except: report.append("❌ **Voice Matrix:** Unreachable")

    # 4. Config / Guardrails
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{API_URL}/system/config") as r:
                if r.status == 200:
                    c = await r.json()
                    camp = c.get("active_campaign", "Unknown")
                    report.append(f"✅ **Campaign:** {camp} (Physics Active)")
    except: pass

    # Send
    embed = discord.Embed(title="🛡️ System Status Diagnostics", description="\n".join(report), color=0x3498db)
    if isinstance(ctx, discord.Interaction): await ctx.response.send_message(embed=embed)
    else: await ctx.send(embed=embed)

@bot.command(aliases=["help", "commands"])
async def menu(ctx):
    desc = "`!buttons` - Open Control Deck\n`!status` - Run System Diagnostics"
    await ctx.send(embed=discord.Embed(title="📜 RealmQuest Interface", description=desc, color=0x9b59b6))

@bot.command()
async def status(ctx): await status_check(ctx)

@bot.command(aliases=['join'])
async def buttons(ctx):
    if ctx.author.voice:
        vc = ctx.guild.voice_client
        if not vc: vc = await ctx.author.voice.channel.connect(cls=voice_recv.VoiceRecvClient, self_deaf=False)
        if not vc.is_listening():
            vc.listen(ZeroLatencySink(bot, source_channel=ctx.channel))
            # Persist active narration/text channel (no drift)
            global ACTIVE_TEXT_CHANNEL_ID
            ACTIVE_TEXT_CHANNEL_ID = ctx.channel.id
            try:
                if r_client: r_client.set('rq_text_channel_id', str(ctx.channel.id))
            except Exception:
                pass
    await ctx.send(embed=discord.Embed(title="🎛️ Control Deck", color=0x2ecc71), view=Dashboard())

@bot.command()
async def leave(ctx):
    if ctx.voice_client: await ctx.voice_client.disconnect(force=True)

@bot.event
async def on_ready():
    print(f"✅ SYSTEM: Bot Online ({bot.user})")
    for guild in bot.guilds:
        await sync_roster_to_redis(guild)

    # Start RollWatcher once the bot is ready (additive; no UI drift)
    if not hasattr(bot, '_roll_watcher_started'):
        try:
            watcher = RollWatcher(
                bot,
                API_URL,
                redis_client=r_client,
                poll_interval=float(os.getenv('ROLL_POLL_INTERVAL', '2.0')),
                limit=int(os.getenv('ROLL_FEED_LIMIT', '50')),
                channel_id_getter=lambda: ACTIVE_TEXT_CHANNEL_ID,
            )
            watcher.start()
            bot.roll_watcher = watcher
            bot._roll_watcher_started = True
        except Exception as e:
            logging.getLogger('rq.roll_watcher').error(f'RollWatcher failed to start: {e}')

if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
