#===============================================================
#Script Name: rolls.py
#Script Location: /opt/RealmQuest/api/rolls.py
#Date: 01/31/2026
#Created By: T03KNEE
#Github: https://github.com/To3Knee/RealmQuest
#Version: 1.0.1
#About: Canonical roll event endpoints for bot-aware dice and shared player roll feed (no UI drift required).
#===============================================================

import os
import re
import time
import uuid
import secrets
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from pymongo import MongoClient

from system_config import get_active_campaign_id


router = APIRouter()

try:
    mongo = MongoClient(os.getenv("MONGO_URL", "mongodb://realmquest-mongo:27017/"), serverSelectionTimeoutMS=2000)
    db = mongo["realmquest"]
except Exception:
    db = None


class RollCreate(BaseModel):
    # Identity
    campaign_id: Optional[str] = None
    character_id: Optional[str] = None
    character_name: Optional[str] = None
    owner_discord_id: Optional[str] = None
    player_name: Optional[str] = None

    # Core dice data (either provide dice_count+sides or provide notation)
    dice_count: int = Field(default=1, ge=1, le=100)
    sides: Optional[int] = Field(default=None, ge=2, le=1000)
    rolls: List[int] = Field(default_factory=list)

    # Modifiers
    modifier: int = 0
    bonus: int = 0
    attribute: Optional[str] = None

    # Total (client may provide; server will validate/compute if possible)
    grand_total: Optional[int] = None

    # Context (optional)
    roll_type: Optional[str] = None  # e.g. "check", "save", "attack", "damage", "stat", "custom"
    notation: Optional[str] = None   # e.g. "2d20+5", "4d6", "1d8+3" (basic parsing; advanced can be added later)
    context: Optional[Dict[str, Any]] = None

    # Visibility (future-proof; default public)
    visibility: str = "public"


class RollEvent(BaseModel):
    roll_id: str
    campaign_id: str
    created_at_epoch: float
    created_at: str

    character_id: Optional[str] = None
    character_name: Optional[str] = None
    owner_discord_id: Optional[str] = None
    player_name: Optional[str] = None

    dice_count: int
    sides: int
    rolls: List[int]

    modifier: int = 0
    bonus: int = 0
    attribute: Optional[str] = None

    grand_total: int

    roll_type: Optional[str] = None
    notation: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    visibility: str = "public"


_NOTATION_RE = re.compile(
    r"^\s*(?P<count>\d+)?\s*[dD]\s*(?P<sides>\d+)\s*(?P<mods>(?:[+\-]\s*\d+\s*)*)$"
)


def _parse_notation(notation: str) -> Tuple[int, int, int]:
    """Parse very common dice notation: NdS(+/-X...)

    Examples:
      - "d20" -> (1, 20, 0)
      - "1d20+5" -> (1, 20, 5)
      - "2d6-1" -> (2, 6, -1)
      - "4d6+2+1" -> (4, 6, 3)

    Advanced formats (kh/kl/dl/dh/explode) are intentionally not parsed here yet.
    They can be added later without breaking this contract.
    """
    if not notation:
        raise ValueError("empty_notation")

    m = _NOTATION_RE.match(notation)
    if not m:
        raise ValueError("unsupported_notation")

    count_str = (m.group("count") or "").strip()
    sides_str = (m.group("sides") or "").strip()
    mods_str = (m.group("mods") or "").strip()

    count = int(count_str) if count_str else 1
    sides = int(sides_str)

    # Sum all +/- numbers in the tail
    total_mod = 0
    if mods_str:
        for tok in re.finditer(r"([+\-])\s*(\d+)", mods_str):
            sign = tok.group(1)
            val = int(tok.group(2))
            total_mod += val if sign == "+" else -val

    if count < 1 or count > 100:
        raise ValueError("count_out_of_range")
    if sides < 2 or sides > 1000:
        raise ValueError("sides_out_of_range")

    return count, sides, total_mod


