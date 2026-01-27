# ===============================================================
# Script Name: chat_engine.py
# Script Location: /opt/RealmQuest/api/chat_engine.py
# Date: 2026-01-27
# Version: 21.0.0 (Performance & Realism)
# ===============================================================

import os
import json
import redis
import re
import requests
import time
from fastapi import APIRouter, Response, BackgroundTasks, HTTPException
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

# --- CONFIG ---
KENKU_URL = os.getenv("KENKU_URL", "http://realmquest-kenku:3333").rstrip("/")
FALLBACK_VOICE_ID = "onwK4e9ZLuTAKqWW03F9" # Daniel

# --- RUNTIME MEMORY ---
VOICE_DB = {}      
ARCHETYPE_DB = {}  
DM_VOICE_ID = ""
LAST_DB_SYNC = 0

class ChatRequest(BaseModel):
    message: str
    discord_id: str
    player_name: str
    is_meta: bool = False

class TTSRequest(BaseModel):
    text: str
    voice_id: str

class ImageRequest(BaseModel):
    prompt: str

class PromptUpdate(BaseModel):
    prompt: str

CHAT_HISTORY = [] 

# --- HELPERS ---

def get_active_campaign_name():
    if db is not None:
        try:
            conf = db["system_config"].find_one({"config_id": "audio_registry"})
            if conf and conf.get("active_campaign"):
                val = conf.get("active_campaign")
                if val and val.lower() != "default": return val
        except: pass
    return "the_collision_stone"

def get_campaign_paths():
    campaign_name = get_active_campaign_name()
    base = f"/campaigns/{campaign_name}"
    return {
        "name": campaign_name,
        "root": base,
        "images": os.path.join(base, "assets", "images"),
        "npcs": os.path.join(base, "codex", "npcs")
    }

def sync_voices_from_db():
    global VOICE_DB, ARCHETYPE_DB, DM_VOICE_ID, LAST_DB_SYNC
    if db is None: return
    if time.time() - LAST_DB_SYNC < 10: return

    try:
        config = db["system_config"].find_one({"config_id": "audio_registry"})
        if config:
            raw_voices = config.get("voices", [])
            for v in raw_voices:
                VOICE_DB[v["label"].lower()] = v["voice_id"]

            raw_archetypes = config.get("archetypes", [])
            for arc in raw_archetypes:
                role = arc.get("role", "").lower()
                target_label = arc.get("voice_label", "").lower()
                if target_label in VOICE_DB:
                    ARCHETYPE_DB[role] = VOICE_DB[target_label]
            
            if config.get("dmVoice"): DM_VOICE_ID = config.get("dmVoice")
        LAST_DB_SYNC = time.time()
    except Exception: pass

# Hardcoded Fallbacks
SAFE_ARCHETYPES = {
    "female": "EXAVITQu4vr4xnSDxMaL", 
    "male": "ErXwobaYiN019PkySvjV",   
    "monster": "CwhRBWXzGAHq8TQ4Fs17" 
}

def get_voice_for_role(actor_tag, audio_registry):
    tag = actor_tag.lower()
    
    if tag.strip() in ARCHETYPE_DB: return ARCHETYPE_DB[tag.strip()]
    for name, vid in VOICE_DB.items():
        if tag in name: return vid
    
    if any(x in tag for x in ["maid", "woman", "lady", "girl", "queen", "mother"]): return SAFE_ARCHETYPES["female"]
    if any(x in tag for x in ["man", "boy", "king", "prince", "lord", "sir", "bartender", "smith"]): return SAFE_ARCHETYPES["male"]
    if any(x in tag for x in ["guard", "soldier", "warrior", "captain", "thug"]): return SAFE_ARCHETYPES["male"]
    if any(x in tag for x in ["goblin", "orc", "monster", "beast", "dragon"]): return SAFE_ARCHETYPES["monster"]

    return DM_VOICE_ID or FALLBACK_VOICE_ID

def async_audio_manager(mapped_track_id):
    if not mapped_track_id or str(mapped_track_id).startswith("sys_"): return
    try:
        requests.put(f"{KENKU_URL}/v1/playlist/volume", json={"volume": 0.3}, timeout=0.5)
        requests.put(f"{KENKU_URL}/v1/playlist/play", json={"id": mapped_track_id}, timeout=0.5)
        requests.put(f"{KENKU_URL}/v1/soundboard/play", json={"id": mapped_track_id}, timeout=0.5)
    except: pass

