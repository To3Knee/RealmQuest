# ===============================================================
# Script Name: sink.py
# Script Location: /opt/RealmQuest/bot/core/sink.py
# Date: 2026-01-27
# Version: 21.0.0 (Priority Hearing)
# ===============================================================

import asyncio
import discord
import logging
import time
import audioop
import aiohttp
import io
import wave
from collections import deque
from discord.ext import voice_recv
from core.config import RMS_THRESHOLD, SILENCE_TIMEOUT, MAX_RECORD_TIME, PRE_BUFFER_LEN, API_URL, SCRIBE_URL

logger = logging.getLogger("sink")

# PRIORITY LEXICON (Common D&D terms FIRST)
WHISPER_CONTEXT = (
    "Ale, Beer, Mead, Drink, Order, Quest Board, I would like, Tavern, Innkeeper, Barmaid, "
    "RealmQuest, Dungeon Master, Player Character, NPC, "
    "Dungeons and Dragons, 5e, Critical Hit, Initiative, Armor Class, Saving Throw, Ability Check, "
    "Advantage, Disadvantage, Proficiency, Inspiration, Spell Slot, Cantrip, Long Rest, Short Rest, "
    "Hit Points, Temporary HP, Death Save, Exhaustion, Condition, Blinded, Charmed, Deafened, "
    "Frightened, Grappled, Incapacitated, Invisible, Paralyzed, Petrified, Poisoned, Prone, "
    "Restrained, Stunned, Unconscious, Abjuration, Conjuration, Divination, Enchantment, Evocation, "
    "Illusion, Necromancy, Transmutation, Artificer, Barbarian, Bard, Cleric, Druid, Fighter, Monk, "
    "Paladin, Ranger, Rogue, Sorcerer, Warlock, Wizard, Aarakocra, Dragonborn, Dwarf, Elf, Gnome, "
    "Halfling, Human, Tiefling, Orc, Goblin, Kobold, Bugbear, Hobgoblin, Mind Flayer, Beholder, "
    "Lich, Vampire, Zombie, Skeleton, Dragon, Giant, Elemental, Fey, Fiend, Celestial, Construct, "
    "Aberration, Beast, Monstrosity, Ooze, Plant, Undead, Acid, Bludgeoning, Cold, Fire, Force, "
    "Lightning, Necrotic, Piercing, Poison, Psychic, Radiant, Slashing, Thunder, Magic Missile, "
    "Fireball, Cure Wounds, Healing Word, Shield, Mage Armor, Detect Magic, Identify, Counterspell, "
    "Dispel Magic, Haste, Slow, Fly, Invisibility, Polymorph, Banishment, Teleport, Wish, "
    "Bag of Holding, Potion of Healing, Scroll, Wand, Staff, Rod, Ring, Amulet, Cloak, Boots, "
    "Sword, Shield, Dagger, Bow, Crossbow, Axe, Hammer, Mace, Spear, Staff, D20, D12, D10, D8, D6, D4"
)

