# -----------------------------------------------------------------------------
# RealmQuest API - Campaign/System Manager Router
# File: api/campaign_manager.py
# Version: v18.2.6
#
# Router is included with prefix="/system" in main.py
# -----------------------------------------------------------------------------

import os
from pathlib import Path
from typing import Dict, Any, List, Optional

import requests
import docker
from dotenv import dotenv_values, set_key, unset_key
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from pymongo import MongoClient

router = APIRouter()

# -----------------------------
# Mongo
# -----------------------------
MONGO_URL = os.getenv("MONGO_URL", "mongodb://realmquest-mongo:27017/")

try:
    mongo = MongoClient(MONGO_URL, serverSelectionTimeoutMS=2000)
    db = mongo["realmquest"]
except Exception:
    db = None

# -----------------------------
# Env path resolution
# -----------------------------
def _resolve_env_path() -> str:
    # Preferred: explicit ENV_FILE_PATH (docker-compose sets this)
    candidates = [
        os.getenv("ENV_FILE_PATH"),
        os.getenv("REALMQUEST_ENV_PATH"),
        "/config/.env",
        "/opt/RealmQuest/.env",
        "/app/.env",
    ]
    for c in candidates:
        if not c:
            continue
        try:
            p = Path(c)
            # Only accept real files; bind-mounting a missing file can create a directory.
            if p.exists() and p.is_file():
                return c
        except Exception:
            # If Path() fails for any reason, just keep going
            pass
    # Fall back to the first non-empty candidate, otherwise a safe default
    for c in candidates:
        if c:
            return c
    return "/config/.env"

ENV_FILE_PATH = _resolve_env_path()

def _safe_key(k: str) -> str:
    k = (k or "").strip()
    # allow A-Z, 0-9, and underscore only
    return "".join(ch for ch in k if ch.isalnum() or ch == "_")

def _read_env() -> Dict[str, str]:
    """Read env file into a dict. Returns {} if missing or unreadable."""
    path = Path(ENV_FILE_PATH)
    if (not path.exists()) or (not path.is_file()):
        return {}
    try:
        data = dotenv_values(str(path)) or {}
    except Exception:
        return {}
    out: Dict[str, str] = {}
    for k, v in data.items():
        if not k:
            continue
        out[str(k)] = "" if v is None else str(v)
    return out


def _ensure_env_file() -> Path:
    """Ensure ENV_FILE_PATH exists as a regular file and its parent dir exists."""
    p = Path(ENV_FILE_PATH)
    p.parent.mkdir(parents=True, exist_ok=True)
    if p.exists() and not p.is_file():
        raise HTTPException(status_code=500, detail=f"ENV path is not a file: {p}")
    if not p.exists():
        p.touch()
    return p


def _get_admin_pin() -> str:
    # Prefer real process env; fall back to env file (allows updating pin without restart).
    pin = os.getenv("ADMIN_PIN", "").strip()
    if pin:
        return pin
    try:
        return str(_read_env().get("ADMIN_PIN", "")).strip()
    except Exception:
        return ""

# -----------------------------
# Audio config model
# -----------------------------
class AudioConfig(BaseModel):
    dmVoice: Optional[str] = ""
    dmName: str = "DM"
    archetypes: List[Dict[str, Any]] = []
    soundscapes: List[Dict[str, Any]] = []

def _coerce_audio_registry(raw: Any) -> Dict[str, Any]:
    # Normalize DB payload into a stable schema the UI expects
    reg = raw if isinstance(raw, dict) else {}
    dm_name = str(reg.get("dmName") or "DM")
    dm_voice = str(reg.get("dmVoice") or "")
    archetypes = reg.get("archetypes") if isinstance(reg.get("archetypes"), list) else []
    soundscapes = reg.get("soundscapes") if isinstance(reg.get("soundscapes"), list) else []

    def norm_items(items, kind: str):
        out = []
        for it in items:
            if not isinstance(it, dict):
                continue
            _id = str(it.get("id") or "").strip()
            label = str(it.get("label") or "").strip()
            if not _id:
                continue
            if not label:
                label = _id.replace("_", " ").title()
            if kind == "archetype":
                out.append({"id": _id, "label": label, "voice_id": str(it.get("voice_id") or "")})
            else:
                out.append({"id": _id, "label": label, "track_id": str(it.get("track_id") or "")})
        return out

    return {
        "config_id": "audio_registry",
        "dmName": dm_name,
        "dmVoice": dm_voice,
        "archetypes": norm_items(archetypes, "archetype"),
        "soundscapes": norm_items(soundscapes, "soundscape"),
    }

