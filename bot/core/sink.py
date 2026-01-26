# ===============================================================
# Script Name: sink.py
# Script Location: /opt/RealmQuest/bot/core/sink.py
# Date: 2026-01-26
# Version: 18.9.0
# About: Sink with Markdown Stripper & Native Upload
# ===============================================================

import asyncio
import discord
import logging
import time
import audioop
import aiohttp
import re
import os
from collections import deque
from discord.ext import voice_recv
from core.audio import convert_pcm_to_wav
from core import brain
from core.config import RMS_THRESHOLD, SILENCE_TIMEOUT, MAX_RECORD_TIME, PRE_BUFFER_LEN, API_URL

logger = logging.getLogger("sink")
CAMPAIGN_ROOT = "/campaigns" 

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
        self.wake_word = "DM"
        self.last_sync = 0
        self.task = bot.loop.create_task(self.worker())
        logger.info(f">>> 🔌 SINK STARTED [Target: {source_channel.name if source_channel else 'None'}]")

    def wants_opus(self): return False 
    def write(self, user, data):
        if data.pcm: self.queue.put_nowait((user, data.pcm))
    def cleanup(self): self.task.cancel()
    def toggle_mute(self): self.muted = not self.muted; return self.muted
    def toggle_meta(self): self.meta_mode = not self.meta_mode; return self.meta_mode

    async def sync_wake_word(self):
        if time.time() - self.last_sync > 30:
            new_name = await brain.fetch_wake_word()
            if new_name != self.wake_word: self.wake_word = new_name
            self.last_sync = time.time()

    async def worker(self):
        while True:
            try:
                await self.sync_wake_word()
                try: user, pcm = await asyncio.wait_for(self.queue.get(), timeout=0.5)
                except asyncio.TimeoutError:
                    if self.speaking:
                        if not self.muted: await self.process_segment()
                        self.speaking = False
                        self.buffer = bytearray(); self.pre_buffer.clear()
                    continue
                if self.muted: continue 
                if self.bot.voice_clients and self.bot.voice_clients[0].is_playing(): continue 
                try: rms = audioop.rms(pcm, 2)
                except: rms = 0
                is_loud = rms > RMS_THRESHOLD
                if not self.speaking:
                    self.pre_buffer.append(pcm)
                    if is_loud:
                        self.speaking = True; self.user = user; self.start_time = time.time(); self.last_speech = time.time()
                        self.buffer = bytearray(); 
                        for chunk in self.pre_buffer: self.buffer.extend(chunk)
                        self.buffer.extend(pcm)
                else:
                    self.buffer.extend(pcm); now = time.time()
                    if is_loud: self.last_speech = now
                    if (now - self.last_speech > SILENCE_TIMEOUT) or (now - self.start_time > MAX_RECORD_TIME):
                        await self.process_segment(); self.speaking = False; self.buffer = bytearray(); self.pre_buffer.clear()
            except asyncio.CancelledError: break
            except Exception as e: logger.error(f"Worker Error: {e}")

    async def process_segment(self):
        if self.muted: return
        if len(self.buffer) / 192000.0 < 0.5: return
        wav_data = await convert_pcm_to_wav(self.buffer)
        if not wav_data: return
        text = await brain.transcribe_audio(wav_data)
        
        if text:
            text_lower = text.lower()
            
            # VOICE PAINT
            vision_match = re.match(r"^(vision|paint|draw)\s+(.*)", text_lower)
            if vision_match:
                prompt = vision_match.group(2).strip()
                logger.info(f"🎨 MANUAL PAINT: {prompt}")
                if prompt:
                    filename, err = await brain.generate_image(prompt)
                    if filename:
                        await self.upload_image(filename, prompt, "Manual Request")
                        await self.speak(f"Visualizing {prompt}")
                    else: await self.speak("I could not generate that image.")
                return

            # CHAT
            curr = self.wake_word.lower()
            aliases = [curr, "oracle"]
            if curr == "dm": aliases.extend(["dan", "them", "damn", "dean", "the m", "d m"])

            matched = None
            for alias in aliases:
                if re.match(rf"^{re.escape(alias)}\b", text_lower): matched = alias; break
            
            if not matched: return
            clean = re.sub(rf"^{re.escape(matched)}\W*", '', text_lower).strip()
            if not clean: return
            
            logger.info(f"🗣️ USER: {clean}")
            
            reply, voice_id, image_data = await brain.generate_response(clean, self.user.id, self.user.display_name, is_meta=self.meta_mode)
            
            # DIRECTOR UPLOAD
            if image_data and self.source_channel:
                await self.upload_image(image_data['filename'], image_data['prompt'], "Director Mode")
            
            if reply: await self.speak(reply, voice_id)

    async def upload_image(self, filename, prompt, footer):
        if not self.source_channel: return
        filepath = None
        for root, dirs, files in os.walk(CAMPAIGN_ROOT):
            if filename in files:
                filepath = os.path.join(root, filename)
                break
        
        if filepath and os.path.exists(filepath):
            try:
                file = discord.File(filepath, filename=filename)
                embed = discord.Embed(title="🎨 Scene Visualization", description=f"*{prompt}*", color=0xf1c40f)
                embed.set_image(url=f"attachment://{filename}")
                embed.set_footer(text=f"RealmQuest Vision Engine // {footer}")
                await self.source_channel.send(file=file, embed=embed)
                logger.info(f"✅ UPLOADED: {filename}")
            except Exception as e: logger.error(f"Upload Failed: {e}")
        else: logger.error(f"❌ FILE NOT FOUND: {filename}")

    async def speak(self, text, voice_id=None):
        # CLEAN FOR TTS: Remove Markdown Tables, Headers, Bold/Italic
        clean_text = text
        # Remove Tables (Lines starting with |)
        clean_text = re.sub(r'^\s*\|.*\|.*$', '', clean_text, flags=re.MULTILINE)
        # Remove Table Dividers (|---|)
        clean_text = re.sub(r'^\s*\|[-:]+\|.*$', '', clean_text, flags=re.MULTILINE)
        # Remove Headers (###)
        clean_text = re.sub(r'#+\s', '', clean_text)
        # Remove Bold/Italic (** or *)
        clean_text = re.sub(r'\*\*|__|\*', '', clean_text)
        # Remove Links
        clean_text = re.sub(r'\[.*?\]\(.*?\)', '', clean_text)
        
        clean_text = clean_text.strip()
        if not clean_text: return # Nothing left to say

        logger.info(f"🔊 SPEAKING ({len(clean_text)} chars): {clean_text[:50]}...")
        
        payload = {"text": clean_text}
        if voice_id: payload["voice_id"] = voice_id
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{API_URL}/game/tts", json=payload) as resp:
                    if resp.status == 200:
                        data = await resp.read()
                        with open("reply.mp3", "wb") as f: f.write(data)
                        if self.bot.voice_clients:
                            vc = self.bot.voice_clients[0]
                            if vc.is_playing(): vc.stop()
                            vc.play(discord.FFmpegPCMAudio("reply.mp3"))
        except: pass