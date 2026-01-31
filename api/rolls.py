#===============================================================
#Script Name: rolls.py
#Script Location: /opt/RealmQuest/api/rolls.py
#Date: 01/31/2026
#Created By: T03KNEE
#Github: https://github.com/To3Knee/RealmQuest
#Version: 1.1.3
#About: Canonical roll event endpoints for bot-aware dice and shared player roll feed.
#       Adds advanced dice notation parsing (kh/kl/dh/dl), advantage/disadvantage,
#       d100/percentile (d%), and stat-block rolling (4d6 drop-lowest x6).
#       Additive and backward-compatible: existing clients that send dice_count+sides+rolls still work.
#===============================================================

import os
import re
import time
import uuid
import secrets
from typing import Any, Dict, List, Optional, Tuple, Union

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


# -----------------------------
# Models
# -----------------------------

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
    roll_type: Optional[str] = None  # e.g. "check", "save", "attack", "damage", "stat", "custom", "stat_block"
    notation: Optional[str] = None   # e.g. "2d20kh1+5", "4d6dl1", "d%", "1d8+3"
    context: Optional[Dict[str, Any]] = None

    # Visibility (future-proof; default public)
    visibility: str = "public"


class DiceTermDetail(BaseModel):
    sign: int
    count: int
    sides: int
    keep_drop: Optional[str] = None  # kh/kl/dh/dl
    keep_drop_n: Optional[int] = None
    rolls: List[int] = Field(default_factory=list)
    kept: List[int] = Field(default_factory=list)
    dropped: List[int] = Field(default_factory=list)
    subtotal: int = 0


class ExpressionDetail(BaseModel):
    normalized: str
    constants: int = 0
    terms: List[DiceTermDetail] = Field(default_factory=list)
    total: int = 0
    is_percentile: bool = False


class RollEvent(BaseModel):
    roll_id: str
    campaign_id: str
    created_at_epoch: float
    created_at: str

    character_id: Optional[str] = None
    character_name: Optional[str] = None
    owner_discord_id: Optional[str] = None
    player_name: Optional[str] = None

    # For backwards compatibility, keep the original single-group fields.
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

    # New optional advanced breakdown (safe additive)
    expression: Optional[ExpressionDetail] = None
    kept: Optional[List[int]] = None
    dropped: Optional[List[int]] = None


class StatsRequest(BaseModel):
    # Identity (same as RollCreate, subset)
    campaign_id: Optional[str] = None
    character_id: Optional[str] = None
    character_name: Optional[str] = None
    owner_discord_id: Optional[str] = None
    player_name: Optional[str] = None

    # Stat rolling config
    method: str = "4d6dl1"  # classic 5e method
    stats: int = Field(default=6, ge=1, le=12)

    # Optional context
    roll_type: str = "stat_block"
    visibility: str = "public"


# -----------------------------
# Notation parsing and evaluation
# -----------------------------

# Supported dice term:
#   [count]d[sides|%][khN|klN|dhN|dlN]
# Examples: d20, 2d20kh1, 4d6dl1, d%, 1d100
_DICE_TERM_RE = re.compile(r"^(?P<count>\d*)[dD](?P<sides>\d+|%)(?P<kd>(?:kh|kl|dh|dl)\d+)?$")


def _split_signed(expr: str) -> List[Tuple[int, str]]:
    """Tokenize by +/-, keeping signs, after stripping whitespace."""
    s = (expr or "").strip()
    if not s:
        return []
    s = re.sub(r"\s+", "", s)

    parts: List[Tuple[int, str]] = []
    i = 0
    sign = 1
    buf = ""
    while i < len(s):
        ch = s[i]
        if ch in "+-":
            if buf:
                parts.append((sign, buf))
                buf = ""
            sign = 1 if ch == "+" else -1
            i += 1
            continue
        buf += ch
        i += 1
    if buf:
        parts.append((sign, buf))
    return parts


