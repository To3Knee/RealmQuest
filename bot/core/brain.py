# ===============================================================
# Script Name: brain.py
# Script Location: /opt/RealmQuest/bot/core/brain.py
# Date: 2026-01-26
# Version: 18.36.0 (Debug Logging)
# ===============================================================

import aiohttp
import logging
from core.config import API_URL, SCRIBE_URL

logger = logging.getLogger("brain")

async def transcribe_audio(wav_buffer):
    try:
        async with aiohttp.ClientSession() as session:
            data = aiohttp.FormData()
            data.add_field('file', wav_buffer, filename='voice.wav')
            async with session.post(f"{SCRIBE_URL}/transcribe", data=data) as resp:
                if resp.status == 200:
                    js = await resp.json()
                    return js.get("text", "").strip()
                else:
                    logger.error(f"Scribe Error: {resp.status}")
    except Exception as e: logger.error(f"Transcribe Exception: {e}")
    return ""

async def generate_response(text, user_id, user_name, is_meta=False):
    payload = {"message": text, "discord_id": str(user_id), "player_name": user_name, "is_meta": is_meta}
    try:
        async with aiohttp.ClientSession() as session:
            url = f"{API_URL}/game/chat/generate"
            async with session.post(url, json=payload) as resp:
                if resp.status == 200:
                    js = await resp.json()
                    return js.get("response", ""), js.get("voice_id"), js.get("image")
                else:
                    logger.error(f"API Brain Error: {resp.status}")
    except Exception as e: logger.error(f"Brain Exception: {e}")
    return "", None, None