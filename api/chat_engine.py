# ===============================================================
# Script Name: chat_engine.py
# Script Location: /opt/RealmQuest/api/chat_engine.py
# Date: 2026-01-31
# Version: 21.1.1 (Canonical campaign id + imagine payload hardening)
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

from system_config import get_active_campaign_id

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
    # Optional routing metadata (backwards compatible; bot can pass these)
    kind: str | None = None            # e.g. "npc", "scene", "generic"
    npc_name: str | None = None        # Used when kind == "npc"
    output_filename: str | None = None # Advanced: force filename (server will sanitize)

    # Optional metadata (backwards compatible; prevents gallery/index crashes)
    player_name: str | None = None
    discord_id: str | None = None
    source: str | None = None

class PromptUpdate(BaseModel):
    prompt: str

CHAT_HISTORY = []
SYSTEM_PROMPT_OVERRIDE = ""

def _slugify(value: str) -> str:
    value = (value or "").strip().lower()
    value = re.sub(r"[^a-z0-9\s_-]", "", value)
    value = re.sub(r"[\s_-]+", "-", value).strip("-")
    return value or "npc"


def _norm_key(s: str) -> str:
    return "".join([c for c in (s or "").lower() if c.isalnum()])

def _best_match_npc_json(npcs_dir: str, npc_name: str) -> str | None:
    """Find an existing NPC dossier basename that matches npc_name."""
    try:
        import difflib
        target = _norm_key(npc_name)
        if not target:
            return None

        candidates = []
        norm_to_stem = {}

        for fn in os.listdir(npcs_dir):
            if not fn.lower().endswith(".json"):
                continue
            stem = os.path.splitext(fn)[0]
            nk = _norm_key(stem)
            if nk:
                candidates.append(nk)
                norm_to_stem[nk] = stem

        if target in norm_to_stem:
            return norm_to_stem[target]

        close = difflib.get_close_matches(target, candidates, n=1, cutoff=0.78)
        if close:
            return norm_to_stem.get(close[0])

        for nk, stem in norm_to_stem.items():
            if target in nk or nk in target:
                return stem
    except Exception:
        return None
    return None

