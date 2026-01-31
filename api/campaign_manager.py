#===============================================================
#Script Name: campaign_manager.py
#Script Location: /opt/RealmQuest/api/campaign_manager.py
#Date: 01/31/2026
#Created By: T03KNEE
#Github: https://github.com/To3Knee/RealmQuest
#Version: 19.13.1
#About: Phase 3.7 Hotfix - Import missing FastAPI symbols (Query/File/UploadFile) for delete/replace routes.
#===============================================================

import os
import shutil
import logging
import requests
import docker
import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from dotenv import dotenv_values, set_key, unset_key
from fastapi import APIRouter, HTTPException, Body, Request, Query, UploadFile, File
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
# 3B. CODEX + GALLERY BRIDGE (API)
# -----------------------------
# These endpoints unify campaign filesystem content into simple JSON payloads
# for the Portal. They are read-only and do not mutate campaigns.
#
# Codex Bridge:
#   - Lists /codex/npcs/*.json for the active campaign
#   - Attempts to resolve a portrait image by basename or best-match
#   - Returns dossiers + resolved portrait URLs
#
# Gallery Bridge:
#   - Lists /assets/images/* for the active campaign
#   - Returns URLs + basic metadata for the Portal gallery

_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp"}

def _active_campaign_dir() -> Path:
    camp_id = _get_active_campaign_id()
    return (CAMPAIGNS_DIR / camp_id)

def _safe_read_json(path: Path) -> Optional[Dict[str, Any]]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

def _norm_key(s: str) -> str:
    # Normalize names for matching: lower, alnum only.
    return "".join([c for c in (s or "").lower() if c.isalnum()])

def _collect_images(*dirs: Path) -> List[Path]:
    out: List[Path] = []
    for d in dirs:
        try:
            if d.exists() and d.is_dir():
                for p in d.iterdir():
                    if p.is_file() and p.suffix.lower() in _IMAGE_EXTS:
                        out.append(p)
        except Exception:
            continue
    return out

def _best_match_image(stem: str, images: List[Path]) -> Optional[Path]:
    """Resolve portrait via basename + fuzzy matching."""
    import difflib

    target = _norm_key(stem)
    if not target:
        return None

    norm_map: Dict[str, Path] = {}
    for p in images:
        nk = _norm_key(p.stem)
        if nk and nk not in norm_map:
            norm_map[nk] = p

    if target in norm_map:
        return norm_map[target]

    candidates = list(norm_map.keys())
    close = difflib.get_close_matches(target, candidates, n=1, cutoff=0.78)
    if close:
        return norm_map.get(close[0])

    for nk, p in norm_map.items():
        if target in nk or nk in target:
            return p

    return None


def _resolve_image_from_dossier(dossier: Optional[Dict[str, Any]], base: Path, camp_id: str) -> Optional[Dict[str, Any]]:
    """Prefer explicit dossier image field when present (supports legacy layouts)."""
    if not isinstance(dossier, dict):
        return None
    img = dossier.get("image") or dossier.get("portrait") or dossier.get("portrait_path")
    if not img:
        return None
    try:
        fname = Path(str(img)).name
        if not fname:
            return None
        # Check codex/npcs first (preferred), then assets/images
        codex = base / "codex" / "npcs" / fname
        assets = base / "assets" / "images" / fname

        if codex.exists():
            return {"filename": fname, "url": f"/campaigns/{camp_id}/codex/npcs/{fname}", "source_dir": "codex/npcs"}
        if assets.exists():
            return {"filename": fname, "url": f"/campaigns/{camp_id}/assets/images/{fname}", "source_dir": "assets/images"}
    except Exception:
        return None
    return None