def _parse_term(token: str) -> Union[int, Dict[str, Any]]:
    """
    Returns:
      - int constant, or
      - dict for dice term with keys: count, sides, keep_drop, keep_drop_n, is_percentile
    """
    if token.isdigit():
        return int(token)

    m = _DICE_TERM_RE.match(token)
    if not m:
        raise ValueError(f"unsupported_token:{token}")

    count_str = (m.group("count") or "").strip()
    sides_str = (m.group("sides") or "").strip()
    kd_str = (m.group("kd") or "").strip()

    count = int(count_str) if count_str else 1
    is_percentile = False
    if sides_str == "%":
        sides = 100
        is_percentile = True
    else:
        sides = int(sides_str)

    keep_drop = None
    keep_drop_n = None
    if kd_str:
        keep_drop = kd_str[:2].lower()
        keep_drop_n = int(kd_str[2:])

    # Validate ranges
    if count < 1 or count > 100:
        raise ValueError("count_out_of_range")
    if sides < 2 or sides > 1000:
        raise ValueError("sides_out_of_range")
    if keep_drop is not None:
        if keep_drop_n is None or keep_drop_n < 1 or keep_drop_n > count:
            raise ValueError("keep_drop_out_of_range")

    return {
        "count": count,
        "sides": sides,
        "keep_drop": keep_drop,
        "keep_drop_n": keep_drop_n,
        "is_percentile": is_percentile,
    }


def _apply_keep_drop(rolls: List[int], keep_drop: Optional[str], n: Optional[int]) -> Tuple[List[int], List[int]]:
    if not rolls:
        return [], []
    if not keep_drop or not n:
        return list(rolls), []

    indexed = list(enumerate(int(x) for x in rolls))
    indexed_sorted = sorted(indexed, key=lambda t: (t[1], t[0]))

    if keep_drop == "kh":
        keep = sorted(indexed, key=lambda t: (t[1], t[0]), reverse=True)[:n]
        keep_idx = set(i for i, _ in keep)
    elif keep_drop == "kl":
        keep = indexed_sorted[:n]
        keep_idx = set(i for i, _ in keep)
    elif keep_drop == "dh":
        drop = sorted(indexed, key=lambda t: (t[1], t[0]), reverse=True)[:n]
        drop_idx = set(i for i, _ in drop)
        keep_idx = set(i for i, _ in indexed if i not in drop_idx)
    elif keep_drop == "dl":
        drop = indexed_sorted[:n]
        drop_idx = set(i for i, _ in drop)
        keep_idx = set(i for i, _ in indexed if i not in drop_idx)
    else:
        keep_idx = set(range(len(rolls)))

    kept = [int(v) for i, v in indexed if i in keep_idx]
    dropped = [int(v) for i, v in indexed if i not in keep_idx]
    return kept, dropped


def _ensure_rolls(count: int, sides: int, provided: Optional[List[int]] = None) -> List[int]:
    if provided and isinstance(provided, list) and len(provided) > 0:
        out: List[int] = []
        for r in provided[:count]:
            try:
                rv = int(r)
            except Exception:
                continue
            if rv < 1:
                rv = 1
            if rv > sides:
                rv = sides
            out.append(rv)
        while len(out) < count:
            out.append(secrets.randbelow(sides) + 1)
        return out
    return [secrets.randbelow(sides) + 1 for _ in range(count)]