@router.post("/chat/generate")
async def generate_response(payload: ChatRequest, background_tasks: BackgroundTasks):
    if not ai_available: return {"response": "Brain Offline.", "voice_id": "default"}
    sync_voices_from_db()

    audio_config = {"dmName": "DM", "dmVoice": DM_VOICE_ID, "soundscapes": []}
    if db is not None:
        try:
            acr = db["system_config"].find_one({"config_id": "audio_registry"})
            if acr: audio_config = acr
        except: pass

    available_sounds = [s.get("label") for s in audio_config.get("soundscapes", [])]
    dm_name = audio_config.get('dmName', 'DM')
    
    system_instruction = (
        f"You are {dm_name}, the Dungeon Master. I am the Player ({payload.player_name}).\n"
        "**ROLEPLAY ONLY.**\n"
        "1. **SEPARATION:** Pick ONE mode per turn:\n"
        "   - **NARRATOR:** Describe scene. No actors. Use DM Voice.\n"
        "   - **ACTOR:** `[ACTOR: Name, Role]` followed ONLY by dialogue.\n"
        f"2. **SOUNDS:** Use `[SOUND: Label]` ONLY if the location changes.\n"
        "3. **BREVITY:** Keep descriptions under 4 sentences."
    )
    
    CHAT_HISTORY.append({"role": "user", "content": payload.message})
    if len(CHAT_HISTORY) > 6: CHAT_HISTORY.pop(0)

    full_prompt = f"SYSTEM: {system_instruction}\n\n"
    for turn in CHAT_HISTORY:
        full_prompt += f"{turn['role'].upper()}: {turn['content']}\n"
    full_prompt += "ASSISTANT:"

    raw_response = ai.generate_story(system_instruction, full_prompt)
    raw_response = re.sub(r"\|\s*VOICE_ID:[^\]]+", "", raw_response)
    if payload.message[:10].lower() in raw_response.lower():
        raw_response = raw_response.replace(payload.message, "").strip()

    print(f"🧠 RAW: {raw_response}")
    CHAT_HISTORY.append({"role": "assistant", "content": raw_response})

    clean_text = raw_response
    active_voice_id = DM_VOICE_ID or FALLBACK_VOICE_ID
    
    # NEW LOGIC: SINGLE TRIGGER
    pending_prompt = None
    image_type = "none" # 'npc', 'scene', or 'none'
    
    # 1. Sound Logic
    match_sound = re.search(r"\[SOUND:\s*(.*?)\]", clean_text, re.IGNORECASE)
    if match_sound:
        sound_tag = match_sound.group(1).strip()
        mapped_id = None
        for s in audio_config.get("soundscapes", []):
            if sound_tag.lower() in s.get("label", "").lower():
                mapped_id = s.get("track_id"); break
        if mapped_id:
            background_tasks.add_task(async_audio_manager, mapped_id)
        
        # SCENE TRIGGER
        pending_prompt = re.sub(r"\[.*?\]", "", clean_text).strip()[:400]
        image_type = "scene"

    # 2. Actor Logic (Overrides Scene)
    match_actor = re.search(r"\[ACTOR:\s*(.*?)\]", clean_text, re.IGNORECASE)
    if match_actor:
        actor_full_tag = match_actor.group(1).strip()
        found_voice = get_voice_for_role(actor_full_tag, audio_config)
        if found_voice: active_voice_id = found_voice
        
        # NPC TRIGGER
        if image_type == "none": # Only if no scene change
            desc_text = re.sub(r"\[.*?\]", "", clean_text).strip()[:300]
            # STRICT ART STYLE
            pending_prompt = f"Oil painting of D&D Character: {actor_full_tag}. {desc_text}. Grim realism."
            image_type = "npc"

    clean_text = re.sub(r"\[SOUND:.*?\]", "", clean_text, flags=re.IGNORECASE)
    clean_text = re.sub(r"\[ACTOR:.*?\]", "", clean_text, flags=re.IGNORECASE) 
    clean_text = clean_text.strip()

    if any(x in payload.message.lower() for x in ["show", "draw", "image"]):
        pending_prompt = clean_text[:300]
        image_type = "scene"

    paths = get_campaign_paths()
    return {
        "response": clean_text, 
        "voice_id": active_voice_id, 
        "pending_image_prompt": pending_prompt,
        "image_type": image_type, # Instructs Bot what to do
        "active_campaign": paths["name"]
    }

# ... (TTS Endpoint unchanged) ...
@router.post("/tts")
async def text_to_speech(payload: TTSRequest):
    key = os.getenv("ELEVENLABS_API_KEY")
    if not key: return Response(content=b"", status_code=500)
    voices_to_try = [payload.voice_id, DM_VOICE_ID, FALLBACK_VOICE_ID]
    voices_to_try = [v for v in voices_to_try if v]

    for vid in voices_to_try:
        try:
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{vid}?optimize_streaming_latency=3"
            r = requests.post(url, json={"text": payload.text[:2000], "model_id": "eleven_monolingual_v1"}, headers={"xi-api-key": key}, timeout=15)
            if r.status_code == 200: return Response(content=r.content, media_type="audio/mpeg")
        except: continue
    return Response(content=b"", status_code=500)

@router.get("/discord/members")
def get_discord_members():
    if r_client:
        try: return json.loads(r_client.get("discord_roster"))
        except: pass
    return [{"id": "bot", "name": "RealmQuest Bot", "status": "online", "role": "System"}]

@router.get("/brain/status")
def get_brain_status(): return {"status": "online", "turns": len(CHAT_HISTORY)}

@router.post("/brain/wipe")
def wipe_memory():
    global CHAT_HISTORY; CHAT_HISTORY = []; return {"status": "wiped"}

@router.post("/brain/prompt")
def update_prompt(payload: PromptUpdate):
    global SYSTEM_PROMPT_OVERRIDE; SYSTEM_PROMPT_OVERRIDE = payload.prompt; return {"status": "updated"}
    
@router.post("/imagine")
async def generate_image(payload: ImageRequest):
    if not ai_available: return {"error": "AI Engine Offline"}
    paths = get_campaign_paths()
    os.makedirs(paths["images"], exist_ok=True)
    
    # REALISTIC ART STYLE INJECTION
    style_prompt = f"Dungeons & Dragons 5e art, oil painting, realistic lighting, grim fantasy, detailed. NO cartoons. {payload.prompt}"
    
    fn, err = ai.generate_image(style_prompt, paths["root"], style="Cinematic Fantasy")
    if err: raise HTTPException(status_code=500, detail=err)
    return {"status": "success", "filename": fn}