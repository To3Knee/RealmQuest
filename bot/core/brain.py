# ===============================================================
# Script Name: brain.py
# Script Location: /opt/RealmQuest/bot/core/brain.py
# Date: 2026-01-26
# Version: 18.6.0
# About: API Client handling Composite Payloads (Text + Image)
# ===============================================================

import aiohttp
import logging
import json
from core.config import API_URL, SCRIBE_URL

logger = logging.getLogger("brain")
DEFAULT_WAKE_WORD = "DM"

async def fetch_wake_word():
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{API_URL}/system/config") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    registry = data.get("audio_registry", {})
                    name = registry.get("dmName", DEFAULT_WAKE_WORD)
                    return name if name and name.strip() else DEFAULT_WAKE_WORD
    except: pass
    return DEFAULT_WAKE_WORD

async def transcribe_audio(wav_data):
    try:
        async with aiohttp.ClientSession() as session:
            data = aiohttp.FormData()
            data.add_field('file', wav_data, filename='voice.wav')
            async with session.post(f"{SCRIBE_URL}/transcribe", data=data) as resp:
                if resp.status == 200:
                    js = await resp.json()
                    return js.get("text", "").strip()
    except Exception as e: logger.error(f"Transcribe Error: {e}")
    return ""

async def generate_response(text, user_id, user_name, is_meta=False):
    payload = {"message": text, "discord_id": str(user_id), "player_name": user_name, "is_meta": is_meta}
    try:
        async with aiohttp.ClientSession() as session:
            url = f"{API_URL}/game/chat/generate"
            logger.info(f"🚀 POSTING TO: {url} [Meta: {is_meta}]")
            async with session.post(url, json=payload) as resp:
                if resp.status == 200:
                    js = await resp.json()
                    logger.info(f"🧠 RESPONSE: Text Len={len(js.get('response', ''))} | Image={js.get('image') is not None}")
                    # Return tuple: (Text, VoiceID, ImageData)
                    return js.get("response", ""), js.get("voice_id"), js.get("image")
                else:
                    logger.error(f"API Error: {resp.status}")
    except Exception as e: logger.error(f"Chat Error: {e}")
    return "", None, None

async def generate_image(prompt):
    payload = {"prompt": prompt}
    try:
        async with aiohttp.ClientSession() as session:
            url = f"{API_URL}/game/imagine"
            async with session.post(url, json=payload) as resp:
                if resp.status == 200:
                    js = await resp.json()
                    return js.get("filename"), None
                else: return None, await resp.text()
    except Exception as e: return None, str(e)