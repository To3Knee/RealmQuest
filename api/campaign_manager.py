# -----------------------------------------------------------------------------
# RealmQuest API - Campaign/System Manager Router
# File: api/campaign_manager.py
# Version: v18.64.0 (Deep Search JSON Extraction)
# -----------------------------------------------------------------------------

import os
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

import requests
import docker
from dotenv import dotenv_values, set_key, unset_key
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from pymongo import MongoClient

# SETUP LOGGING
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("api")

router = APIRouter()

# -----------------------------
# Mongo & Env Setup
# -----------------------------
MONGO_URL = os.getenv("MONGO_URL", "mongodb://realmquest-mongo:27017/")
try:
    mongo = MongoClient(MONGO_URL, serverSelectionTimeoutMS=2000)
    db = mongo["realmquest"]
except Exception: db = None

# -----------------------------
# SEED DATA
# -----------------------------
DEFAULT_VOICES = [
    {"id": "roger", "label": "Roger", "voice_id": "CwhRBWXzGAHq8TQ4Fs17"},
    {"id": "sarah", "label": "Sarah", "voice_id": "EXAVITQu4vr4xnSDxMaL"},
    {"id": "laura", "label": "Laura", "voice_id": "FGY2WhTYpPnrIDTdsKH5"},
    {"id": "charlie", "label": "Charlie", "voice_id": "IKne3meq5aSn9XLyUdCD"},
    {"id": "george", "label": "George", "voice_id": "JBFqnCBsd6RMkjVDRZzb"},
    {"id": "callum", "label": "Callum", "voice_id": "N2lVS1w4EtoT3dr4eOWO"},
    {"id": "river", "label": "River", "voice_id": "SAz9YHcvj6GT2YYXdXww"},
    {"id": "harry", "label": "Harry", "voice_id": "SOYHLrjzK2X1ezoPC6cr"},
    {"id": "liam", "label": "Liam", "voice_id": "TX3LPaxmHKxFdv7VOQHJ"},
    {"id": "alice", "label": "Alice", "voice_id": "Xb7hH8MSUJpSbSDYk0k2"},
    {"id": "matilda", "label": "Matilda", "voice_id": "XrExE9yKIg1WjnnlVkGX"},
    {"id": "will", "label": "Will", "voice_id": "bIHbv24MWmeRgasZH58o"},
    {"id": "jessica", "label": "Jessica", "voice_id": "cgSgspJ2msm6clMCkdW9"},
    {"id": "eric", "label": "Eric", "voice_id": "cjVigY5qzO86Huf0OWal"},
    {"id": "chris", "label": "Chris", "voice_id": "iP95p4xoKVk53GoZ742B"},
    {"id": "brian", "label": "Brian", "voice_id": "nPczCjzI2devNBz1zQrb"},
    {"id": "daniel", "label": "Daniel", "voice_id": "onwK4e9ZLuTAKqWW03F9"},
    {"id": "lily", "label": "Lily", "voice_id": "pFZP5JQG7iQjIQuC4Bku"},
    {"id": "adam", "label": "Adam", "voice_id": "pNInz6obpgDQGcFmaJgB"},
    {"id": "bill", "label": "Bill", "voice_id": "pqHfZKP75CvOlQylNhV4"},
    {"id": "rcbruh", "label": "RCBruh", "voice_id": "8y2HqT4TID923rG2Vc75"}
]

DEFAULT_ARCHETYPE_MAP = {
    "male": "roger", "female": "sarah", "child": "jessica", "wizard": "bill",
    "old_man": "george", "old_woman": "matilda", "guard": "adam", "villain": "charlie",
    "noble": "daniel", "merchant": "river", "thug": "callum", "monster": "harry", "spirit": "lily"
}

DEFAULT_SOUND_SEEDS = [
    {"id": "sys_tavern", "name": "Ambience: Tavern Bustle"},
    {"id": "sys_forest", "name": "Ambience: Forest Day"},
    {"id": "sys_dungeon", "name": "Ambience: Dungeon Creepy"},
    {"id": "sys_combat", "name": "Music: General Combat"},
    {"id": "sys_boss", "name": "Music: Boss Battle"},
    {"id": "sys_rain", "name": "Ambience: Heavy Rain"},
    {"id": "sys_fire", "name": "SFX: Campfire Crackle"},
    {"id": "sys_door", "name": "SFX: Door Creak"},
    {"id": "sys_spell", "name": "SFX: Magic Spell"},
    {"id": "sys_sword", "name": "SFX: Sword Clash"},
    {"id": "sys_roar", "name": "SFX: Monster Roar"}
]

