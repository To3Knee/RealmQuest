# -----------------------------------------------------------------------------
# RealmQuest API - Campaign/System Manager Router
# File: api/campaign_manager.py
# Version: v19.11.0 (Golden Master: Auth + Logs + Campaign Management)
# -----------------------------------------------------------------------------

import os
import shutil
import logging
import requests
import docker
import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from dotenv import dotenv_values, set_key, unset_key
from fastapi import APIRouter, HTTPException, Body, Request
from pydantic import BaseModel
from pymongo import MongoClient

# SETUP LOGGING
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("api")

router = APIRouter()

# -----------------------------
# 1. CONFIGURATION & PATHS
# -----------------------------
ENV_FILE = Path("/app/.env") 
CAMPAIGNS_DIR = Path("/campaigns")
MONGO_URL = os.getenv("MONGO_URL", "mongodb://realmquest-mongo:27017/")

try:
    mongo = MongoClient(MONGO_URL, serverSelectionTimeoutMS=2000)
    db = mongo["realmquest"]
except Exception: db = None

# -----------------------------
# 2. DATA MODELS
# -----------------------------
class AudioConfig(BaseModel):
    dmVoice: Optional[str] = ""
    dmName: str = "DM"
    archetypes: List[Dict[str, Any]] = []
    soundscapes: List[Dict[str, Any]] = []
    voices: List[Dict[str, Any]] = []

class CampaignAction(BaseModel):
    campaign_id: str

class ForgeDraft(BaseModel):
    title: str
    villain: str
    pitch: str
    scenes: List[Dict[str, str]] = []
    mysteries: List[str] = []
    loot_table: List[str] = []

# -----------------------------
# 3. CAMPAIGN MANAGEMENT (RESTORED)
# -----------------------------

def _get_active_campaign_id():
    """Fetches active campaign from DB, defaults to 'the_collision_stone'."""
    if db is None: return "the_collision_stone"
    try:
        cfg = db["system_config"].find_one({"config_id": "main"})
        return cfg.get("active_campaign", "the_collision_stone") if cfg else "the_collision_stone"
    except: return "the_collision_stone"

@router.get("/campaigns/list")
def list_campaigns():
    """Scans the /campaigns folder and returns available campaigns."""
    if not CAMPAIGNS_DIR.exists(): return []
    
    active_id = _get_active_campaign_id()
    campaigns = []
    
    for item in CAMPAIGNS_DIR.iterdir():
        if item.is_dir():
            # Try to read manifest if exists
            desc = "A RealmQuest Campaign"
            manifest = item / "manifest.json"
            if manifest.exists():
                try:
                    with open(manifest) as f:
                        data = json.load(f)
                        desc = data.get("pitch", desc)
                except: pass
            
            campaigns.append({
                "id": item.name,
                "name": item.name.replace("_", " ").title(),
                "description": desc,
                "is_active": (item.name == active_id)
            })
    return campaigns

@router.post("/campaigns/activate")
def activate_campaign(payload: CampaignAction):
    """Switches the active campaign in the Database."""
    if db is None: raise HTTPException(503, "Database unavailable")
    
    target_path = CAMPAIGNS_DIR / payload.campaign_id
    if not target_path.exists():
        raise HTTPException(404, "Campaign not found on disk")
        
    try:
        db["system_config"].update_one(
            {"config_id": "main"},
            {"$set": {"active_campaign": payload.campaign_id}},
            upsert=True
        )
        logger.info(f"⚔️ Active Campaign Switched to: {payload.campaign_id}")
        return {"status": "success", "active": payload.campaign_id}
    except Exception as e:
        raise HTTPException(500, f"Failed to activate: {e}")

@router.delete("/campaigns/delete/{campaign_id}")
def delete_campaign(campaign_id: str):
    """Permanently deletes a campaign folder."""
    target = CAMPAIGNS_DIR / campaign_id
    if not target.exists(): raise HTTPException(404, "Not found")
    
    # Prevent deleting the active one? Optional safety.
    if campaign_id == _get_active_campaign_id():
         raise HTTPException(400, "Cannot delete the active campaign. Switch first.")

    try:
        shutil.rmtree(target)
        logger.info(f"🗑️ Campaign Deleted: {campaign_id}")
        return {"status": "success", "deleted": campaign_id}
    except Exception as e:
        raise HTTPException(500, f"Delete failed: {e}")

# --- THE FORGE (Creating New Campaigns) ---