def _load_gallery_index(assets_dir: Path) -> List[Dict[str, Any]]:
    """Load campaign gallery index (assets/images/gallery.json)."""
    idx = assets_dir / "gallery.json"
    if not idx.exists():
        return []
    try:
        with open(idx, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return [x for x in data if isinstance(x, dict)]
        if isinstance(data, dict) and isinstance(data.get("items"), list):
            return [x for x in data.get("items") if isinstance(x, dict)]
    except Exception:
        return []
    return []

def _save_gallery_index(assets_dir: Path, items: List[Dict[str, Any]]) -> None:
    """Persist gallery index to assets/images/gallery.json (list format)."""
    assets_dir.mkdir(parents=True, exist_ok=True)
    idx = assets_dir / "gallery.json"
    tmp = assets_dir / ".gallery.json.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(items, f, indent=2, ensure_ascii=False)
        f.write("\n")
    tmp.replace(idx)


def _scan_npc_image_references(codex_dir: Path, filename: str) -> List[str]:
    """Return list of NPC json filenames that reference a given image filename."""
    refs: List[str] = []
    if not codex_dir.exists():
        return refs
    target = filename.strip()
    if not target:
        return refs
    for p in sorted(codex_dir.glob("*.json")):
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                continue
            img = str(data.get("image") or data.get("portrait") or data.get("avatar") or "").strip()
            if not img:
                continue
            # Match by exact filename or by suffix path segment
            if img == target or img.endswith("/" + target) or img.endswith("\\" + target):
                refs.append(p.name)
        except Exception:
            continue
    return refs


def _safe_unlink(path: Path) -> bool:
    """Attempt to unlink a file; returns True if removed."""
    try:
        if path.exists() and path.is_file():
            path.unlink()
            return True
    except Exception:
        return False
    return False

def _gallery_meta_map(assets_dir: Path) -> Dict[str, Dict[str, Any]]:
    """Map filename -> metadata from gallery.json."""
    out: Dict[str, Dict[str, Any]] = {}
    for entry in _load_gallery_index(assets_dir):
        fn = str(entry.get("filename") or entry.get("file") or "").strip()
        if fn:
            out[fn] = entry
    return out

@router.get("/campaigns/codex/npcs")
def codex_npcs(include_dossier: bool = True):
    """Return NPC dossiers for the active campaign with resolved portrait URLs."""
    camp_id = _get_active_campaign_id()
    base = _active_campaign_dir()
    codex_dir = base / "codex" / "npcs"
    assets_dir = base / "assets" / "images"

    if not codex_dir.exists():
        return {"campaign": camp_id, "items": []}

    images = _collect_images(codex_dir, assets_dir)

    items: List[Dict[str, Any]] = []
    for jf in sorted(codex_dir.glob("*.json")):
        stem = jf.stem
        dossier = _safe_read_json(jf) if include_dossier else None

        display_name = None
        if isinstance(dossier, dict):
            display_name = dossier.get("name") or dossier.get("npc_name") or dossier.get("title")

        if not display_name:
            display_name = stem.replace("_", " ").replace("-", " ").title()

        # Prefer explicit dossier image field when present (supports legacy JSON: "image": "assets/images/<file>.png")
        portrait_obj = _resolve_image_from_dossier(dossier, base, camp_id)

        # Otherwise attempt basename/fuzzy match across codex + assets
        if portrait_obj is None:
            portrait_path = _best_match_image(stem, images)
            if portrait_path:
                try:
                    source_dir = "assets/images" if "assets/images" in str(portrait_path) else "codex/npcs"
                    if source_dir == "assets/images":
                        url = f"/campaigns/{camp_id}/assets/images/{portrait_path.name}"
                    else:
                        url = f"/campaigns/{camp_id}/codex/npcs/{portrait_path.name}"
                    portrait_obj = {"filename": portrait_path.name, "url": url, "source_dir": source_dir}
                except Exception:
                    portrait_obj = None

        items.append({
            "id": stem,
            "name": display_name,
            "json_filename": jf.name,
            "json_url": f"/campaigns/{camp_id}/codex/npcs/{jf.name}",
            "portrait": portrait_obj,
            "dossier": dossier if include_dossier else None
        })

    return {"campaign": camp_id, "items": items}


@router.delete("/campaigns/gallery/images/{filename}")
def campaign_gallery_delete_image(filename: str, force: bool = Query(False, description="Delete even if referenced by NPC dossiers")):
    """Delete a gallery image from assets/images and update gallery.json."

    Safety:
      - If the image is referenced by one or more NPC dossiers, this returns HTTP 409 unless force=true.
    """
    camp_id = _get_active_campaign_id()
    base = _active_campaign_dir()
    assets_dir = base / "assets" / "images"
    codex_dir = base / "codex" / "npcs"

    filename = (filename or "").strip()
    if not filename:
        raise HTTPException(status_code=400, detail="filename required")

    # Prevent directory traversal
    if "/" in filename or "\\" in filename or filename.startswith("."):
        raise HTTPException(status_code=400, detail="invalid filename")

    refs = _scan_npc_image_references(codex_dir, filename)
    if refs and not force:
        raise HTTPException(status_code=409, detail={"reason": "referenced_by_npcs", "refs": refs})

    img_path = assets_dir / filename
    removed = _safe_unlink(img_path)

    # Update gallery.json by removing entries with this filename
    idx_items = _load_gallery_index(assets_dir)
    idx_items = [x for x in idx_items if str(x.get("filename") or x.get("file") or "").strip() != filename]
    _save_gallery_index(assets_dir, idx_items)

    return {"campaign": camp_id, "filename": filename, "deleted": bool(removed), "referenced_by": refs}


@router.post("/campaigns/gallery/images/{filename}/replace")
async def campaign_gallery_replace_image(filename: str, file: UploadFile = File(...)):
    """Replace the bytes for a gallery image (keeps filename + URL stable) and refresh gallery.json metadata."""
    camp_id = _get_active_campaign_id()
    base = _active_campaign_dir()
    assets_dir = base / "assets" / "images"

    filename = (filename or "").strip()
    if not filename:
        raise HTTPException(status_code=400, detail="filename required")
    if "/" in filename or "\\" in filename or filename.startswith("."):
        raise HTTPException(status_code=400, detail="invalid filename")

    assets_dir.mkdir(parents=True, exist_ok=True)
    dst = assets_dir / filename

    # Basic extension sanity
    ext = Path(filename).suffix.lower()
    if ext not in [".png", ".jpg", ".jpeg", ".webp"]:
        raise HTTPException(status_code=400, detail="only png/jpg/jpeg/webp allowed")

    try:
        content = await file.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"failed to read upload: {e}")

    if not content:
        raise HTTPException(status_code=400, detail="empty upload")

    tmp = assets_dir / f".{filename}.upload.tmp"
    try:
        with open(tmp, "wb") as f:
            f.write(content)
        tmp.replace(dst)
    finally:
        try:
            if tmp.exists():
                tmp.unlink()
        except Exception:
            pass

    stat = dst.stat()
    meta_map = _gallery_meta_map(assets_dir)
    entry = meta_map.get(filename, {})
    # preserve existing fields, but refresh size + modified time
    entry = dict(entry) if isinstance(entry, dict) else {}
    entry["filename"] = filename
    entry["bytes"] = stat.st_size
    entry["modified_epoch"] = int(stat.st_mtime)
    entry.setdefault("meta", {})
    if isinstance(entry.get("meta"), dict):
        entry["meta"]["updated_at"] = time.time()
        entry["meta"]["updated_at_epoch"] = int(time.time())

    # Write back into gallery.json list (upsert)
    idx_items = _load_gallery_index(assets_dir)
    wrote = False
    for i, it in enumerate(idx_items):
        fn = str(it.get("filename") or it.get("file") or "").strip()
        if fn == filename:
            idx_items[i] = entry
            wrote = True
            break
    if not wrote:
        idx_items.insert(0, entry)
    _save_gallery_index(assets_dir, idx_items)

    return {"campaign": camp_id, "item": _build_gallery_item(assets_dir, filename, meta_map={filename: entry})}