FALLBACK_VOICE_ID = "onwK4e9ZLuTAKqWW03F9"

# Helper Functions
def _ensure_env_file() -> Path:
    p = Path("/config/.env")
    p.parent.mkdir(parents=True, exist_ok=True)
    if not p.exists(): p.touch()
    return p

def _read_env() -> Dict[str, str]:
    if not Path("/config/.env").is_file(): return {}
    try: return dotenv_values("/config/.env") or {}
    except: return {}

def _get_admin_pin() -> str:
    return os.getenv("ADMIN_PIN", "").strip() or str(_read_env().get("ADMIN_PIN", "")).strip()

class AudioConfig(BaseModel):
    dmVoice: Optional[str] = ""
    dmName: str = "DM"
    archetypes: List[Dict[str, Any]] = []
    soundscapes: List[Dict[str, Any]] = []
    voices: List[Dict[str, Any]] = []

def _coerce_audio_registry(raw: Any) -> Dict[str, Any]:
    reg = raw if isinstance(raw, dict) else {}
    def norm_list(items):
        if not isinstance(items, list): return []
        return [i for i in items if isinstance(i, dict)]
    return {
        "config_id": "audio_registry",
        "dmName": str(reg.get("dmName") or "DM"),
        "dmVoice": str(reg.get("dmVoice") or FALLBACK_VOICE_ID),
        "archetypes": norm_list(reg.get("archetypes")),
        "soundscapes": norm_list(reg.get("soundscapes")),
        "voices": norm_list(reg.get("voices"))
    }

def repair_audio_config():
    if db is None: return
    try:
        conf = db["system_config"].find_one({"config_id": "audio_registry"})
        if not conf:
            payload = {
                "config_id": "audio_registry",
                "dmVoice": FALLBACK_VOICE_ID,
                "dmName": "DM",
                "voices": DEFAULT_VOICES,
                "archetypes": [{"role": k, "voice_label": v, "voice_id": ""} for k, v in DEFAULT_ARCHETYPE_MAP.items()],
                "soundscapes": []
            }
            db["system_config"].update_one({"config_id": "audio_registry"}, {"$set": payload}, upsert=True)
            return

        existing_roles = {a.get("role") for a in conf.get("archetypes", [])}
        new_entries = []
        for role, v_label in DEFAULT_ARCHETYPE_MAP.items():
            if role not in existing_roles:
                new_entries.append({"role": role, "voice_label": v_label, "voice_id": ""})
        if new_entries:
            db["system_config"].update_one({"config_id": "audio_registry"}, {"$push": {"archetypes": {"$each": new_entries}}})
    except Exception: pass

@router.get("/config")
def get_system_config():
    repair_audio_config()
    config = {
        "active_campaign": "the_collision_stone",
        "llm_provider": os.getenv("AI_PROVIDER", "Gemini-Flash"),
        "art_style": "Cinematic Fantasy",
        "audio_registry": _coerce_audio_registry({})
    }
    if db is not None:
        try:
            audio_conf = db["system_config"].find_one({"config_id": "audio_registry"}, {"_id": 0})
            if audio_conf: config["audio_registry"] = _coerce_audio_registry(audio_conf)
        except: pass
    return config