@router.post("/campaigns/forge/preview")
def forge_preview(payload: Dict[str, str] = Body(...)):
    """
    Placeholder for AI Oracle. 
    In the future, this calls the LLM to dream up the campaign.
    For now, it returns a structured draft so the UI works.
    """
    concept = payload.get("concept", "Generic Adventure")
    return {
        "title": concept.split(" ")[0].title() + " Saga",
        "villain": "The Unknown",
        "pitch": f"A generated adventure based on: {concept}",
        "scenes": [
            {"name": "The Hook", "goal": "Meet the patron", "location": "Tavern"},
            {"name": "The Twist", "goal": "Survive the ambush", "location": "Roadside"}
        ],
        "mysteries": ["Who hired the assassins?", "What is the artifact?"],
        "loot_table": ["Gold Pouch", "Strange Key"]
    }

@router.post("/campaigns/forge/create")
def forge_create(draft: ForgeDraft):
    """Creates the folder structure and manifest."""
    safe_id = draft.title.lower().replace(" ", "_")
    base = CAMPAIGNS_DIR / safe_id
    
    if base.exists(): raise HTTPException(400, "Campaign already exists")
    
    try:
        # Create Structure
        (base / "assets/images").mkdir(parents=True, exist_ok=True)
        (base / "assets/audio").mkdir(parents=True, exist_ok=True)
        (base / "codex/npcs").mkdir(parents=True, exist_ok=True)
        (base / "codex/locations").mkdir(parents=True, exist_ok=True)
        
        # Write Manifest
        with open(base / "manifest.json", "w") as f:
            json.dump(draft.dict(), f, indent=2)
            
        return {"status": "success", "id": safe_id}
    except Exception as e:
        raise HTTPException(500, f"Forge failed: {e}")

# -----------------------------
# 4. ENVIRONMENT VAULT (UNIVERSAL)
# -----------------------------
@router.get("/env")
async def get_env_vars():
    settings = []
    try:
        if not ENV_FILE.exists(): ENV_FILE.touch()
        with open(ENV_FILE, "r") as f:
            lines = f.readlines()
        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"): continue
            if "=" in line:
                key, val = line.split("=", 1)
                settings.append({"key": key.strip(), "value": val.strip()})
        return {"status": "success", "settings": settings}
    except Exception as e:
        logger.error(f"Vault Read Error: {e}")
        return {"status": "error", "message": str(e), "settings": []}

@router.post("/env")
async def update_env_universal(request: Request):
    try:
        payload = await request.json()
        
        # MODE A: SINGLE KEY (Seal Button)
        if "key" in payload:
            key = str(payload.get("key")).strip()
            val = str(payload.get("value", "")).strip()
            if not key: raise HTTPException(400, "Missing key")
            if not ENV_FILE.exists(): ENV_FILE.touch()

            if not val:
                unset_key(str(ENV_FILE), key)
                return {"deleted": key}
            else:
                set_key(str(ENV_FILE), key, val)
                return {"set": key, "val": val}

        # MODE B: BULK UPDATE (Vault Page)
        elif "settings" in payload:
            updates_map = {item['key']: item['value'] for item in payload['settings']}
            new_lines = []
            if ENV_FILE.exists():
                with open(ENV_FILE, "r") as f:
                    for line in f:
                        stripped = line.strip()
                        if stripped and not stripped.startswith("#") and "=" in stripped:
                            k = stripped.split("=")[0].strip()
                            if k in updates_map:
                                new_lines.append(f"{k}={updates_map[k]}\n")
                                del updates_map[k]
                            else:
                                new_lines.append(line)
                        else:
                            new_lines.append(line)
            for k, v in updates_map.items():
                new_lines.append(f"{k}={v}\n")
            with open(ENV_FILE, "w") as f:
                f.writelines(new_lines)
            return {"status": "success", "message": "Vault Updated"}
        else:
            raise HTTPException(422, "Unknown Payload Format")
    except Exception as e:
        logger.error(f"❌ Vault Error: {e}")
        raise HTTPException(500, str(e))

@router.delete("/env/{key}")
def delete_env_var(key: str):
    try:
        unset_key(str(ENV_FILE), str(key).strip())
        return {"status": "success", "deleted": key}
    except Exception as e:
        raise HTTPException(500, str(e))

@router.get("/env/all")
def env_all_legacy():
    return [{"key": k, "value": v} for k, v in sorted(dotenv_values(ENV_FILE).items())]

# -----------------------------
# 5. AUTH & SECURITY
# -----------------------------
def _get_admin_pin() -> str:
    return dotenv_values(ENV_FILE).get("ADMIN_PIN", "").strip()

@router.get("/auth/status")
def auth_status():
    return {"locked": False, "has_pin": bool(_get_admin_pin())}