class ZeroLatencySink(voice_recv.AudioSink):
    def __init__(self, bot, source_channel=None):
        super().__init__()
        self.bot = bot
        self.source_channel = source_channel
        self.queue = asyncio.Queue()
        self.pre_buffer = deque(maxlen=PRE_BUFFER_LEN)
        self.buffer = bytearray()
        self.speaking = False
        self.last_speech = 0
        self.start_time = 0
        self.user = None
        self.muted = False 
        self.meta_mode = False 
        self.task = asyncio.create_task(self.worker())
        print(f"✅ EAR: Attached to {source_channel.name} | Sens: {RMS_THRESHOLD}", flush=True)

    def wants_opus(self): return False 
    
    def write(self, user, data):
        if self.muted: return
        if data.pcm: 
            self.queue.put_nowait((user, data.pcm))

    def cleanup(self): self.task.cancel()
    def toggle_mute(self): self.muted = not self.muted; return self.muted
    def toggle_meta(self): self.meta_mode = not self.meta_mode; return self.meta_mode

    async def worker(self):
        while True:
            try:
                try: 
                    user, pcm = await asyncio.wait_for(self.queue.get(), timeout=0.5)
                except asyncio.TimeoutError:
                    if self.speaking:
                        if not self.muted: await self.process_segment()
                        self.speaking = False
                        self.buffer = bytearray(); self.pre_buffer.clear()
                    continue
                
                if self.muted: continue 
                
                try: rms = audioop.rms(pcm, 2)
                except: rms = 0
                
                # Smart Interrupt: If bot talking, need LOUD voice (RMS 24+)
                is_bot_talking = False
                if self.bot.voice_clients and self.bot.voice_clients[0].is_playing():
                    is_bot_talking = True
                
                dynamic_threshold = (RMS_THRESHOLD * 2.5) if is_bot_talking else RMS_THRESHOLD
                is_loud = rms > dynamic_threshold
                
                if not self.speaking:
                    self.pre_buffer.append(pcm)
                    if is_loud:
                        self.speaking = True; self.user = user; self.start_time = time.time(); self.last_speech = time.time()
                        self.buffer = bytearray(); 
                        for chunk in self.pre_buffer: self.buffer.extend(chunk)
                        self.buffer.extend(pcm)
                        print(f"🎤 VOICE: {user.display_name} (RMS: {rms:.1f})", flush=True)
                        if is_bot_talking:
                            self.bot.voice_clients[0].stop()
                else:
                    self.buffer.extend(pcm); now = time.time()
                    if is_loud: self.last_speech = now
                    
                    if (now - self.last_speech > SILENCE_TIMEOUT):
                        print("⏳ SILENCE: Processing...", flush=True)
                        await self.process_segment()
                        self.speaking = False; self.buffer = bytearray(); self.pre_buffer.clear()
                    elif (now - self.start_time > MAX_RECORD_TIME):
                        await self.process_segment()
                        self.speaking = False; self.buffer = bytearray(); self.pre_buffer.clear()
            except asyncio.CancelledError: break
            except Exception: await asyncio.sleep(1)

    async def process_segment(self):
        if len(self.buffer) < 20000: return
        
        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, 'wb') as wav_file:
            wav_file.setnchannels(2); wav_file.setsampwidth(2); wav_file.setframerate(48000)
            wav_file.writeframes(self.buffer)
        wav_buffer.seek(0)

        text = ""
        try:
            async with aiohttp.ClientSession() as session:
                form = aiohttp.FormData()
                form.add_field('file', wav_buffer, filename='speech.wav')
                form.add_field('prompt', WHISPER_CONTEXT) 
                
                async with session.post(f"{SCRIBE_URL}/transcribe", data=form) as resp:
                    if resp.status == 200:
                        res = await resp.json()
                        text = res.get("text", "").strip()
                        print(f"📝 HEARD: '{text}'", flush=True)
        except Exception: return
        
        if not text or len(text) < 5: 
            print(f"⛔ IGNORED NOISE: '{text}'", flush=True)
            return
            
        uid = str(self.user.id) if self.user else "000000"
        uname = self.user.display_name if self.user else "Traveler"

        try:
            payload = {"message": text, "discord_id": uid, "player_name": uname, "is_meta": self.meta_mode}
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{API_URL}/game/chat/generate", json=payload) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        reply = data.get("response")
                        voice_id = data.get("voice_id")
                        campaign = data.get("active_campaign", "default")
                        
                        # SINGLE IMAGE LOGIC
                        image_type = data.get("image_type", "none")
                        pending_prompt = data.get("pending_image_prompt")
                        
                        if image_type != "none" and pending_prompt:
                             asyncio.create_task(self.trigger_and_post_image(pending_prompt, campaign))

                        if reply: 
                            asyncio.create_task(self.speak(reply, voice_id))
        except Exception as e: logger.error(f"Brain Error: {e}")

    async def trigger_and_post_image(self, prompt, campaign_name):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{API_URL}/game/imagine", json={"prompt": prompt}) as resp:
                    if resp.status == 200:
                        res = await resp.json()
                        if res.get("status") == "success":
                            # Wait for file to write to disk
                            await asyncio.sleep(2.0) 
                            await self.post_image({"filename": res.get("filename"), "prompt": prompt}, campaign_name)
        except Exception as e: logger.error(f"Auto-Art Fail: {e}")

    async def post_image(self, img_data, campaign_name):
        fname = img_data.get("filename")
        if not fname: return
        try:
            file_url = f"{API_URL}/campaigns/{campaign_name}/assets/images/{fname}"
            async with aiohttp.ClientSession() as session:
                async with session.get(file_url) as resp:
                    if resp.status == 200:
                        data = await resp.read()
                        f = discord.File(io.BytesIO(data), filename=fname)
                        embed = discord.Embed(title="🎨 Visuals", description=img_data.get("prompt", "")[:200], color=0x9b59b6)
                        embed.set_image(url=f"attachment://{fname}")
                        await self.source_channel.send(file=f, embed=embed)
                    else:
                        logger.error(f"Image 404: {file_url}")
        except Exception as e: logger.error(f"Image Post Fail: {e}")

    async def speak(self, text, voice_id=None):
        try:
            async with aiohttp.ClientSession() as session:
                payload = {"text": text.strip(), "voice_id": voice_id}
                async with session.post(f"{API_URL}/game/tts", json=payload) as resp:
                    if resp.status == 200:
                        data = await resp.read()
                        with open("reply.mp3", "wb") as f: f.write(data)
                        if self.bot.voice_clients:
                            vc = self.bot.voice_clients[0]
                            if vc.is_playing(): vc.stop()
                            vc.play(discord.FFmpegPCMAudio("reply.mp3"))
        except Exception: pass