@router.delete("/campaigns/codex/npcs/{npc_id}")
def codex_delete_npc(npc_id: str, delete_portrait: bool = Query(True, description="Also delete the portrait image referenced by the dossier, if present")):
    """Delete an NPC dossier JSON and optionally its portrait image."""
    camp_id = _get_active_campaign_id()
    base = _active_campaign_dir()
    codex_dir = base / "codex" / "npcs"
    assets_dir = base / "assets" / "images"

    npc_id = (npc_id or "").strip()
    if not npc_id:
        raise HTTPException(status_code=400, detail="npc_id required")
    # prevent traversal
    if "/" in npc_id or "\\" in npc_id or npc_id.startswith("."):
        raise HTTPException(status_code=400, detail="invalid npc_id")

    json_path = codex_dir / f"{npc_id}.json"
    if not json_path.exists():
        # try the legacy naming if caller provided filename-like id
        alt = codex_dir / npc_id
        if alt.exists() and alt.suffix.lower() == ".json":
            json_path = alt
        else:
            raise HTTPException(status_code=404, detail="npc dossier not found")

    portrait_deleted = False
    portrait_target = None

    if delete_portrait:
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                img = str(data.get("image") or data.get("portrait") or data.get("avatar") or "").strip()
                if img:
                    portrait_target = img
        except Exception:
            portrait_target = None

        # Resolve portrait path within campaign dir only
        if portrait_target:
            # normalize and strip leading slash
            p = portrait_target.lstrip("/").replace("\\", "/")
            # only allow within these roots
            candidates = [
                base / p,
                assets_dir / Path(p).name,           # if only filename
                codex_dir / Path(p).name,            # if portrait stored in codex dir
            ]
            for cand in candidates:
                try:
                    cand = cand.resolve()
                except Exception:
                    continue
                # Ensure candidate is under campaign base
                try:
                    if not str(cand).startswith(str(base.resolve())):
                        continue
                except Exception:
                    continue
                if cand.exists() and cand.is_file():
                    portrait_deleted = _safe_unlink(cand)
                    # If it was an assets/images file, also remove from gallery.json
                    if portrait_deleted and str(cand).startswith(str(assets_dir.resolve())):
                        fn = cand.name
                        idx_items = _load_gallery_index(assets_dir)
                        idx_items = [x for x in idx_items if str(x.get("filename") or x.get("file") or "").strip() != fn]
                        _save_gallery_index(assets_dir, idx_items)
                    break

    dossier_deleted = _safe_unlink(json_path)

    return {
        "campaign": camp_id,
        "npc_id": npc_id,
        "dossier_deleted": bool(dossier_deleted),
        "portrait_deleted": bool(portrait_deleted),
        "portrait_target": portrait_target,
    }