# -----------------------------
# System config endpoints
# -----------------------------
@router.get("/config")
def get_system_config():
    config: Dict[str, Any] = {
        "active_campaign": "the_collision_stone",
        "llm_provider": os.getenv("AI_PROVIDER", "Gemini-Flash"),
        "art_style": "Cinematic Fantasy",
        "audio_registry": _coerce_audio_registry({}),
    }

    if db is not None:
        audio_conf = db["system_config"].find_one({"config_id": "audio_registry"}, {"_id": 0})
        if audio_conf:
            config["audio_registry"] = _coerce_audio_registry(audio_conf)

    return config

@router.post("/audio/save")
def save_audio_config(payload: AudioConfig):
    if db is None:
        raise HTTPException(status_code=500, detail="Mongo unavailable")
    data = _coerce_audio_registry(payload.dict())
    db["system_config"].update_one(
        {"config_id": "audio_registry"},
        {"$set": data},
        upsert=True,
    )
    return {"ok": True, "saved": True, "audio_registry": data}

# -----------------------------
# Auth (PIN lock)
# -----------------------------
ADMIN_PIN = str(os.getenv("ADMIN_PIN", "")).strip()
AUTH_LOCKED = False

@router.get("/auth/status")
def auth_status():
    return {"locked": AUTH_LOCKED, "has_pin": bool(_get_admin_pin())}

@router.post("/auth/lock")
def auth_lock():
    global AUTH_LOCKED
    if _get_admin_pin():
        AUTH_LOCKED = True
    return {"ok": True, "locked": AUTH_LOCKED, "has_pin": bool(_get_admin_pin())}

@router.post("/auth/unlock")
def auth_unlock(payload: dict):
    global AUTH_LOCKED
    admin_pin = _get_admin_pin()
    if not admin_pin:
        AUTH_LOCKED = False
        return {"ok": True, "locked": False, "has_pin": False}
    pin = str((payload or {}).get("pin", "")).strip()
    if pin == admin_pin:
        AUTH_LOCKED = False
        return {"ok": True, "locked": False, "has_pin": True}
    raise HTTPException(status_code=401, detail="Invalid PIN")

# -----------------------------
# Env endpoints (Neural Config)
# -----------------------------
@router.get("/env/path")
def env_path():
    p = Path(ENV_FILE_PATH)
    return {"path": ENV_FILE_PATH, "exists": p.exists(), "size": p.stat().st_size if p.exists() else 0}

@router.get("/env/all")
def env_all():
    data = _read_env()
    return [{"key": k, "value": v} for k, v in sorted(data.items(), key=lambda kv: kv[0].lower())]

@router.get("/env/{key}")
def env_get(key: str):
    data = _read_env()
    k = _safe_key(key)
    if not k:
        raise HTTPException(status_code=400, detail="Bad key")
    return {"key": k, "value": data.get(k, "")}

@router.post("/env")
def env_set(payload: dict):
    # supports either {"key": "...", "value": "..."} or bulk {"K1":"V1","K2":"V2"}
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Bad payload")

    # Ensure the env file exists before attempting any writes.
    _ensure_env_file()

    if "key" in payload:
        key = _safe_key(str(payload.get("key", "")))
        val = "" if payload.get("value") is None else str(payload.get("value")).strip()
        if not key:
            raise HTTPException(status_code=400, detail="Missing key")
        if val == "":
            unset_key(ENV_FILE_PATH, key)
            return {"ok": True, "key": key, "deleted": True}
        set_key(ENV_FILE_PATH, key, val)
        return {"ok": True, "key": key, "value": val}

    changed = []
    for k, v in payload.items():
        key = _safe_key(str(k))
        if not key:
            continue
        val = "" if v is None else str(v).strip()
        if val == "":
            unset_key(ENV_FILE_PATH, key)
            changed.append({"key": key, "deleted": True})
        else:
            set_key(ENV_FILE_PATH, key, val)
            changed.append({"key": key, "value": val})
    return {"ok": True, "changed": changed}

# -----------------------------
# Audio sources
# -----------------------------
ELEVEN_API_KEY = os.getenv("ELEVENLABS_API_KEY", "").strip()

@router.get("/audio/voices")
def list_voices():
    if not ELEVEN_API_KEY:
        return []
    try:
        r = requests.get(
            "https://api.elevenlabs.io/v1/voices",
            headers={"xi-api-key": ELEVEN_API_KEY},
            timeout=10,
        )
        r.raise_for_status()
        data = r.json() or {}
        voices = data.get("voices") or []
        out = []
        for v in voices:
            if not isinstance(v, dict):
                continue
            out.append({"id": v.get("voice_id", ""), "name": v.get("name", "")})
        return out
    except Exception:
        return []

