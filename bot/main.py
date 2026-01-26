# ===============================================================
# Script Name: main.py
# Script Location: /opt/RealmQuest/bot/main.py
# Date: 2026-01-26
# Version: 18.6.0
# About: Bot Entrypoint (Passes Context to Sink)
# ===============================================================

import discord
import logging
import os
import asyncio
import redis
import json
import aiohttp
from discord.ext import commands, voice_recv
from discord.ui import Button, View
from core.config import DISCORD_TOKEN, API_URL
from core.sink import ZeroLatencySink

from discord import opus
_orig = opus.Decoder.decode
def _safe(self, *args, **kwargs):
    try: return _orig(self, *args, **kwargs)
    except: return b'\x00' * 3840
opus.Decoder.decode = _safe

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-8s %(name)s %(message)s")
logging.getLogger("discord").setLevel(logging.WARNING)
logging.getLogger("discord.ext.voice_recv").setLevel(logging.WARNING)

REDIS_URL = os.getenv("REDIS_URL", "redis://realmquest-redis:6379/0")
try: r_client = redis.from_url(REDIS_URL, decode_responses=True)
except: r_client = None

intents = discord.Intents.default()
intents.message_content = True
intents.members = True   
intents.presences = True 
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

async def sync_roster_to_redis(guild):
    if not r_client: return
    members = []
    for member in guild.members:
        if member.status == discord.Status.offline: continue
        role = "Player"
        if member.bot:
            if "RQFM" in member.display_name or "Kenku" in member.display_name: role = "KENKU [AUDIO]"
            elif "RealmQuest" in member.display_name: role = "DUNGEON MASTER [AI]"
            else: role = "System"
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
            # PASSING CHANNEL CONTEXT HERE
            vc.listen(ZeroLatencySink(bot, source_channel=interaction.channel))
            await interaction.response.send_message("🎧 **Listening.**", delete_after=3)
        else: await interaction.response.send_message("⚠️ Already active.", delete_after=3)

    @discord.ui.button(label="Stop", style=discord.ButtonStyle.danger, emoji="🛑", row=0)
    async def stop_btn(self, interaction: discord.Interaction, button: Button):
        vc = interaction.guild.voice_client
        if vc and vc.is_playing(): vc.stop(); await interaction.response.send_message("🛑 **Stopped.**", delete_after=3)

    @discord.ui.button(label="Mute", style=discord.ButtonStyle.primary, emoji="🔇", row=1)
    async def mute_btn(self, interaction: discord.Interaction, button: Button):
        vc = interaction.guild.voice_client
        if vc and vc.is_listening() and isinstance(vc.sink, ZeroLatencySink):
            is_muted = vc.sink.toggle_mute()
            button.label = "Unmute" if is_muted else "Mute"
            button.style = discord.ButtonStyle.danger if is_muted else discord.ButtonStyle.primary
            button.emoji = "😶" if is_muted else "🔇"
            await interaction.response.edit_message(view=self)
            await interaction.channel.send("🔴 **MUTED**" if is_muted else "🟢 **UNMUTED**")

    @discord.ui.button(label="Meta Mode", style=discord.ButtonStyle.secondary, emoji="🔮", row=1)
    async def meta_btn(self, interaction: discord.Interaction, button: Button):
        vc = interaction.guild.voice_client
        if vc and vc.is_listening() and isinstance(vc.sink, ZeroLatencySink):
            is_meta = vc.sink.toggle_meta()
            button.style = discord.ButtonStyle.blurple if is_meta else discord.ButtonStyle.secondary
            button.label = "Meta Active" if is_meta else "Meta Mode"
            await interaction.response.edit_message(view=self)
            await interaction.channel.send("🔮 **ORACLE MODE** (OOC)" if is_meta else "🎭 **DM MODE** (RP)")

    @discord.ui.button(label="Leave", style=discord.ButtonStyle.danger, emoji="👋", row=1)
    async def leave_btn(self, interaction: discord.Interaction, button: Button):
        if interaction.guild.voice_client: await interaction.guild.voice_client.disconnect(force=True); await interaction.response.send_message("👋")

@bot.command(aliases=["help", "commands"])
async def menu(ctx):
    desc = "**Dashboard**\n`!buttons` - UI\n\n**Voice**\n`!listen` / `!stop`\n`!mute` / `!unmute`\n`!meta` - Toggle Rules Mode\n\n**Vision**\n`!paint <prompt>`"
    await ctx.send(embed=discord.Embed(title="📜 RealmQuest Interface", description=desc, color=0x9b59b6))

@bot.command()
async def meta(ctx):
    vc = ctx.guild.voice_client
    if vc and vc.is_listening() and isinstance(vc.sink, ZeroLatencySink):
        state = vc.sink.toggle_meta()
        await ctx.send(f"🔮 Meta Mode: **{'ON' if state else 'OFF'}**")

@bot.command(aliases=["vision", "art", "draw"])
async def paint(ctx, *, prompt):
    msg = await ctx.send(f"🎨 **Visualizing:** *{prompt}* ...")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{API_URL}/game/imagine", json={"prompt": prompt}) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    await msg.delete(); await ctx.send(embed=discord.Embed(title="🎨 Canvas Complete", description=f"**Prompt:** {prompt}\n**File:** `{data.get('filename')}`", color=0xf1c40f))
                else: await msg.edit(content=f"❌ Error: {await resp.text()}")
    except Exception as e: await msg.edit(content=f"❌ Error: {e}")

@bot.command(aliases=['join'])
async def buttons(ctx):
    if ctx.author.voice:
        vc = ctx.guild.voice_client
        if not vc: vc = await ctx.author.voice.channel.connect(cls=voice_recv.VoiceRecvClient, self_deaf=False)
        if not vc.is_listening(): vc.listen(ZeroLatencySink(bot, source_channel=ctx.channel)); await ctx.send("🎧 **Connected.**")
    await ctx.send(embed=discord.Embed(title="🎛️ Control Deck", color=0x2ecc71), view=Dashboard())

@bot.command()
async def mute(ctx):
    vc = ctx.guild.voice_client
    if vc and vc.is_listening(): vc.sink.toggle_mute(); await ctx.send("🔴 **MUTED**")
@bot.command()
async def unmute(ctx):
    vc = ctx.guild.voice_client
    if vc and vc.is_listening(): vc.sink.toggle_mute(); await ctx.send("🟢 **UNMUTED**")
@bot.command()
async def leave(ctx):
    if ctx.voice_client: await ctx.voice_client.disconnect(force=True)
@bot.command()
async def listen(ctx):
    if ctx.author.voice:
        vc = ctx.guild.voice_client
        if not vc: vc = await ctx.author.voice.channel.connect(cls=voice_recv.VoiceRecvClient, self_deaf=False)
        if not vc.is_listening(): vc.listen(ZeroLatencySink(bot, source_channel=ctx.channel)); await ctx.send("🎧 **Listening.**")
@bot.command()
async def stop(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing(): ctx.voice_client.stop()

@bot.event
async def on_ready():
    print(f"✅ SYSTEM: Bot Online ({bot.user})")
    for guild in bot.guilds: await sync_roster_to_redis(guild)
@bot.event
async def on_member_join(m): await sync_roster_to_redis(m.guild)
@bot.event
async def on_member_remove(m): await sync_roster_to_redis(m.guild)
@bot.event
async def on_presence_update(b, a):
    if b.status != a.status: await sync_roster_to_redis(a.guild)

if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)