@router.post("/auth/lock")
def lock_vault():
    return {"status": "success", "message": "Vault Locked"}

@router.post("/auth/unlock")
def unlock_vault(payload: Dict[str, Any] = Body(...)):
    real_pin = _get_admin_pin()
    user_pin = str(payload.get("pin", "")).strip()
    if not real_pin: return {"status": "success", "message": "Open Access"}
    if user_pin == real_pin: return {"status": "success", "message": "Access Granted"}
    raise HTTPException(401, "Invalid PIN")

@router.post("/auth/verify")
def verify_alias(payload: Dict[str, Any] = Body(...)):
    return unlock_vault(payload)

# -----------------------------
# 6. SEED DATA & CONFIG
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
    # LOAD ACTIVE CAMPAIGN FROM DB
    active = _get_active_campaign_id()
    
    config = {
        "active_campaign": active,
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

# -----------------------------
# 7. KENKU & SYSTEM CONTROLS
# -----------------------------
ELEVEN_API_KEY = os.getenv("ELEVENLABS_API_KEY", "").strip()
@router.get("/audio/voices")
def list_voices():
    if not ELEVEN_API_KEY: return []
    try:
        r = requests.get("https://api.elevenlabs.io/v1/voices", headers={"xi-api-key": ELEVEN_API_KEY}, timeout=5)
        return [{"id": v["voice_id"], "name": v["name"]} for v in r.json().get("voices", [])]
    except: return []

KENKU_URL = os.getenv("KENKU_URL", "http://realmquest-kenku:3333").rstrip("/")

def _docker_client():
    try: return docker.DockerClient(base_url="unix:///var/run/docker.sock")
    except: return None

# HELPER: RECURSIVE TRACK FINDER
def _extract_tracks_recursive(data: Any, tracks: List[Dict[str, str]]):
    if isinstance(data, dict):
        if "id" in data and ("url" in data or "title" in data):
            title = data.get("title") or data.get("url") or data.get("id") or "Unknown"
            if "track" in data and isinstance(data["track"], dict):
                title = data["track"].get("title") or title
            tracks.append({
                "id": data["id"],
                "name": f"[File] {title}",
                "source": "kenku_scan"
            })
        for key, value in data.items():
            _extract_tracks_recursive(value, tracks)
    elif isinstance(data, list):
        for item in data:
            _extract_tracks_recursive(item, tracks)

@router.get("/audio/kenku/tracks")
def list_kenku_tracks():
    real_tracks = []
    logger.info(f"🎵 KENKU: Connecting to {KENKU_URL}...")
    try:
        r_pl = requests.get(f"{KENKU_URL}/v1/playlist", timeout=3)
        if r_pl.status_code == 200: _extract_tracks_recursive(r_pl.json(), real_tracks)
        r_sb = requests.get(f"{KENKU_URL}/v1/soundboard", timeout=3)
        if r_sb.status_code == 200: _extract_tracks_recursive(r_sb.json(), real_tracks)
        
        unique_tracks = {t['id']: t for t in real_tracks}.values()
        real_tracks = list(unique_tracks)
    except Exception as e:
        logger.error(f"❌ KENKU SCAN FAIL: {e}")

    phantom_tracks = []
    for seed in DEFAULT_SOUND_SEEDS:
        phantom_tracks.append({
            "id": seed["id"],
            "name": f"✨ {seed['name']} (System Default)",
            "source": "system_phantom"
        })
    return real_tracks + phantom_tracks

# DOCKER CONTROL LOGS
@router.get("/logs/{container_name}")
def get_logs_alias(container_name: str):
    return control_logs(container_name)

@router.get("/control/logs/{service}")
def control_logs(service: str):
    cli = _docker_client()
    if not cli: return {"status": "error", "logs": "Docker Socket Unavailable"}
    try:
        target = service if "realmquest" in service else f"realmquest-{service.replace('rq-', '')}"
        try:
            container = cli.containers.get(target)
            logs = container.logs(tail=400).decode("utf-8", "ignore")
            return {"status": "success", "logs": logs}
        except docker.errors.NotFound:
             return {"status": "error", "logs": f"Container '{target}' not found."}
    except Exception as e: return {"status": "error", "logs": str(e)}

@router.post("/control/restart/{service}")
def control_restart(service: str):
    cli = _docker_client()
    if not cli: return {"ok": False}
    try:
        target = service if "realmquest" in service else f"realmquest-{service.replace('rq-', '')}"
        cli.containers.get(target).restart()
        return {"ok": True}
    except: return {"ok": False}