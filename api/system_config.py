#===============================================================
#Script Name: system_config.py
#Script Location: /opt/RealmQuest/api/system_config.py
#Date: 01/31/2026
#Created By: T03KNEE
#Github: https://github.com/To3Knee/RealmQuest
#Version: 1.0.0
#About: Canonical active-campaign source of truth helpers to prevent split-brain across API modules.
#===============================================================

from __future__ import annotations

from typing import Any, Dict, Optional


DEFAULT_CAMPAIGN = "the_collision_stone"


def _get_cfg(db, config_id: str) -> Optional[Dict[str, Any]]:
    if db is None:
        return None
    try:
        return db["system_config"].find_one({"config_id": config_id}, {"_id": 0})
    except Exception:
        return None


def _set_cfg(db, config_id: str, payload: Dict[str, Any]) -> None:
    if db is None:
        return
    try:
        db["system_config"].update_one({"config_id": config_id}, {"$set": payload}, upsert=True)
    except Exception:
        return


def get_active_campaign_id(db, default: str = DEFAULT_CAMPAIGN) -> str:
    """Return the canonical active campaign id.

    Canonical location: system_config: {config_id: "main"}.active_campaign

    Backwards-compatible migration:
      - If main has no active_campaign, check legacy docs:
        - config_id: "system"
        - config_id: "audio_registry"
      - If found in legacy, persist into main to converge state.
    """
    # 1) Canonical
    main = _get_cfg(db, "main")
    if main and main.get("active_campaign"):
        val = str(main["active_campaign"]).strip()
        return val or default

    # 2) Legacy fallbacks (migration)
    for legacy_id in ("system", "audio_registry"):
        legacy = _get_cfg(db, legacy_id)
        if legacy and legacy.get("active_campaign"):
            val = str(legacy["active_campaign"]).strip()
            if val:
                _set_cfg(db, "main", {"active_campaign": val})
                return val

    return default


def set_active_campaign_id(db, campaign_id: str) -> str:
    """Set active campaign id in canonical doc and mirror to legacy docs for safety."""
    cid = str(campaign_id or "").strip() or DEFAULT_CAMPAIGN

    # Canonical
    _set_cfg(db, "main", {"active_campaign": cid})

    # Mirror (keeps older code paths safe even if any remain)
    _set_cfg(db, "system", {"active_campaign": cid})
    _set_cfg(db, "audio_registry", {"active_campaign": cid})

    return cid