def _evaluate_notation(
    notation: str,
    provided_rolls: Optional[List[int]],
    fallback_modifier: int,
    fallback_bonus: int,
) -> Tuple[ExpressionDetail, int, int, List[int], List[int], List[int], int, int, int]:
    """
    Evaluate a dice notation expression.

    Returns:
      (expression_detail, rep_count, rep_sides, rep_rolls, kept_flat, dropped_flat, modifier_used, bonus_used, computed_total)

    Rules:
      - Supports multi-term: "2d6+1d8+3"
      - Supports keep/drop on each dice term: kh/kl/dh/dl
      - Percentile: d% -> d100
      - Constants inside notation are treated as modifier ONLY if (fallback_modifier==0 and fallback_bonus==0).
        This preserves backward compatibility with clients that already send modifier separately.
    """
    parts = _split_signed(notation)
    if not parts:
        raise ValueError("empty_notation")

    constants = 0
    dice_terms: List[DiceTermDetail] = []
    is_percentile = False

    # If there is exactly one dice term and the caller provided rolls, allow them to be used.
    can_use_provided_rolls = bool(provided_rolls) and len(parts) == 1

    for sign, tok in parts:
        term = _parse_term(tok)
        if isinstance(term, int):
            constants += sign * term
            continue

        is_percentile = is_percentile or bool(term.get("is_percentile"))
        count = int(term["count"])
        sides = int(term["sides"])
        kd = term.get("keep_drop")
        kd_n = term.get("keep_drop_n")

        if can_use_provided_rolls:
            rolls_for_term = _ensure_rolls(count, sides, provided_rolls)
        else:
            rolls_for_term = _ensure_rolls(count, sides, None)

        kept, dropped = _apply_keep_drop(rolls_for_term, kd, kd_n)
        subtotal = sign * sum(kept)

        dice_terms.append(DiceTermDetail(
            sign=sign,
            count=count,
            sides=sides,
            keep_drop=kd,
            keep_drop_n=kd_n,
            rolls=[int(x) for x in rolls_for_term],
            kept=[int(x) for x in kept],
            dropped=[int(x) for x in dropped],
            subtotal=int(subtotal),
        ))

    modifier_used = int(fallback_modifier or 0)
    bonus_used = int(fallback_bonus or 0)

    # Apply constants as modifier only when client didn't supply modifiers.
    constants_for_display = int(constants)
    if (modifier_used == 0 and bonus_used == 0) and constants != 0:
        modifier_used = int(constants)
        constants = 0

    base_total = sum(int(t.subtotal) for t in dice_terms) + int(constants)
    computed_total = int(base_total + modifier_used + bonus_used)

    normalized = re.sub(r"\s+", "", (notation or "").strip())

    expr_detail = ExpressionDetail(
        normalized=normalized,
        constants=int(constants_for_display),
        terms=dice_terms,
        total=int(base_total),
        is_percentile=bool(is_percentile),
    )

    rep_count = dice_terms[0].count if dice_terms else 1
    rep_sides = dice_terms[0].sides if dice_terms else 20
    rep_rolls = dice_terms[0].rolls if dice_terms else []

    kept_flat: List[int] = []
    dropped_flat: List[int] = []
    for t in dice_terms:
        kept_flat.extend(t.kept)
        dropped_flat.extend(t.dropped)

    return expr_detail, rep_count, rep_sides, rep_rolls, kept_flat, dropped_flat, modifier_used, bonus_used, computed_total


def _compute_total_simple(rolls: List[int], modifier: int, bonus: int) -> int:
    base = sum(int(x) for x in (rolls or []))
    return base + int(modifier or 0) + int(bonus or 0)


# -----------------------------
# Endpoints
# -----------------------------

@router.post("/roll", response_model=RollEvent)
def create_roll(payload: RollCreate):
    """Create a canonical roll event for shared feed + bot awareness."""
    if db is None:
        raise HTTPException(status_code=503, detail="database_unavailable")

    campaign_id = (payload.campaign_id or "").strip() or get_active_campaign_id(db)
    now = float(time.time())
    roll_id = str(uuid.uuid4())

    dice_count = int(payload.dice_count or 1)
    sides = int(payload.sides) if payload.sides is not None else None
    rolls = payload.rolls or []
    modifier = int(payload.modifier or 0)
    bonus = int(payload.bonus or 0)

    expression: Optional[ExpressionDetail] = None
    kept: Optional[List[int]] = None
    dropped: Optional[List[int]] = None

    if payload.notation and str(payload.notation).strip():
        try:
            expression, rep_count, rep_sides, rep_rolls, kept_flat, dropped_flat, mod_used, bonus_used, computed_total = _evaluate_notation(
                notation=str(payload.notation),
                provided_rolls=rolls,
                fallback_modifier=modifier,
                fallback_bonus=bonus,
            )
            dice_count = int(rep_count)
            sides = int(rep_sides)
            rolls = rep_rolls
            kept = kept_flat
            dropped = dropped_flat
            modifier = int(mod_used)
            bonus = int(bonus_used)
        except ValueError as e:
            raise HTTPException(status_code=422, detail=f"invalid_notation: {e}")
    else:
        if sides is None:
            raise HTTPException(status_code=422, detail="missing_required: sides or notation")
        rolls = _ensure_rolls(dice_count, int(sides), rolls)
        computed_total = _compute_total_simple(rolls, modifier, bonus)
        kept = list(rolls)
        dropped = []

    grand_total = payload.grand_total
    if grand_total is None:
        grand_total = int(computed_total)
    else:
        try:
            if int(grand_total) != int(computed_total):
                grand_total = int(computed_total)
        except Exception:
            grand_total = int(computed_total)

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
        "sides": int(sides if sides is not None else 20),
        "rolls": [int(x) for x in (rolls or [])],

        "modifier": int(modifier),
        "bonus": int(bonus),
        "attribute": payload.attribute,

        "grand_total": int(grand_total),

        "roll_type": payload.roll_type,
        "notation": payload.notation,
        "context": payload.context or None,
        "visibility": payload.visibility or "public",

        "expression": expression.model_dump() if expression is not None else None,
        "kept": kept,
        "dropped": dropped,
    }

    try:
        db["roll_events"].insert_one({k: v for k, v in event.items() if v is not None})
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