@router.post("/audio/save")
def save_audio_config(payload: AudioConfig):
    if db is None: raise HTTPException(status_code=500, detail="Mongo unavailable")
    try:
        data = _coerce_audio_registry(payload.dict())
        db["system_config"].update_one({"config_id": "audio_registry"}, {"$set": data}, upsert=True)
        return {"ok": True, "saved": True, "audio_registry": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB Write Error: {e}")

@router.get("/auth/status")
def auth_status(): return {"locked": False, "has_pin": bool(_get_admin_pin())}

@router.get("/env/all")
def env_all(): return [{"key": k, "value": v} for k, v in sorted(_read_env().items())]

@router.post("/env")
def env_set(payload: dict):
    p = Path("/config/.env")
    if not p.exists(): p.touch()
    key, val = str(payload.get("key", "")).strip(), str(payload.get("value", "")).strip()
    if not key: raise HTTPException(400, "Missing key")
    if not val: unset_key(p, key); return {"deleted": key}
    set_key(p, key, val); return {"set": key, "val": val}

ELEVEN_API_KEY = os.getenv("ELEVENLABS_API_KEY", "").strip()
@router.get("/audio/voices")
def list_voices():
    if not ELEVEN_API_KEY: return []
    try:
        r = requests.get("https://api.elevenlabs.io/v1/voices", headers={"xi-api-key": ELEVEN_API_KEY}, timeout=5)
        return [{"id": v["voice_id"], "name": v["name"]} for v in r.json().get("voices", [])]
    except: return []

# -----------------------------
# KENKU BRIDGE (Deep Search)
# -----------------------------
KENKU_URL = os.getenv("KENKU_URL", "http://realmquest-kenku:3333").rstrip("/")

def _docker_client():
    try: return docker.DockerClient(base_url="unix:///var/run/docker.sock")
    except: return None

# HELPER: RECURSIVE TRACK FINDER
def _extract_tracks_recursive(data: Any, tracks: List[Dict[str, str]]):
    """
    Crawls arbitrary JSON to find objects that look like audio tracks.
    A 'Track' is defined as a dict with an 'id' and either 'url' or 'title'.
    """
    if isinstance(data, dict):
        # Is this a track?
        if "id" in data and ("url" in data or "title" in data):
            # It's a track!
            title = data.get("title") or data.get("url") or data.get("id") or "Unknown"
            
            # Special case for Playlist Items: they might have a nested 'track' object
            if "track" in data and isinstance(data["track"], dict):
                title = data["track"].get("title") or title
                
            tracks.append({
                "id": data["id"],
                "name": f"[File] {title}",
                "source": "kenku_scan"
            })
        
        # Recurse values
        for key, value in data.items():
            _extract_tracks_recursive(value, tracks)
            
    elif isinstance(data, list):
        # Recurse items
        for item in data:
            _extract_tracks_recursive(item, tracks)

@router.get("/audio/kenku/tracks")
def list_kenku_tracks():
    real_tracks = []
    
    logger.info(f"🎵 KENKU: Connecting to {KENKU_URL}...")
    
    # 1. FETCH EVERYTHING
    try:
        # Try Playlist Endpoint
        r_pl = requests.get(f"{KENKU_URL}/v1/playlist", timeout=3)
        if r_pl.status_code == 200:
            _extract_tracks_recursive(r_pl.json(), real_tracks)
            
        # Try Soundboard Endpoint
        r_sb = requests.get(f"{KENKU_URL}/v1/soundboard", timeout=3)
        if r_sb.status_code == 200:
            _extract_tracks_recursive(r_sb.json(), real_tracks)
            
        # Remove duplicates based on ID
        unique_tracks = {t['id']: t for t in real_tracks}.values()
        real_tracks = list(unique_tracks)
        
        logger.info(f"✅ KENKU: Deep Scan found {len(real_tracks)} real tracks.")
        
    except Exception as e:
        logger.error(f"❌ KENKU SCAN FAIL: {e}")

    # 2. ADD PHANTOM TRACKS (System Defaults)
    phantom_tracks = []
    for seed in DEFAULT_SOUND_SEEDS:
        phantom_tracks.append({
            "id": seed["id"],
            "name": f"✨ {seed['name']} (System Default)",
            "source": "system_phantom"
        })

    # Combine
    final_list = real_tracks + phantom_tracks
    logger.info(f"📦 RETURNING TOTAL: {len(final_list)} (Real: {len(real_tracks)} / Ghost: {len(phantom_tracks)})")
    return final_list

@router.get("/control/logs/{service}")
def control_logs(service: str):
    cli = _docker_client()
    if not cli: return "Docker Error"
    try: return cli.containers.get(service if "realmquest" in service else f"realmquest-{service.replace('rq-', '')}").logs(tail=400).decode("utf-8", "ignore")
    except Exception as e: return str(e)

@router.post("/control/restart/{service}")
def control_restart(service: str):
    cli = _docker_client()
    if not cli: return {"ok": False}
    try:
        cli.containers.get(service if "realmquest" in service else f"realmquest-{service.replace('rq-', '')}").restart()
        return {"ok": True}
    except: return {"ok": False}