import os
import json
import redis
import requests
from fastapi import APIRouter, Response
from pydantic import BaseModel
from pymongo import MongoClient

router = APIRouter()
try:
    mongo = MongoClient(os.getenv("MONGO_URL", "mongodb://realmquest-mongo:27017/"), serverSelectionTimeoutMS=2000)
    db = mongo["realmquest"]
except: db = None

try:
    from ai_engine import AIEngine
    ai = AIEngine()
    ai_available = True
except: ai = None; ai_available = False

try: r_client = redis.from_url(os.getenv("REDIS_URL", "redis://realmquest-redis:6379/0"), decode_responses=True)
except: r_client = None

class ChatRequest(BaseModel):
    message: str
    discord_id: str
    player_name: str

class TTSRequest(BaseModel):
    text: str
    voice_id: str

@router.post("/chat/generate")
async def generate_response(payload: ChatRequest):
    if not ai_available: return {"response": "Brain Offline.", "voice_id": "default"}
    
    active_voice_id = "default"
    dm_name = "DM"
    if db is not None:
        audio_conf = db["system_config"].find_one({"config_id": "audio_registry"})
        if audio_conf:
            dm_name = audio_conf.get("dmName", "DM")
            active_voice_id = audio_conf.get("dmVoice", {}).get("id", "default") if isinstance(audio_conf.get("dmVoice"), dict) else audio_conf.get("dmVoice", "default")

    # FORCEFUL SYSTEM PROMPT
    system_prompt = (
        f"You are {dm_name}, a Dungeon Master. "
        "Do NOT answer with single words. "
        "Describe the scene, the outcome of actions, or ask follow-up questions. "
        "Be atmospheric but keep it under 3-4 sentences."
    )
    
    return {"response": ai.generate_story(system_prompt, payload.message), "voice_id": active_voice_id}

@router.post("/tts")
async def text_to_speech(payload: TTSRequest):
    key = os.getenv("ELEVENLABS_API_KEY")
    if not key or payload.voice_id in ["default", "onyx"]: return Response(content=b"", status_code=500)
    try:
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{payload.voice_id}?optimize_streaming_latency=3"
        r = requests.post(url, json={"text": payload.text, "model_id": "eleven_monolingual_v1"}, headers={"xi-api-key": key, "Content-Type": "application/json"}, timeout=10)
        if r.status_code == 200: return Response(content=r.content, media_type="audio/mpeg")
    except: pass
    return Response(content=b"", status_code=500)

@router.get("/discord/members")
def get_discord_members():
    if r_client:
        try: return json.loads(r_client.get("discord_roster"))
        except: pass
    return [{"id": "bot", "name": "RealmQuest Bot", "status": "online", "role": "System"}]
@router.get("/roster")
def get_roster(): return []
