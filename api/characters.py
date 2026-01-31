# ===============================================================
# Script Name: characters.py
# Script Location: /opt/RealmQuest/api/characters.py
# Date: 2026-01-31
# Version: 1.2.0 (GET endpoint + safe deep-merge PUT + response consistency)
# ===============================================================

import os
import uuid
import json
import re
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, UploadFile, File, Query
from pydantic import BaseModel, Field

try:
    from pymongo import MongoClient
except Exception:
    MongoClient = None

router = APIRouter(tags=["characters"])


def _utc_now_iso() -> str:
    # keep it simple + stable; ISO string is sufficient for sorting
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def _get_db():
    if MongoClient is None:
        return None
    uri = os.getenv("MONGO_URL") or os.getenv("RQ_MONGO_URI") or ""
    if not uri:
        return None
    try:
        client = MongoClient(uri)
        db_name = os.getenv("RQ_MONGO_DB", "realmquest")
        return client[db_name]
    except Exception:
        return None


def _get_active_campaign_id(db) -> str:
    """Mirror of campaign_manager._get_active_campaign_id(), kept local to avoid import loops."""
    if db is None:
        return os.getenv("RQ_DEFAULT_CAMPAIGN", "the_collision_stone")
    try:
        cfg = db["system_config"].find_one({"config_id": "system"}, {"_id": 0})
        if cfg and cfg.get("active_campaign"):
            return str(cfg["active_campaign"])
    except Exception:
        pass
    return os.getenv("RQ_DEFAULT_CAMPAIGN", "the_collision_stone")


def _campaign_root(active_campaign: str) -> str:
    return f"/campaigns/{active_campaign}"


def _avatar_dir(active_campaign: str) -> str:
    return f"{_campaign_root(active_campaign)}/assets/avatars"


def _safe_slug(s: str) -> str:
    s = (s or "").strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s or "hero"


def _deep_merge(base: Any, incoming: Any) -> Any:
    """Recursively merge dicts. Incoming overwrites base for non-dicts/lists."""
    if isinstance(base, dict) and isinstance(incoming, dict):
        out = dict(base)
        for k, v in incoming.items():
            if k in out and isinstance(out[k], dict) and isinstance(v, dict):
                out[k] = _deep_merge(out[k], v)
            else:
                out[k] = v
        return out
    return incoming


class CharacterRecord(BaseModel):
    character_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    campaign_id: Optional[str] = None

    # Identity
    name: str = ""
    class_name: str = ""
    race: str = ""
    level: int = 1

    # Player linking
    owner_discord_id: Optional[str] = None
    owner_display_name: Optional[str] = None

    # Presentation
    avatar_url: Optional[str] = None  # served from /campaigns/<campaign>/assets/avatars/<file>

    # Sheet payload (keep flexible)
    sheet: Dict[str, Any] = Field(default_factory=dict)

    # Timestamps
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


@router.get("/characters")
def list_characters(
    owner_discord_id: Optional[str] = Query(default=None),
    campaign_id: Optional[str] = Query(default=None),
    limit: int = Query(default=200, ge=1, le=1000),
):
    db = _get_db()
    if db is None:
        # No DB: return empty (keeps portal functional without crashing)
        return []

    active_campaign = campaign_id or _get_active_campaign_id(db)

    q: Dict[str, Any] = {"campaign_id": active_campaign}
    if owner_discord_id:
        q["owner_discord_id"] = owner_discord_id

    docs = list(
        db["characters"].find(q, {"_id": 0}).sort("updated_at", -1).limit(limit)
    )
    return docs


