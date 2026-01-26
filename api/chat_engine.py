# ===============================================================
# Script Name: chat_engine.py
# Script Location: /opt/RealmQuest/api/chat_engine.py
# Date: 2026-01-26
# Version: 18.14.0
# About: Ambient Sound (Kenku) & Auto-NPC Creation (The Codex)
# ===============================================================

import os
import json
import redis
import re
import requests
import time
from fastapi import APIRouter, Response, HTTPException, Body
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

# --- MODELS ---
class ChatRequest(BaseModel):
    message: str
    discord_id: str
    player_name: str
    is_meta: bool = False

class ImageRequest(BaseModel):
    prompt: str

class PromptUpdate(BaseModel):
    prompt: str

class TTSRequest(BaseModel):
    text: str
    voice_id: str

CHAT_HISTORY = [] 
SYSTEM_PROMPT_OVERRIDE = ""
FALLBACK_VOICE_ID = "21m00Tcm4TlvDq8ikWAM" # Rachel

# --- AUDIO MATRIX: SOUNDSCAPES (Kenku FM) ---
# Map simple keywords to Kenku Track IDs (UUIDs)
# In production, these would come from the Portal Config
SOUND_CONSTANTS = {
    "tavern": "track_tavern_uuid_123",
    "rain": "track_rain_uuid_456",
    "storm": "track_storm_uuid_789",
    "forest": "track_forest_uuid_101",
    "dungeon": "track_dungeon_uuid_112",
    "combat": "track_combat_uuid_131",
    "battle": "track_combat_uuid_131",
    "wind": "track_wind_uuid_415",
    "fire": "track_fire_uuid_161",
    "camp": "track_fire_uuid_161"
}

# --- VOICE ROSTER (Smart Casting) ---
VOICE_ROSTER = [
    {"name": "Roger", "id": "CwhRBWXzGAHq8TQ4Fs17", "gender": "male", "tags": ["laid-back", "casual"]},
    {"name": "Sarah", "id": "EXAVITQu4vr4xnSDxMaL", "gender": "female", "tags": ["mature", "confident"]},
    {"name": "Laura", "id": "FGY2WhTYpPnrIDTdsKH5", "gender": "female", "tags": ["quirky", "enthusiast"]},
    {"name": "Charlie", "id": "IKne3meq5aSn9XLyUdCD", "gender": "male", "tags": ["deep", "confident"]},
    {"name": "George", "id": "JBFqnCBsd6RMkjVDRZzb", "gender": "male", "tags": ["warm", "storyteller"]},
    {"name": "Callum", "id": "N2lVS1w4EtoT3dr4eOWO", "gender": "male", "tags": ["husky", "trickster"]},
    {"name": "River", "id": "SAz9YHcvj6GT2YYXdXww", "gender": "neutral", "tags": ["relaxed", "neutral"]},
    {"name": "Harry", "id": "SOYHLrjzK2X1ezoPC6cr", "gender": "male", "tags": ["fierce", "warrior"]},
    {"name": "Liam", "id": "TX3LPaxmHKxFdv7VOQHJ", "gender": "male", "tags": ["energetic"]},
    {"name": "Alice", "id": "Xb7hH8MSUJpSbSDYk0k2", "gender": "female", "tags": ["clear", "educator"]},
    {"name": "Matilda", "id": "XrExE9yKIg1WjnnlVkGX", "gender": "female", "tags": ["knowledgeable", "professional"]},
    {"name": "Will", "id": "bIHbv24MWmeRgasZH58o", "gender": "male", "tags": ["relaxed", "optimist"]},
    {"name": "Jessica", "id": "cgSgspJ2msm6clMCkdW9", "gender": "female", "tags": ["playful", "warm"]},
    {"name": "Eric", "id": "cjVigY5qzO86Huf0OWal", "gender": "male", "tags": ["smooth", "trustworthy"]},
    {"name": "Chris", "id": "iP95p4xoKVk53GoZ742B", "gender": "male", "tags": ["charming"]},
    {"name": "Brian", "id": "nPczCjzI2devNBz1zQrb", "gender": "male", "tags": ["deep", "comforting"]},
    {"name": "Daniel", "id": "onwK4e9ZLuTAKqWW03F9", "gender": "male", "tags": ["steady"]},
    {"name": "Lily", "id": "pFZP5JQG7iQjIQuC4Bku", "gender": "female", "tags": ["velvety", "actress"]},
    {"name": "Adam", "id": "pNInz6obpgDQGcFmaJgB", "gender": "male", "tags": ["dominant", "firm"]},
    {"name": "Bill", "id": "pqHfZKP75CvOlQylNhV4", "gender": "male", "tags": ["wise", "mature"]}
]