@router.post("/campaigns/codex/npcs/{npc_id}/portrait")
async def codex_replace_portrait(npc_id: str, file: UploadFile = File(...)):
    """Upload/replace an NPC portrait and update the dossier's image field.

    This writes the portrait into /codex/npcs/ as <npc_id>.<ext> (stable and NPC-scoped).
    """
    camp_id = _get_active_campaign_id()
    base = _active_campaign_dir()
    codex_dir = base / "codex" / "npcs"
    npc_id = (npc_id or "").strip()
    if not npc_id:
        raise HTTPException(status_code=400, detail="npc_id required")
    if "/" in npc_id or "\\" in npc_id or npc_id.startswith("."):
        raise HTTPException(status_code=400, detail="invalid npc_id")

    json_path = codex_dir / f"{npc_id}.json"
    if not json_path.exists():
        alt = codex_dir / npc_id
        if alt.exists() and alt.suffix.lower() == ".json":
            json_path = alt
            npc_id = alt.stem
        else:
            raise HTTPException(status_code=404, detail="npc dossier not found")

    try:
        content = await file.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"failed to read upload: {e}")
    if not content:
        raise HTTPException(status_code=400, detail="empty upload")

    # extension based on upload filename
    up_name = (file.filename or "").strip()
    ext = Path(up_name).suffix.lower() if up_name else ".png"
    if ext not in [".png", ".jpg", ".jpeg", ".webp"]:
        raise HTTPException(status_code=400, detail="only png/jpg/jpeg/webp allowed")

    codex_dir.mkdir(parents=True, exist_ok=True)

    # Remove any existing portrait with known extensions (npc scoped)
    for old_ext in [".png", ".jpg", ".jpeg", ".webp"]:
        old = codex_dir / f"{npc_id}{old_ext}"
        if old.exists() and old.is_file() and old_ext != ext:
            _safe_unlink(old)

    dst = codex_dir / f"{npc_id}{ext}"
    tmp = codex_dir / f".{npc_id}{ext}.upload.tmp"
    try:
        with open(tmp, "wb") as f:
            f.write(content)
        tmp.replace(dst)
    finally:
        try:
            if tmp.exists():
                tmp.unlink()
        except Exception:
            pass

    # Update dossier image field to point to codex location
    updated = None
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            data = {}
        data["image"] = f"codex/npcs/{dst.name}"
        data["updated_at"] = time.time()
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write("\n")
        updated = data
    except Exception:
        updated = None

    # Return refreshed codex item
    item = {
        "id": npc_id,
        "name": (updated or {}).get("name") or npc_id.replace("_", " ").strip().title(),
        "json_filename": json_path.name,
        "json_url": f"/campaigns/{camp_id}/codex/npcs/{json_path.name}",
        "portrait": {"filename": dst.name, "url": f"/campaigns/{camp_id}/codex/npcs/{dst.name}", "source_dir": "codex/npcs"},
        "dossier": updated,
    }
    return {"campaign": camp_id, "item": item}