@router.delete("/rolls")
def clear_rolls(
    campaign_id: Optional[str] = Query(None),
):
    """Clear roll events for the active campaign (or an explicit campaign_id).

    This is used by the Portal trash-can action so the shared feed does not repopulate
    on the next poll cycle.
    """
    if db is None:
        raise HTTPException(status_code=503, detail="mongo_unavailable")

    cid = campaign_id or get_active_campaign_id(db)
    if not cid:
        raise HTTPException(status_code=400, detail="missing_campaign_id")

    try:
        res = db["roll_events"].delete_many({"campaign_id": cid})
        return {"campaign_id": cid, "deleted": int(res.deleted_count)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"roll_clear_failed: {e}")
@router.post("/rolls/clear")
def clear_rolls_post(
    campaign_id: Optional[str] = Query(None),
):
    """POST-based clear endpoint (browser/proxy friendly).

    Some environments (or security middleware) block DELETE requests from browsers.
    The Portal will prefer this endpoint and fall back to DELETE.
    """
    return clear_rolls(campaign_id=campaign_id)


@router.post("/roll/stats", response_model=RollEvent)
def roll_stats_block(payload: StatsRequest):
    """Roll a full stat block (default: 4d6dl1, x6) and store as a single canonical event."""
    if db is None:
        raise HTTPException(status_code=503, detail="database_unavailable")

    campaign_id = (payload.campaign_id or "").strip() or get_active_campaign_id(db)
    method = (payload.method or "4d6dl1").strip()
    n_stats = int(payload.stats or 6)

    stats: List[Dict[str, Any]] = []
    totals: List[int] = []
    for i in range(n_stats):
        expr, _, _, _, kept, dropped, _, _, computed_total = _evaluate_notation(
            notation=method,
            provided_rolls=None,
            fallback_modifier=0,
            fallback_bonus=0,
        )
        # Expect first dice term to hold the dice breakdown.
        term0 = expr.terms[0] if expr.terms else None
        stat_rolls = term0.rolls if term0 else []
        stat_kept = term0.kept if term0 else kept
        stat_dropped = term0.dropped if term0 else dropped

        stats.append({
            "index": i + 1,
            "method": method,
            "rolls": [int(x) for x in stat_rolls],
            "kept": [int(x) for x in stat_kept],
            "dropped": [int(x) for x in stat_dropped],
            "total": int(computed_total),
        })
        totals.append(int(computed_total))

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

        "dice_count": 4,
        "sides": 6,
        "rolls": [],

        "modifier": 0,
        "bonus": 0,
        "attribute": None,

        # store sum of all stats as grand_total (useful quick metric; details in context)
        "grand_total": int(sum(totals)),

        "roll_type": payload.roll_type or "stat_block",
        "notation": f"{method} x{n_stats}",
        "context": {
            "method": method,
            "stats": stats,
            "totals": totals,
        },
        "visibility": payload.visibility or "public",
    }

    try:
        db["roll_events"].insert_one(event)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"roll_insert_failed: {e}")

    return event


@router.get("/roll/templates")
def list_roll_templates():
    """Template catalog for portal/bot. Additive; does not change UI unless wired in."""
    return {
        "templates": [
            {"id": "d20", "label": "d20 (check/save/attack)", "notation": "1d20", "description": "Standard d20 roll."},
            {"id": "adv", "label": "Advantage (2d20 keep highest)", "notation": "2d20kh1", "description": "Advantage roll."},
            {"id": "dis", "label": "Disadvantage (2d20 keep lowest)", "notation": "2d20kl1", "description": "Disadvantage roll."},
            {"id": "stats_4d6dl1", "label": "Stats (4d6 drop lowest) x6", "notation": "4d6dl1 x6", "description": "Roll 6 ability scores."},
            {"id": "percentile", "label": "Percentile (d%)", "notation": "d%", "description": "Percentile roll (d100)."},
            {"id": "damage_d8", "label": "Damage (1d8)", "notation": "1d8", "description": "Common weapon/spell damage die."},
        ]
    }