# --- SMART CASTING LOGIC ---
def smart_cast(role_name):
    role = role_name.lower()
    gender = "male" 
    female_triggers = ["queen", "maid", "lady", "witch", "girl", "woman", "mother", "sister", "princess", "actress", "waitress", "matron", "crone", "goddess", "barmaid"]
    if any(x in role for x in female_triggers): gender = "female"
    
    if gender == "female":
        if "maid" in role or "waitress" in role: return "cgSgspJ2msm6clMCkdW9" # Jessica
        if "queen" in role or "noble" in role: return "pFZP5JQG7iQjIQuC4Bku" # Lily
        if "witch" in role or "hag" in role: return "FGY2WhTYpPnrIDTdsKH5" # Laura
        if "guard" in role or "warrior" in role: return "EXAVITQu4vr4xnSDxMaL" # Sarah
        return "EXAVITQu4vr4xnSDxMaL" # Sarah (Default)

    # Male/Neutral
    if "king" in role or "lord" in role: return "pNInz6obpgDQGcFmaJgB" # Adam
    if "guard" in role or "soldier" in role or "orc" in role: return "SOYHLrjzK2X1ezoPC6cr" # Harry
    if "wizard" in role or "priest" in role: return "pqHfZKP75CvOlQylNhV4" # Bill
    if "goblin" in role or "thief" in role: return "N2lVS1w4EtoT3dr4eOWO" # Callum
    if "inn" in role or "keep" in role or "bartender" in role: return "JBFqnCBsd6RMkjVDRZzb" # George
    if "villain" in role or "demon" in role: return "IKne3meq5aSn9XLyUdCD" # Charlie
    
    return "pNInz6obpgDQGcFmaJgB" # Adam (Default)

# --- VOICE CACHE ---
VOICE_CACHE = {}
LAST_VOICE_FETCH = 0

def refresh_elevenlabs_voices():
    global VOICE_CACHE, LAST_VOICE_FETCH
    key = os.getenv("ELEVENLABS_API_KEY")
    if not key: return
    if time.time() - LAST_VOICE_FETCH < 600 and VOICE_CACHE: return
    try:
        r = requests.get("https://api.elevenlabs.io/v1/voices", headers={"xi-api-key": key}, timeout=5)
        if r.status_code == 200:
            VOICE_CACHE = {v["name"].lower(): v["voice_id"] for v in r.json().get("voices", [])}
            LAST_VOICE_FETCH = time.time()
            print(f"✅ VOICE CACHE: Loaded {len(VOICE_CACHE)} voices.")
    except: pass

# --- HELPER: SAVE NPC NOTE ---
def save_npc_codex(npc_data, image_file, voice_id, campaign_path):
    """Writes a JSON dossier for the new NPC"""
    try:
        # Ensure directory exists: /campaigns/default/codex/npcs/
        codex_dir = os.path.join(campaign_path, "codex", "npcs")
        os.makedirs(codex_dir, exist_ok=True)
        
        # Clean filename
        safe_name = re.sub(r'[^a-zA-Z0-9]', '_', npc_data.get("name", "Unknown")).lower()
        file_path = os.path.join(codex_dir, f"{safe_name}.json")
        
        # Enrich Data
        npc_data["voice_id"] = voice_id
        npc_data["image"] = f"assets/images/{image_file}" if image_file else None
        npc_data["created_at"] = time.time()
        
        with open(file_path, "w") as f:
            json.dump(npc_data, f, indent=2)
            
        print(f"📜 CODEX UPDATED: Saved {safe_name}.json")
    except Exception as e:
        print(f"❌ CODEX ERROR: {e}")

