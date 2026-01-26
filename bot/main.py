import discord
import logging
import os
import asyncio
import redis
import json
from discord.ext import commands, voice_recv
from discord.ui import Button, View
from core.config import DISCORD_TOKEN
from core.sink import ZeroLatencySink

# --- TITANIUM SHIELD (Opus Fix) ---
from discord import opus
_orig = opus.Decoder.decode
def _safe(self, *args, **kwargs):
    try: return _orig(self, *args, **kwargs)
    except: return b'\x00' * 3840
opus.Decoder.decode = _safe

# --- LOGGING ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-8s %(name)s %(message)s")
logging.getLogger("discord").setLevel(logging.WARNING)
logging.getLogger("discord.ext.voice_recv").setLevel(logging.WARNING)

# --- REDIS CONNECTION (ROSTER SYNC) ---
REDIS_URL = os.getenv("REDIS_URL", "redis://realmquest-redis:6379/0")
try:
    r_client = redis.from_url(REDIS_URL, decode_responses=True)
    print("✅ REDIS: Connected for Roster Sync")
except Exception as e:
    r_client = None
    print(f"⚠️ REDIS FAILURE: {e}")

# --- BOT SETUP ---
intents = discord.Intents.default()
intents.message_content = True
intents.members = True   # REQUIRED for Roster
intents.presences = True # REQUIRED for Status (Online/Idle)

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# ==============================================================================
# 1. ROSTER SYNCHRONIZATION (THE "WHO IS HERE" LOGIC)
# ==============================================================================
async def sync_roster_to_redis(guild):
    """Scrapes active members and pushes to Redis for the Portal"""
    if not r_client: return

    members = []
    # Scan all members in the server
    for member in guild.members:
        # Filter: Skip Offline users (Optional - comment out if you want everyone)
        if member.status == discord.Status.offline:
            continue
        
        # Determine Role
        role = "Player"
        if member.bot: role = "System"
        # Check for specific "DM" or "Dungeon Master" roles
        if any(r.name.lower() in ["dm", "dungeon master", "gm"] for r in member.roles):
            role = "Dungeon Master"

        # Avatar Logic
        avatar_url = str(member.avatar.url) if member.avatar else "https://cdn.discordapp.com/embed/avatars/0.png"

        members.append({
            "id": str(member.id),
            "name": member.display_name,
            "status": str(member.status), # online, idle, dnd
            "role": role,
            "avatar": avatar_url
        })
    
    # Save to Redis (Key: 'discord_roster')
    # Set expiry to 1 hour so it doesn't rot if bot dies
    try:
        r_client.set("discord_roster", json.dumps(members), ex=3600)
        logging.info(f"📡 ROSTER SYNC: {len(members)} active users pushed to Portal.")
    except Exception as e:
        logging.error(f"❌ Redis Write Error: {e}")

