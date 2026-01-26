import aiohttp
import logging
import json
from core.config import API_URL, SCRIBE_URL

logger = logging.getLogger("brain")

# Default if API fails
DEFAULT_WAKE_WORD = "DM"

async def fetch_wake_word():
    """Fetches the custom Name/Wake Word from the Portal Config"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{API_URL}/system/config") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    registry = data.get("audio_registry", {})
                    name = registry.get("dmName", DEFAULT_WAKE_WORD)
                    return name if name and name.strip() else DEFAULT_WAKE_WORD
    except Exception as e:
        # logger.error(f"Failed to fetch wake word: {e}")
        pass
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
    except Exception as e:
        logger.error(f"Brain Transcribe Error: {e}")
    return ""

async def generate_response(text, user_id, user_name):
    payload = {"message": text, "discord_id": str(user_id), "player_name": user_name}
    try:
        async with aiohttp.ClientSession() as session:
            url = f"{API_URL}/game/chat/generate"
            logger.info(f"🚀 POSTING TO: {url}")
            async with session.post(url, json=payload) as resp:
                if resp.status == 200:
                    js = await resp.json()
                    logger.info(f"🧠 API RESPONSE: {json.dumps(js)}")
                    return js.get("response", ""), js.get("voice_id")
                else:
                    logger.error(f"API Error: {resp.status} - {await resp.text()}")
    except Exception as e:
        logger.error(f"Brain Chat Error: {e}")
    return "", None