# --- HELPER: TRIGGER KENKU ---
def trigger_sound(tag):
    """Sends command to Kenku Bridge (Mock for now, ready for implementation)"""
    track_id = SOUND_CONSTANTS.get(tag.lower())
    if track_id:
        print(f"🎵 KENKU PLAY: {tag} ({track_id})")
        # requests.post("http://rq-kenku:3333/play", json={"id": track_id}) 
    else:
        print(f"⚠️ KENKU: Sound '{tag}' not found in constants.")

# --- ENDPOINTS ---

@router.get("/brain/status")
def get_brain_status():
    return {
        "history": CHAT_HISTORY[-10:],
        "system_prompt": SYSTEM_PROMPT_OVERRIDE or "Default DM Protocol",
        "stats": {"tokens": sum(len(m['content']) for m in CHAT_HISTORY) // 4, "turns": len(CHAT_HISTORY)}
    }

@router.post("/brain/wipe")
def wipe_memory():
    global CHAT_HISTORY
    CHAT_HISTORY = []
    return {"status": "wiped"}

@router.post("/brain/prompt")
def update_prompt(payload: PromptUpdate):
    global SYSTEM_PROMPT_OVERRIDE
    SYSTEM_PROMPT_OVERRIDE = payload.prompt
    return {"status": "updated"}

@router.post("/chat/generate")
async def generate_response(payload: ChatRequest):
    if not ai_available: return {"response": "Brain Offline.", "voice_id": "default"}
    
    refresh_elevenlabs_voices()

    # 1. FETCH CONFIG
    active_campaign = "default"
    dm_name = "DM"
    active_voice_id = "default"
    art_style = "Cinematic Fantasy"
    matrix_archetypes = {}
    
    if db is not None:
        sys_conf = db["system_config"].find_one({"config_id": "main"})
        if sys_conf: 
            active_campaign = sys_conf.get("active_campaign", "default")
            art_style = sys_conf.get("art_style", art_style)
        
        audio_conf = db["system_config"].find_one({"config_id": "audio_registry"})
        if audio_conf:
            dm_name = audio_conf.get("dmName", "DM")
            v_val = audio_conf.get("dmVoice", "default")
            active_voice_id = v_val.get("id", "default") if isinstance(v_val, dict) else v_val
            
            raw_arch = audio_conf.get("archetypes", [])
            for arc in raw_arch:
                if arc.get("label") and arc.get("voice_id"):
                    matrix_archetypes[arc["label"].lower()] = arc["voice_id"]

    # 2. PLAYER CONTEXT
    player_context = ""
    if db is not None:
        char_data = db["players"].find_one({"discord_id": payload.discord_id})
        if char_data:
            player_context = (
                f"\n[CURRENT SPEAKER]: {char_data.get('name')} (Lvl {char_data.get('level')} {char_data.get('class_name')})"
            )
    
    # 3. PROMPT CONSTRUCTION
    if payload.is_meta:
        system_prompt = "YOU ARE: The Oracle. GOAL: Answer D&D 5e rules concisely. TONE: OOC. NO ROLEPLAY."
    else:
        base_prompt = SYSTEM_PROMPT_OVERRIDE or (
            f"You are {dm_name}, the Dungeon Master. "
            "RULES: "
            "1. Keep responses CONCISE (max 3 sentences). "
            "2. If introducing a NEW scene, output [IMAGE: description] and [SOUND: tag]. "
            "3. If a NEW NPC is introduced, output [NPC_NEW: {\"name\": \"...\", \"desc\": \"...\", \"location\": \"...\"}]. "
            "4. If an NPC speaks, output [ACTOR: Name]. "
            "5. Speak naturally. Do not use markdown."
        )
        system_prompt = base_prompt + player_context

    # 4. GENERATE
    raw_response = ai.generate_story(system_prompt, payload.message)
    
    # 5. PARSE & PROCESS
    clean_text = raw_response
    image_data = None
    npc_data_payload = None
    
    # A. IMAGE
    match_img = re.search(r"\[IMAGE:\s*(.*?)\]", clean_text, re.IGNORECASE | re.DOTALL)
    if match_img:
        visual_prompt = match_img.group(1).strip()
        clean_text = clean_text.replace(match_img.group(0), "").strip()
        campaign_path = os.path.join("/campaigns", active_campaign)
        filename, err = ai.generate_image(visual_prompt, campaign_path, style=art_style)
        if filename:
            image_data = {"filename": filename, "prompt": visual_prompt}

    # B. SOUND (Kenku)
    match_sound = re.search(r"\[SOUND:\s*(.*?)\]", clean_text, re.IGNORECASE)
    if match_sound:
        sound_tag = match_sound.group(1).strip()
        clean_text = clean_text.replace(match_sound.group(0), "").strip()
        trigger_sound(sound_tag)

    # C. NPC NEW (Codex)
    match_npc = re.search(r"\[NPC_NEW:\s*({.*?})\]", clean_text, re.IGNORECASE | re.DOTALL)
    if match_npc:
        try:
            json_str = match_npc.group(1).strip()
            npc_data_payload = json.loads(json_str)
            clean_text = clean_text.replace(match_npc.group(0), "").strip()
        except:
            print("⚠️ Failed to parse NPC JSON")

    # D. ACTOR (Voice)
    match_actor = re.search(r"\[ACTOR:\s*(.*?)\]", clean_text, re.IGNORECASE)
    if match_actor:
        actor_name = match_actor.group(1).strip()
        actor_key = actor_name.lower()
        clean_text = clean_text.replace(match_actor.group(0), "").strip()
        
        # Priority Logic
        if actor_key in matrix_archetypes:
            active_voice_id = matrix_archetypes[actor_key]
        else:
            smart_id = smart_cast(actor_name)
            if smart_id: active_voice_id = smart_id
            elif actor_key in VOICE_CACHE: active_voice_id = VOICE_CACHE[actor_key]

    # 6. SAVE CODEX (If new NPC was detected)
    if npc_data_payload:
        campaign_path = os.path.join("/campaigns", active_campaign)
        # Use the voice ID we just assigned (or default if not switched)
        # Use the image we just generated (if any)
        img_file = image_data['filename'] if image_data else None
        save_npc_codex(npc_data_payload, img_file, active_voice_id, campaign_path)

    # 7. HISTORY
    CHAT_HISTORY.append({"role": "user", "content": payload.message})
    CHAT_HISTORY.append({"role": "assistant", "content": clean_text})
    
    return {
        "response": clean_text, 
        "voice_id": active_voice_id, 
        "image": image_data
    }

# ... (Imagine, TTS, Discord Members endpoints remain unchanged) ...
@router.post("/imagine")
async def generate_image(payload: ImageRequest):
    if not ai_available: return {"error": "AI Engine Offline"}
    active_campaign = "default"
    art_style = "Cinematic Fantasy"
    if db is not None:
        sys_conf = db["system_config"].find_one({"config_id": "main"})
        if sys_conf: 
            active_campaign = sys_conf.get("active_campaign", "default")
            art_style = sys_conf.get("art_style", art_style)
    campaign_path = os.path.join("/campaigns", active_campaign)
    filename, error = ai.generate_image(payload.prompt, campaign_path, style=art_style)
    if error: raise HTTPException(status_code=500, detail=error)
    return {"status": "success", "filename": filename}

@router.post("/tts")
async def text_to_speech(payload: TTSRequest):
    key = os.getenv("ELEVENLABS_API_KEY")
    if not key: return Response(content=b"", status_code=500)
    safe_text = payload.text[:600]
    target_voice = payload.voice_id
    if target_voice in ["default", "onyx", ""]: target_voice = FALLBACK_VOICE_ID

    def try_voice(vid):
        try:
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{vid}?optimize_streaming_latency=3"
            r = requests.post(url, json={"text": safe_text, "model_id": "eleven_monolingual_v1"}, headers={"xi-api-key": key, "Content-Type": "application/json"}, timeout=30)
            return r
        except: return None

    response = try_voice(target_voice)
    if not response or response.status_code != 200:
        print(f"⚠️ Voice {target_voice} Failed. Fallback to {FALLBACK_VOICE_ID}.")
        response = try_voice(FALLBACK_VOICE_ID)

    if response and response.status_code == 200: 
        return Response(content=response.content, media_type="audio/mpeg")
    return Response(content=b"", status_code=500)

@router.get("/discord/members")
def get_discord_members():
    if r_client:
        try: return json.loads(r_client.get("discord_roster"))
        except: pass
    return [{"id": "bot", "name": "RealmQuest Bot", "status": "online", "role": "System"}]

@router.get("/roster")
def get_roster(): return []