import asyncio
import discord
import logging
import time
import audioop
import aiohttp
import re
from collections import deque
from discord.ext import voice_recv
from core.audio import convert_pcm_to_wav
from core import brain
from core.config import RMS_THRESHOLD, SILENCE_TIMEOUT, MAX_RECORD_TIME, PRE_BUFFER_LEN, API_URL

logger = logging.getLogger("sink")

class ZeroLatencySink(voice_recv.AudioSink):
    def __init__(self, bot):
        super().__init__()
        self.bot = bot
        self.queue = asyncio.Queue()
        self.pre_buffer = deque(maxlen=PRE_BUFFER_LEN)
        self.buffer = bytearray()
        self.speaking = False
        self.last_speech = 0
        self.start_time = 0
        self.user = None
        self.muted = False 
        self.wake_word = "DM"
        self.last_sync = 0
        self.task = bot.loop.create_task(self.worker())
        logger.info(">>> 🔌 SINK STARTED (v27.0: Phonetic Master)")

    def wants_opus(self): return False 
    def write(self, user, data):
        if data.pcm: self.queue.put_nowait((user, data.pcm))
    def cleanup(self): self.task.cancel()
    def toggle_mute(self): self.muted = not self.muted; return self.muted

    async def sync_wake_word(self):
        if time.time() - self.last_sync > 30:
            new_name = await brain.fetch_wake_word()
            if new_name != self.wake_word:
                logger.info(f"🔄 NAME UPDATE: '{self.wake_word}' -> '{new_name}'")
                self.wake_word = new_name
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
            curr = self.wake_word.lower()
            text_lower = text.lower()
            aliases = [curr]
            if curr == "dm": aliases.extend(["dan", "them", "damn", "dean", "the m", "d m"])
            
            matched = None
            for alias in aliases:
                if re.match(rf"^{re.escape(alias)}\b", text_lower): matched = alias; break
            
            if not matched: 
                logger.info(f"🔇 IGNORED: '{text}' (Waiting for '{curr}')")
                return

            clean = re.sub(rf"^{re.escape(matched)}\W*", '', text_lower).strip()
            if not clean: return
            logger.info(f"🗣️ USER: {clean} (Heard: {matched})")
            reply, voice_id = await brain.generate_response(clean, self.user.id, self.user.display_name)
            if reply: await self.speak(reply, voice_id)

    async def speak(self, text, voice_id=None):
        payload = {"text": re.sub(r'\[.*?\]|\*.*?\*', '', text).strip()}
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
