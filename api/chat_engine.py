# ===============================================================
# Script Name: chat_engine.py
# Script Location: /opt/RealmQuest/api/chat_engine.py
# Date: 2026-01-27
# Version: 18.82.0 (Asynchronous Flow)
# ===============================================================

import os
import json
import redis
import re
import requests
import time
from fastapi import APIRouter, Response, BackgroundTasks
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
FALLBACK_VOICE_ID = "onwK4e9ZLuTAKqWW03F9"

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
# REMOVED: SYSTEM_PROMPT_OVERRIDE global to prevent leakage

# --- HELPERS ---

def get_active_campaign_name():
    if db is None: return "default"
    try:
        conf = db["system_config"].find_one({"config_id": "audio_registry"})
        if conf and "active_campaign" in conf: return conf["active_campaign"]
    except: pass
    return "default"

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

def get_voice_for_role(actor_tag, audio_registry):
    tag = actor_tag.lower()
    if tag.strip() in ARCHETYPE_DB: return ARCHETYPE_DB[tag.strip()]
    for name, vid in VOICE_DB.items():
        if tag in name: return vid
    
    # Heuristics
    if any(x in tag for x in ["maid", "woman", "lady", "girl", "queen", "mother"]):
        return ARCHETYPE_DB.get("female") or ARCHETYPE_DB.get("old_woman")
    if any(x in tag for x in ["man", "boy", "king", "prince", "lord", "sir", "bartender"]):
        return ARCHETYPE_DB.get("male") or ARCHETYPE_DB.get("old_man")
    if any(x in tag for x in ["guard", "soldier", "warrior", "captain", "thug"]):
        return ARCHETYPE_DB.get("guard") or ARCHETYPE_DB.get("thug")
    if any(x in tag for x in ["goblin", "orc", "monster", "beast", "dragon"]):
        return ARCHETYPE_DB.get("monster")

    return DM_VOICE_ID or audio_registry.get("dmVoice")

# BACKGROUND AUDIO TASK (Non-Blocking)
def async_audio_manager(mapped_track_id):
    if not mapped_track_id or str(mapped_track_id).startswith("sys_"): return
    
    print(f"🎵 ASYNC AUDIO: Starting {mapped_track_id}")
    try:
        # 1. Kill old audio
        requests.post(f"{KENKU_URL}/v1/soundboard/stop", timeout=0.5)
        requests.post(f"{KENKU_URL}/v1/playlist/playback/pause", timeout=0.5)
        
        # 2. Set Volume Low (Background Mode)
        # Kenku API volume is usually 0.0 to 1.0
        requests.put(f"{KENKU_URL}/v1/playlist/volume", json={"volume": 0.4}, timeout=0.5)
        
        # 3. Play New Track
        requests.put(f"{KENKU_URL}/v1/playlist/play", json={"id": mapped_track_id}, timeout=0.5)
        requests.put(f"{KENKU_URL}/v1/soundboard/play", json={"id": mapped_track_id}, timeout=0.5)
    except Exception as e:
        print(f"❌ AUDIO ERROR: {e}")

# BACKGROUND ASSET TASKS
def async_create_npc_profile(name, description, location, voice_id):
    if not ai_available: return
    paths = get_campaign_paths()
    os.makedirs(paths["npcs"], exist_ok=True); os.makedirs(paths["images"], exist_ok=True)
    
    clean_name = name.split(',')[0].strip()
    safe_name = re.sub(r'[^a-zA-Z0-9]', '_', clean_name).lower()
    
    image_filename = ""
    try:
        img_prompt = f"Fantasy Character Portrait: {name}, {description[:150]}"
        image_filename, _ = ai.generate_image(img_prompt, paths["images"], style="Cinematic Fantasy")
    except: pass

    try:
        rel_path = f"assets/images/{image_filename}" if image_filename else ""
        profile = {
            "name": clean_name, "desc": description, "location": location,
            "voice_id": voice_id, "image": rel_path, 
            "stats": {"class": "Commoner", "level": 1}, "created_at": time.time()
        }
        with open(os.path.join(paths["npcs"], f"{safe_name}.json"), "w") as f:
            json.dump(profile, f, indent=2)
    except: pass