def _ensure_rolls(dice_count: int, sides: int, rolls: List[int]) -> List[int]:
    """If the client didn't provide rolls, generate server-side rolls safely."""
    if rolls and isinstance(rolls, list) and len(rolls) > 0:
        # Normalize and clamp to valid range without crashing
        out: List[int] = []
        for r in rolls[:dice_count]:
            try:
                rv = int(r)
            except Exception:
                continue
            if rv < 1:
                rv = 1
            if rv > sides:
                rv = sides
            out.append(rv)
        # If client sent fewer rolls than dice_count, fill remainder server-side
        while len(out) < dice_count:
            out.append(secrets.randbelow(sides) + 1)
        return out

    # No client rolls provided -> generate
    return [secrets.randbelow(sides) + 1 for _ in range(dice_count)]


def _compute_total(rolls: List[int], modifier: int, bonus: int) -> int:
    base = sum(int(x) for x in (rolls or []))
    return base + int(modifier or 0) + int(bonus or 0)


@router.post("/roll", response_model=RollEvent)
def create_roll(payload: RollCreate):
    """Create a roll event (canonical store) so bot/AI and other players can observe game state.

    Backward-compatible behavior:
      - If the client sends dice_count+sides (+ optional rolls), the server stores/normalizes.
      - If the client sends ONLY notation (e.g., "1d20+5"), the server parses and generates rolls.
    """
    if db is None:
        raise HTTPException(status_code=503, detail="database_unavailable")

    # Resolve campaign id canonically
    campaign_id = (payload.campaign_id or "").strip() or get_active_campaign_id(db)

    # Determine dice parameters
    dice_count = int(payload.dice_count or 1)
    sides = payload.sides

    # If sides missing but notation provided, parse it
    parsed_mod = None
    if (sides is None or int(sides) == 0) and payload.notation:
        try:
            dc, sd, mod = _parse_notation(payload.notation)
            dice_count = dc
            sides = sd
            parsed_mod = mod
        except ValueError as e:
            raise HTTPException(status_code=422, detail=f"invalid_notation: {e}")

    # If sides is still missing, we cannot proceed
    if sides is None:
        raise HTTPException(status_code=422, detail="missing_required: sides or notation")

    sides_i = int(sides)

    # If notation provided and modifier not explicitly set, use parsed modifier
    modifier = int(payload.modifier or 0)
    if parsed_mod is not None and modifier == 0 and (payload.notation or "").strip():
        modifier = int(parsed_mod)

    bonus = int(payload.bonus or 0)

    # Normalize / generate rolls
    rolls = _ensure_rolls(dice_count=dice_count, sides=sides_i, rolls=payload.rolls or [])

    # Determine grand total
    computed_total = _compute_total(rolls, modifier, bonus)
    grand_total = payload.grand_total
    if grand_total is None:
        grand_total = computed_total
    else:
        try:
            if int(grand_total) != int(computed_total):
                # Prefer computed truth when we have normalized rolls
                grand_total = computed_total
        except Exception:
            grand_total = computed_total

    now = float(time.time())
    roll_id = str(uuid.uuid4())

    event: Dict[str, Any] = {
        "roll_id": roll_id,
        "campaign_id": campaign_id,
        "created_at_epoch": now,
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),

        "character_id": payload.character_id,
        "character_name": payload.character_name,
        "owner_discord_id": payload.owner_discord_id,
        "player_name": payload.player_name,

        "dice_count": int(dice_count),
        "sides": int(sides_i),
        "rolls": [int(x) for x in rolls],

        "modifier": int(modifier),
        "bonus": int(bonus),
        "attribute": payload.attribute,

        "grand_total": int(grand_total),

        "roll_type": payload.roll_type,
        "notation": payload.notation,
        "context": payload.context or None,
        "visibility": payload.visibility or "public",
    }

    try:
        db["roll_events"].insert_one(event)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"roll_insert_failed: {e}")

    return event


@router.get("/rolls", response_model=List[RollEvent])
def list_rolls(
    limit: int = Query(50, ge=1, le=200),
    campaign_id: Optional[str] = Query(None),
):
    """List recent roll events for the active campaign (or specified campaign_id)."""
    if db is None:
        raise HTTPException(status_code=503, detail="database_unavailable")

    cid = (campaign_id or "").strip() or get_active_campaign_id(db)
    try:
        cur = (
            db["roll_events"]
            .find({"campaign_id": cid}, {"_id": 0})
            .sort("created_at_epoch", -1)
            .limit(int(limit))
        )
        return list(cur)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"roll_query_failed: {e}")