@router.post("/campaigns/codex/npcs/migrate-portraits")
def migrate_npc_portraits(dry_run: bool = True, overwrite: bool = False):
    """One-time helper: move legacy NPC portraits from assets/images into codex/npcs and update dossiers."""
    camp_id = _get_active_campaign_id()
    base = _active_campaign_dir()
    codex_dir = base / "codex" / "npcs"
    assets_dir = base / "assets" / "images"

    if not codex_dir.exists():
        return {"campaign": camp_id, "dry_run": dry_run, "migrated": [], "skipped": ["codex/npcs missing"]}

    migrated: List[Dict[str, Any]] = []
    skipped: List[Dict[str, Any]] = []

    for jf in sorted(codex_dir.glob("*.json")):
        dossier = _safe_read_json(jf)
        if not isinstance(dossier, dict):
            skipped.append({"npc": jf.name, "reason": "invalid json"})
            continue

        img = str(dossier.get("image") or "").strip()
        if not img:
            skipped.append({"npc": jf.name, "reason": "no image field"})
            continue

        src_name = Path(img).name
        src = assets_dir / src_name
        if not src.exists():
            skipped.append({"npc": jf.name, "reason": "source not in assets/images"})
            continue

        dest = codex_dir / f"{jf.stem}{src.suffix.lower()}"
        if dest.exists() and not overwrite:
            skipped.append({"npc": jf.name, "reason": "dest exists", "dest": dest.name})
            continue

        action = {"npc": jf.stem, "from": f"assets/images/{src_name}", "to": f"codex/npcs/{dest.name}"}

        if not dry_run:
            try:
                shutil.move(str(src), str(dest))
                dossier["image"] = f"codex/npcs/{dest.name}"
                with open(jf, "w", encoding="utf-8") as f:
                    json.dump(dossier, f, indent=2, ensure_ascii=False)
            except Exception as e:
                skipped.append({"npc": jf.name, "reason": f"move failed: {e}"})
                continue

        migrated.append(action)

    return {"campaign": camp_id, "dry_run": dry_run, "migrated": migrated, "skipped": skipped}



@router.get("/campaigns/gallery/images")
def gallery_images(limit: int = 250):
    """Return image gallery metadata for the active campaign from /assets/images."""
    camp_id = _get_active_campaign_id()
    base = _active_campaign_dir()
    assets_dir = base / "assets" / "images"

    meta_map = _gallery_meta_map(assets_dir)

    if not assets_dir.exists():
        return {"campaign": camp_id, "items": []}

    items: List[Dict[str, Any]] = []
    try:
        for p in assets_dir.iterdir():
            if not p.is_file():
                continue
            if p.suffix.lower() not in _IMAGE_EXTS:
                continue
            st = p.stat()
            meta = meta_map.get(p.name) if isinstance(meta_map, dict) else None
            item = {
                "filename": p.name,
                "url": f"/campaigns/{camp_id}/assets/images/{p.name}",
                "bytes": int(st.st_size),
                "modified_epoch": int(st.st_mtime),
            }
            if isinstance(meta, dict):
                # Keep this flat for the Portal
                for k in ["kind", "prompt", "title", "created_at", "created_at_epoch", "created_by", "source", "npc_id", "tags", "context"]:
                    if k in meta and meta.get(k) is not None:
                        item[k] = meta.get(k)
            items.append(item)
    except Exception as e:
        logger.error(f"Gallery scan error: {e}")
        return {"campaign": camp_id, "items": []}

    items.sort(key=lambda x: x.get("modified_epoch", 0), reverse=True)

    if limit and limit > 0:
        items = items[: min(int(limit), 2000)]

    return {"campaign": camp_id, "items": items}

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

# Global vault lock state (process-local). When a PIN exists, we start locked.
_VAULT_LOCKED = True

@router.get("/auth/status")
def auth_status():
    """Return lock status and whether a PIN is configured."""
    global _VAULT_LOCKED
    has_pin = bool(_get_admin_pin())
    if not has_pin:
        # No PIN configured -> nothing is protected.
        _VAULT_LOCKED = False
        return {"locked": False, "has_pin": False}
    return {"locked": bool(_VAULT_LOCKED), "has_pin": True}

@router.post("/auth/lock")
def lock_vault():
    """Lock the vault (global across the API process)."""
    global _VAULT_LOCKED
    if not _get_admin_pin():
        _VAULT_LOCKED = False
        return {"ok": True, "locked": False}
    _VAULT_LOCKED = True
    return {"ok": True, "locked": True}

@router.post("/auth/unlock")
def unlock_vault(payload: Dict[str, Any] = Body(...)):
    """Unlock the vault (global across the API process)."""
    global _VAULT_LOCKED
    real_pin = _get_admin_pin()
    user_pin = str(payload.get("pin", "")).strip()

    if not real_pin:
        # No PIN configured -> always unlocked.
        _VAULT_LOCKED = False
        return {"status": "success", "message": "Open Access", "locked": False}

    if user_pin == real_pin:
        _VAULT_LOCKED = False
        return {"status": "success", "message": "Access Granted", "locked": False}

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