@router.get("/characters/{character_id}")
def get_character(character_id: str):
    db = _get_db()
    if db is None:
        raise HTTPException(status_code=500, detail="Mongo unavailable")

    doc = db["characters"].find_one({"character_id": character_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Character not found")
    return {"ok": True, "character": doc}


@router.get("/characters/template")
def character_template():
    """A clean, manually-fillable template players can download and edit."""
    template = CharacterRecord(
        character_id="TEMPLATE",
        name="Your Character Name",
        class_name="Fighter",
        race="Human",
        level=1,
        owner_discord_id="DISCORD_USER_ID_HERE",
        owner_display_name="DiscordDisplayName",
        sheet={
            "abilities": {
                "str": 10,
                "dex": 10,
                "con": 10,
                "int": 10,
                "wis": 10,
                "cha": 10,
            },
            "bio": {
                "backstory": "",
                "traits": "",
                "ideals": "",
                "bonds": "",
                "flaws": "",
            },
            "combat": {
                "ac": 10,
                "initiative": 0,
                "speed": 30,
                "hp": {"max": 10, "current": 10, "temp": 0},
                "hit_dice": "1d10",
            },
            "inventory": {"coins": {"pp": 0, "gp": 0, "ep": 0, "sp": 0, "cp": 0}, "items": []},
            "notes": {"misc": ""},
        },
    )
    return template.dict()


@router.post("/characters")
def create_character(payload: CharacterRecord):
    db = _get_db()
    if db is None:
        raise HTTPException(status_code=500, detail="Mongo unavailable")

    active_campaign = _get_active_campaign_id(db)

    data = payload.dict()
    if not data.get("character_id") or data.get("character_id") == "TEMPLATE":
        data["character_id"] = str(uuid.uuid4())

    data["campaign_id"] = data.get("campaign_id") or active_campaign
    data["created_at"] = _utc_now_iso()
    data["updated_at"] = _utc_now_iso()

    # Normalize a few fields
    data["name"] = (data.get("name") or "").strip()
    data["class_name"] = (data.get("class_name") or "").strip()
    data["race"] = (data.get("race") or "").strip()

    db["characters"].update_one(
        {"character_id": data["character_id"]},
        {"$set": data},
        upsert=True,
    )

    return {"ok": True, "character": data}


@router.put("/characters/{character_id}")
def update_character(character_id: str, payload: CharacterRecord):
    db = _get_db()
    if db is None:
        raise HTTPException(status_code=500, detail="Mongo unavailable")

    campaign_id = payload.campaign_id or _get_active_campaign_id(db)

    # Pydantic models will include defaults for missing fields; we only want to
    # apply what the client actually sent where possible.
    incoming = payload.dict(exclude_unset=True)

    existing: Dict[str, Any] = db["characters"].find_one({"character_id": character_id}, {"_id": 0}) or {}
    merged = _deep_merge(existing, incoming)

    # Force identity + campaign and timestamps
    merged["character_id"] = character_id
    merged["campaign_id"] = merged.get("campaign_id") or campaign_id

    now = _utc_now_iso()
    merged["created_at"] = merged.get("created_at") or existing.get("created_at") or now
    merged["updated_at"] = now

    db["characters"].update_one({"character_id": character_id}, {"$set": merged}, upsert=True)
    return {"ok": True, "character": merged}


@router.delete("/characters/{character_id}")
def delete_character(character_id: str):
    db = _get_db()
    if db is None:
        raise HTTPException(status_code=500, detail="Mongo unavailable")

    # remove avatar file if present
    doc = db["characters"].find_one({"character_id": character_id}, {"_id": 0}) or {}
    avatar_url = doc.get("avatar_url")

    db["characters"].delete_one({"character_id": character_id})

    if avatar_url:
        # avatar_url is like /campaigns/<campaign>/assets/avatars/<file>
        try:
            path = avatar_url
            if path.startswith("/"):
                path = path[1:]
            # inside container, campaign root is /campaigns/<campaign>/...
            abs_path = "/" + path
            if abs_path.startswith("/campaigns/") and os.path.exists(abs_path):
                os.remove(abs_path)
        except Exception:
            pass

    return {"ok": True, "deleted": True, "character_id": character_id}


@router.get("/characters/{character_id}/export")
def export_character(character_id: str):
    db = _get_db()
    if db is None:
        raise HTTPException(status_code=500, detail="Mongo unavailable")

    doc = db["characters"].find_one({"character_id": character_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Character not found")
    return doc


@router.post("/characters/import")
def import_character(payload: Dict[str, Any]):
    """Import a character JSON created from the template or exported."""
    db = _get_db()
    if db is None:
        raise HTTPException(status_code=500, detail="Mongo unavailable")

    active_campaign = _get_active_campaign_id(db)

    data = dict(payload or {})
    if not data.get("character_id") or data.get("character_id") in ("TEMPLATE", ""):
        data["character_id"] = str(uuid.uuid4())

    data["campaign_id"] = data.get("campaign_id") or active_campaign
    now = _utc_now_iso()
    data["created_at"] = data.get("created_at") or now
    data["updated_at"] = now

    db["characters"].update_one({"character_id": data["character_id"]}, {"$set": data}, upsert=True)
    return {"ok": True, "character": data}


@router.post("/characters/{character_id}/avatar")
async def upload_avatar(character_id: str, file: UploadFile = File(...)):
    db = _get_db()
    if db is None:
        raise HTTPException(status_code=500, detail="Mongo unavailable")

    doc = db["characters"].find_one({"character_id": character_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Character not found")

    campaign = doc.get("campaign_id") or _get_active_campaign_id(db)
    os.makedirs(_avatar_dir(campaign), exist_ok=True)

    # sanitize extension
    filename = file.filename or "avatar.png"
    ext = os.path.splitext(filename)[1].lower()
    if ext not in (".png", ".jpg", ".jpeg", ".webp"):
        ext = ".png"

    base = _safe_slug(doc.get("name") or character_id)
    out_name = f"{base}-{character_id[:8]}{ext}"
    out_path = f"{_avatar_dir(campaign)}/{out_name}"

    data = await file.read()
    try:
        with open(out_path, "wb") as f:
            f.write(data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to write avatar: {e}")

    avatar_url = f"{_campaign_root(campaign)}/assets/avatars/{out_name}"
    db["characters"].update_one({"character_id": character_id}, {"$set": {"avatar_url": avatar_url, "updated_at": _utc_now_iso()}})

    return {"ok": True, "avatar_url": avatar_url}
