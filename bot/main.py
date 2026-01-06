import os
import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# Define the bot with necessary intents
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f'✅ RealmQuest Bot is online as {bot.user}')

@bot.command()
async def join(ctx):
    """Command to make the bot join your current voice channel."""
    if ctx.author.voice:
        channel = ctx.author.voice.channel
        await channel.connect()
        await ctx.send(f"🎙️ RealmQuest connected to {channel}. I'm listening...")
    else:
        await ctx.send("⚠️ You need to be in a voice channel first!")

@bot.command()
async def leave(ctx):
    """Command to make the bot leave voice."""
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("👋 Leaving the channel. Journey safe.")

if __name__ == "__main__":
    bot.run(TOKEN)