def async_generate_environment(prompt):
    if not ai_available: return
    paths = get_campaign_paths()
    os.makedirs(paths["images"], exist_ok=True)
    try:
        full_prompt = f"Fantasy D&D Environment: {prompt}"
        ai.generate_image(full_prompt, paths["images"], style="Cinematic Fantasy")
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
    available_archetypes = list(ARCHETYPE_DB.keys())
    dm_name = audio_config.get('dmName', 'DM')
    
    # SYSTEM PROMPT (Hidden from history to prevent leakage)
    system_instruction = (
        f"You are {dm_name}, the Dungeon Master. I am the Player ({payload.player_name}).\n"
        "**ROLEPLAY ONLY.** Do not explain rules. Do not quote directives. Just play.\n"
        "1. **REALITY:** You narrate the world. If I do something impossible, describe the failure naturally.\n"
        f"2. **SOUNDS:** Start scenes with `[SOUND: Label]`. Options: {', '.join(available_sounds)}.\n"
        f"3. **CASTING:** For NPCs, use `[ACTOR: Name, Role]`. Example: `[ACTOR: Elara, Barmaid]`.\n"
        "4. **BRIVITY:** Keep descriptions under 4 sentences."
    )
    
    # USER INPUT
    CHAT_HISTORY.append({"role": "user", "content": payload.message})
    if len(CHAT_HISTORY) > 6: CHAT_HISTORY.pop(0)

    # GENERATE
    full_prompt = f"SYSTEM: {system_instruction}\n\n"
    for turn in CHAT_HISTORY:
        full_prompt += f"{turn['role'].upper()}: {turn['content']}\n"
    full_prompt += "ASSISTANT:"

    raw_response = ai.generate_story(system_instruction, full_prompt)
    
    # CLEANUP (Remove hallucinations)
    raw_response = re.sub(r"\|\s*VOICE_ID:[^\]]+", "", raw_response)
    if payload.message[:10].lower() in raw_response.lower():
        raw_response = raw_response.replace(payload.message, "").strip()

    print(f"🧠 RAW: {raw_response}")
    CHAT_HISTORY.append({"role": "assistant", "content": raw_response})

    clean_text = raw_response
    active_voice_id = DM_VOICE_ID or FALLBACK_VOICE_ID
    current_location = "Unknown"
    pending_image_prompt = None
    
    # --- LOGIC ---
    
    # 1. Sound (Async Trigger)
    match_sound = re.search(r"\[SOUND:\s*(.*?)\]", clean_text, re.IGNORECASE)
    if match_sound:
        sound_tag = match_sound.group(1).strip()
        current_location = sound_tag
        
        # Find ID
        mapped_id = None
        for s in audio_config.get("soundscapes", []):
            if sound_tag.lower() in s.get("label", "").lower():
                mapped_id = s.get("track_id"); break
        
        if mapped_id:
            # FIRE AND FORGET - Don't wait for audio to start
            background_tasks.add_task(async_audio_manager, mapped_id)
        
        pending_image_prompt = re.sub(r"\[.*?\]", "", clean_text).strip()[:400]
        background_tasks.add_task(async_generate_environment, pending_image_prompt)

    # 2. Actor
    match_actor = re.search(r"\[ACTOR:\s*(.*?)\]", clean_text, re.IGNORECASE)
    if match_actor:
        actor_full_tag = match_actor.group(1).strip()
        found_voice = get_voice_for_role(actor_full_tag, audio_config)
        if found_voice: active_voice_id = found_voice
        
        if not match_sound: 
            desc_text = re.sub(r"\[.*?\]", "", clean_text).strip()[:300]
            background_tasks.add_task(async_create_npc_profile, actor_full_tag, desc_text, current_location, active_voice_id)
            pending_image_prompt = f"Fantasy Portrait: {actor_full_tag}, {desc_text}"

    clean_text = re.sub(r"\[SOUND:.*?\]", "", clean_text, flags=re.IGNORECASE)
    clean_text = re.sub(r"\[ACTOR:.*?\]", "", clean_text, flags=re.IGNORECASE) 
    clean_text = clean_text.strip()

    # Manual Image
    image_data = None
    if any(x in payload.message.lower() for x in ["show", "draw", "image"]):
        prompt = clean_text[:300]
        pending_image_prompt = prompt

    paths = get_campaign_paths()
    active_campaign_name = paths["name"]

    return {
        "response": clean_text, 
        "voice_id": active_voice_id, 
        "image": image_data,
        "pending_image_prompt": pending_image_prompt,
        "active_campaign": active_campaign_name
    }

# --- TTS ENDPOINT ---
@router.post("/tts")
async def text_to_speech(payload: TTSRequest):
    key = os.getenv("ELEVENLABS_API_KEY")
    if not key: return Response(content=b"", status_code=500)
    
    # Priority: 1. Requested ID, 2. Global DM Voice, 3. Hard Safe
    voices_to_try = [payload.voice_id, DM_VOICE_ID, "onwK4e9ZLuTAKqWW03F9"]
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
    fn, err = ai.generate_image(payload.prompt, paths["images"], style="Cinematic Fantasy")
    if err: raise HTTPException(status_code=500, detail=err)
    return {"status": "success", "filename": fn}