def _docker_client():
    try:
        return docker.DockerClient(base_url="unix:///var/run/docker.sock")
    except Exception:
        return None

KENKU_CONTAINER = os.getenv("KENKU_CONTAINER", "realmquest-kenku")

def _scan_kenku_tracks_via_docker(limit: int = 300) -> List[Dict[str, str]]:
    cli = _docker_client()
    if cli is None:
        return []
    try:
        c = cli.containers.get(KENKU_CONTAINER)
    except Exception:
        return []

    # Candidates are intentionally broad; we stop on first directory that yields results.
    scan_dirs = [
        "/root",
        "/root/Music",
        "/root/media",
        "/root/kenku",
        "/root/.local/share",
        "/data",
        "/app",
    ]

    exts = r"-iname '*.mp3' -o -iname '*.wav' -o -iname '*.ogg' -o -iname '*.m4a' -o -iname '*.flac' -o -iname '*.aac'"
    for d in scan_dirs:
        cmd = (
            "sh -lc "
            + repr(
                f"if [ -d {d} ]; then "
                f"find {d} -type f \\( {exts} \\) 2>/dev/null | sed -n '1,{limit}p'; "
                f"fi"
            )
        )
        try:
            rc, out = c.exec_run(cmd)
            if rc != 0:
                continue
            paths = [p.strip() for p in (out.decode("utf-8", "ignore") if isinstance(out, (bytes, bytearray)) else str(out)).splitlines() if p.strip()]
            if not paths:
                continue

            def label_for(p: str) -> str:
                # show last two path components when possible
                parts = [x for x in p.split("/") if x]
                if len(parts) >= 2:
                    return f"{parts[-2]}/{parts[-1]}"
                return parts[-1] if parts else p

            return [{"id": p, "name": label_for(p)} for p in paths]
        except Exception:
            continue
    return []

@router.get("/audio/kenku/tracks")
def list_kenku_tracks():
    # Prefer kenku's own HTTP API if present; otherwise scan container filesystem.
    base = os.getenv("KENKU_URL", "http://realmquest-kenku:3333").rstrip("/")
    candidates = ["/api/tracks", "/tracks", "/api/library/tracks", "/api/library", "/v1/tracks"]

    for path in candidates:
        try:
            r = requests.get(base + path, timeout=3)
            if r.status_code != 200:
                continue
            data = r.json()
            # tolerate various shapes
            if isinstance(data, list):
                tracks = data
            elif isinstance(data, dict):
                tracks = data.get("tracks") or data.get("data") or []
            else:
                tracks = []
            out = []
            for t in tracks:
                if isinstance(t, dict):
                    tid = t.get("id") or t.get("track_id") or t.get("path") or t.get("url")
                    name = t.get("name") or t.get("title") or t.get("filename") or tid
                    if tid:
                        out.append({"id": str(tid), "name": str(name)})
                elif isinstance(t, str):
                    out.append({"id": t, "name": t})
            if out:
                return out
        except Exception:
            pass

    return _scan_kenku_tracks_via_docker()

# -----------------------------
# Docker control endpoints
# -----------------------------
SERVICE_TO_CONTAINER = {
    "rq-bot": "realmquest-bot",
    "rq-api": "realmquest-api",
    "rq-portal": "realmquest-portal",
    "rq-scribe": "realmquest-scribe",
    "rq-kenku": "realmquest-kenku",
    "rq-mongo": "realmquest-mongo",
    "rq-redis": "realmquest-redis",
    "rq-chroma": "realmquest-chroma",
}

@router.get("/control/logs/{service}")
def control_logs(service: str):
    name = SERVICE_TO_CONTAINER.get(service, service)
    cli = _docker_client()
    if cli is None:
        raise HTTPException(status_code=500, detail="Docker unavailable")
    try:
        c = cli.containers.get(name)
        txt = c.logs(tail=400).decode("utf-8", "ignore")
        return txt
    except docker.errors.NotFound:
        raise HTTPException(status_code=404, detail=f"Container not found: {name}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/control/restart/{service}")
def control_restart(service: str):
    name = SERVICE_TO_CONTAINER.get(service, service)
    cli = _docker_client()
    if cli is None:
        raise HTTPException(status_code=500, detail="Docker unavailable")
    try:
        c = cli.containers.get(name)
        c.restart()
        return {"ok": True, "service": service, "container": name}
    except docker.errors.NotFound:
        raise HTTPException(status_code=404, detail=f"Container not found: {name}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