# ==============================================================================
# 2. DASHBOARD UI
# ==============================================================================
class Dashboard(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Roll Call", style=discord.ButtonStyle.secondary, emoji="📜", row=0)
    async def roll_call_btn(self, interaction: discord.Interaction, button: Button):
        if not interaction.guild.voice_client:
             return await interaction.response.send_message("❌ Bot must be connected first.", delete_after=3)
        
        members = interaction.guild.voice_client.channel.members
        names = [f"• {m.display_name}" for m in members if not m.bot]
        
        embed = discord.Embed(title=f"📜 Roll Call ({len(names)})", description="\n".join(names) or "No players.", color=0x95a5a6)
        await interaction.response.send_message(embed=embed)

    @discord.ui.button(label="Listen", style=discord.ButtonStyle.success, emoji="🟢", row=0)
    async def listen_btn(self, interaction: discord.Interaction, button: Button):
        if not interaction.user.voice:
            return await interaction.response.send_message("❌ You must be in a voice channel first!")
        
        vc = interaction.guild.voice_client
        if not vc:
            vc = await interaction.user.voice.channel.connect(cls=voice_recv.VoiceRecvClient, self_deaf=False)
        elif vc.channel != interaction.user.voice.channel:
            await vc.move_to(interaction.user.voice.channel)

        if not vc.is_listening():
            vc.listen(ZeroLatencySink(bot))
            await interaction.response.send_message("🎧 **Ears Open.** I am listening...", delete_after=5)
        else:
            await interaction.response.send_message("⚠️ Already listening.", delete_after=3)

    @discord.ui.button(label="Stop", style=discord.ButtonStyle.danger, emoji="🛑", row=0)
    async def stop_btn(self, interaction: discord.Interaction, button: Button):
        vc = interaction.guild.voice_client
        if vc and vc.is_playing():
            vc.stop()
            await interaction.response.send_message("🛑 **Audio Cut.**", delete_after=3)
        else:
            await interaction.response.send_message("⚠️ Nothing playing.", delete_after=3)

    @discord.ui.button(label="Mute", style=discord.ButtonStyle.primary, emoji="🔇", row=0)
    async def mute_btn(self, interaction: discord.Interaction, button: Button):
        vc = interaction.guild.voice_client
        if vc and vc.is_listening() and isinstance(vc.sink, ZeroLatencySink):
            is_muted = vc.sink.toggle_mute()
            button.label = "Unmute" if is_muted else "Mute"
            button.style = discord.ButtonStyle.danger if is_muted else discord.ButtonStyle.primary
            button.emoji = "😶" if is_muted else "🔇"
            status = "🔴 **MUTED** (I cannot hear you)." if is_muted else "🟢 **UNMUTED** (I am listening)."
            await interaction.response.edit_message(view=self)
            await interaction.channel.send(status)
        else:
            await interaction.response.send_message("❌ Bot is not active.", delete_after=3)

    @discord.ui.button(label="Leave", style=discord.ButtonStyle.danger, emoji="👋", row=0)
    async def leave_btn(self, interaction: discord.Interaction, button: Button):
        if interaction.guild.voice_client:
            await interaction.guild.voice_client.disconnect(force=True)
            await interaction.response.send_message("👋 **Disconnected.**")
        else:
            await interaction.response.send_message("❌ Not connected.", delete_after=3)

# ==============================================================================
# 3. EVENTS
# ==============================================================================
@bot.event
async def on_ready():
    print(f"✅ SYSTEM: Bot Online ({bot.user})")
    # Sync Roster immediately on startup
    for guild in bot.guilds:
        await sync_roster_to_redis(guild)

@bot.event
async def on_member_join(member):
    await sync_roster_to_redis(member.guild)

@bot.event
async def on_member_remove(member):
    await sync_roster_to_redis(member.guild)

@bot.event
async def on_presence_update(before, after):
    # Triggers when someone goes offline/online
    if before.status != after.status:
        await sync_roster_to_redis(after.guild)

# --- TEXT COMMANDS ---
@bot.command()
async def menu(ctx):
    """Shows the list of commands"""
    desc = """
    **UI & Connection**
    `!buttons` - Summon the Dashboard Buttons
    `!join`    - Connect & Summon Dashboard
    `!leave`   - Disconnect the bot
    
    **Audio Controls**
    `!listen`  - Start Listening
    `!stop`    - Cut off current speech
    `!mute`    - Privacy Mode
    `!unmute`  - Resume listening
    """
    embed = discord.Embed(title="📜 Command Menu", description=desc, color=0x9b59b6)
    await ctx.send(embed=embed)

@bot.command(aliases=['join'])
async def buttons(ctx):
    """Summons the Dashboard AND connects"""
    if ctx.author.voice:
        vc = ctx.guild.voice_client
        if not vc:
            vc = await ctx.author.voice.channel.connect(cls=voice_recv.VoiceRecvClient, self_deaf=False)
        elif vc.channel != ctx.author.voice.channel:
            await vc.move_to(ctx.author.voice.channel)
        
        if not vc.is_listening():
            vc.listen(ZeroLatencySink(bot))
            await ctx.send("🎧 **Connected & Listening.**")

    embed = discord.Embed(
        title="🎛️ RealmQuest Audio Interface", 
        description="Control the AI Game Master below.", 
        color=0x2ecc71
    )
    await ctx.send(embed=embed, view=Dashboard())

@bot.command()
async def listen(ctx):
    if not ctx.author.voice: return await ctx.send("❌ Join a voice channel first!")
    vc = ctx.guild.voice_client
    if not vc: vc = await ctx.author.voice.channel.connect(cls=voice_recv.VoiceRecvClient, self_deaf=False)
    if not vc.is_listening():
        vc.listen(ZeroLatencySink(bot))
        await ctx.send("🎧 **Connected & Listening.**")
    else:
        await ctx.send("⚠️ Already listening.")

@bot.command()
async def stop(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.message.add_reaction("🛑")
    else:
        await ctx.send("⚠️ Nothing playing.")

@bot.command()
async def mute(ctx):
    vc = ctx.guild.voice_client
    if vc and vc.is_listening() and isinstance(vc.sink, ZeroLatencySink):
        if not vc.sink.muted:
            vc.sink.toggle_mute()
            await ctx.send("🔴 **MUTED** (Privacy Mode On)")
        else:
            await ctx.send("⚠️ Already muted.")
    else:
        await ctx.send("❌ Bot is not listening.")

@bot.command()
async def unmute(ctx):
    vc = ctx.guild.voice_client
    if vc and vc.is_listening() and isinstance(vc.sink, ZeroLatencySink):
        if vc.sink.muted:
            vc.sink.toggle_mute()
            await ctx.send("🟢 **UNMUTED** (Listening Resumed)")
        else:
            await ctx.send("⚠️ Already unmuted.")
    else:
        await ctx.send("❌ Bot is not listening.")

@bot.command()
async def leave(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect(force=True)
        await ctx.message.add_reaction("👋")
    else:
        await ctx.send("❌ Not connected.")

if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)