def _load_gallery_index(index_path: str):
    try:
        if not os.path.exists(index_path):
            return []
        with open(index_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return [x for x in data if isinstance(x, dict)]
        if isinstance(data, dict) and isinstance(data.get("items"), list):
            return [x for x in data.get("items") if isinstance(x, dict)]
    except Exception:
        return []
    return []

def _save_gallery_index(index_path: str, items):
    try:
        tmp = index_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(items, f, indent=2, ensure_ascii=False)
        os.replace(tmp, index_path)
    except Exception:
        pass

def _upsert_gallery_entry(index_path: str, entry: dict):
    items = _load_gallery_index(index_path)
    fn = str(entry.get("filename") or "").strip()
    if not fn:
        return
    updated = False
    for i, it in enumerate(items):
        if isinstance(it, dict) and str(it.get("filename") or "").strip() == fn:
            items[i] = {**it, **entry}
            updated = True
            break
    if not updated:
        items.append(entry)
    try:
        items.sort(key=lambda x: float(x.get("created_at_epoch", 0)) if isinstance(x, dict) else 0)
    except Exception:
        pass
    _save_gallery_index(index_path, items)

SYSTEM_PROMPT_OVERRIDE = ""

# --- HELPERS ---

def get_active_campaign_name():
    """Canonical active campaign id (split-brain hardened)."""
    return get_active_campaign_id(db, default=os.getenv("RQ_DEFAULT_CAMPAIGN", "the_collision_stone"))

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

    # Optional runtime override (Neural Config). Prepend so it acts as higher-priority rules.
    if SYSTEM_PROMPT_OVERRIDE.strip():
        system_instruction = SYSTEM_PROMPT_OVERRIDE.strip() + "\n\n" + system_instruction
    
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

    npc_name = None

    # 2. Actor Logic (Overrides Scene)
    npc_name = None
    match_actor = re.search(r"\[ACTOR:\s*(.*?)\]", clean_text, re.IGNORECASE)
    if match_actor:
        actor_full_tag = match_actor.group(1).strip()
        # Extract a stable NPC name for downstream tooling (bot, portal)
        npc_name = actor_full_tag.split(",", 1)[0].strip() or None
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
        "npc_name": npc_name,
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
def get_brain_status():
    return {
        "status": "online" if ai_available else "offline",
        "turns": len(CHAT_HISTORY),
        "history": CHAT_HISTORY,
        "system_prompt": SYSTEM_PROMPT_OVERRIDE,
        "stats": {
            "ai_available": ai_available,
        },
    }

@router.post("/brain/wipe")
def wipe_memory():
    global CHAT_HISTORY; CHAT_HISTORY = []; return {"status": "wiped"}

@router.post("/brain/prompt")
def update_prompt(payload: PromptUpdate):
    global SYSTEM_PROMPT_OVERRIDE; SYSTEM_PROMPT_OVERRIDE = payload.prompt; return {"status": "updated"}
    
@router.post("/imagine")
async def generate_image(payload: ImageRequest):
    """Generate an image and place it into the correct campaign folder.

    Phase 3.5 rules:
      - NPC portraits go to:    /campaigns/<camp>/codex/npcs/
      - All other art goes to: /campaigns/<camp>/assets/images/
      - Maintain gallery context index at /assets/images/gallery.json
    """
    if not ai_available:
        return {"status": "error", "message": "AI Engine Offline"}

    paths = get_campaign_paths()
    os.makedirs(paths["images"], exist_ok=True)
    os.makedirs(paths["npcs"], exist_ok=True)

    kind_raw = (payload.kind or "generic").strip().lower()
    npc_name = (payload.npc_name or "").strip() or None

    # Keep existing cinematic realism style injection
    style_prompt = (
        "Dungeons & Dragons 5e art, oil painting, realistic lighting, grim fantasy, detailed. "
        "NO cartoons. "
        f"{payload.prompt}"
    )

    # Treat npc-like kinds as NPC portraits (backwards compatible)
    is_npc = False
    if npc_name:
        is_npc = True
    if kind_raw.startswith("npc") or ("npc" in kind_raw):
        is_npc = True
    if kind_raw in {"portrait", "character", "hero", "villager"}:
        is_npc = True

    # Decide output filename (sanitize)
    if payload.output_filename:
        out_name = os.path.basename(payload.output_filename.strip())
    elif is_npc:
        base = _best_match_npc_json(paths["npcs"], npc_name) if npc_name else None
        if not base:
            base = _slugify(npc_name or payload.prompt).replace("-", "_")
        out_name = f"{base}.png"
    else:
        out_name = f"vis_{int(time.time())}.png"

    if not re.search(r"\.(png|jpg|jpeg|webp)$", out_name, re.IGNORECASE):
        out_name = out_name + ".png"

    output_dir = paths["npcs"] if is_npc else paths["images"]

    fn, err = ai.generate_image(
        style_prompt,
        paths["root"],
        style="Cinematic Fantasy",
        output_dir=output_dir,
        output_filename=out_name,
    )
    if err:
        raise HTTPException(status_code=500, detail=err)

    if is_npc:
        url = f"/campaigns/{paths['name']}/codex/npcs/{fn}"
        kind_out = "npc"
    else:
        url = f"/campaigns/{paths['name']}/assets/images/{fn}"
        kind_out = (kind_raw or "generic")

    # Gallery context index lives in assets/images/gallery.json (campaign-specific)
    index_path = os.path.join(paths["images"], "gallery.json")
    entry = {
        "filename": fn,
        "url": url,
        "kind": kind_out,
        "prompt": payload.prompt,
        "npc_name": npc_name,
        "npc_id": (_slugify(npc_name).replace("-", "_") if npc_name else None),
        "created_at_epoch": float(time.time()),
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "created_by": (payload.player_name or payload.discord_id or None),
        "source": (payload.source or "unknown"),
    }
    _upsert_gallery_entry(index_path, entry)

    # If NPC portrait and a dossier exists, update its image path to codex/npcs/<file>
    if is_npc and npc_name:
        try:
            stem = _best_match_npc_json(paths["npcs"], npc_name)
            if stem:
                jf = os.path.join(paths["npcs"], f"{stem}.json")
                if os.path.exists(jf):
                    with open(jf, "r", encoding="utf-8") as f:
                        dossier = json.load(f)
                    if isinstance(dossier, dict):
                        dossier["image"] = f"codex/npcs/{fn}"
                        with open(jf, "w", encoding="utf-8") as f:
                            json.dump(dossier, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    return {"status": "success", "filename": fn, "url": url, "campaign": paths["name"], "kind": kind_out}