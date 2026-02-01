#===============================================================
#Script Name: roll_watcher.py
#Script Location: /opt/RealmQuest/bot/core/roll_watcher.py
#Date: 02/01/2026
#Created By: T03KNEE
#Github: https://github.com/To3Knee/RealmQuest
#Version: 1.1.7
#About: Polls the API roll feed and posts new roll events to the same Discord text channel used for narration/listening.
#       Enhanced formatting: keep/drop (adv/dis), stat blocks, percentile notation, and safer channel routing via Redis key rq_text_channel_id.
#       Additive, no portal UI drift.
#===============================================================

import asyncio
import logging
import time
import datetime
import os
import re
from typing import Any, Dict, List, Optional

import aiohttp
import discord


logger = logging.getLogger("rq.roll_watcher")


def _safe_int(v: Any) -> Optional[int]:
    try:
        return int(v)
    except Exception:
        return None

def _human_campaign_name(campaign_id: Any) -> str:
    """Convert campaign ids like 'the_collision_stone' -> 'The Collision Stone'."""
    if not campaign_id:
        return "Unknown"
    s = str(campaign_id).strip()
    if not s:
        return "Unknown"
    # Replace underscores/dashes with spaces, collapse whitespace, Title Case
    s = re.sub(r"[_-]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    # Title-case words while keeping small words readable (e.g., 'of', 'the')
    # We'll use title() as a simple baseline; can be refined later.
    return s.title()


def _format_footer_timestamp(ts: str) -> str:
    """Format API timestamp 'YYYY-MM-DD HH:MM:SS' -> 'Date: mm/dd/yyyy Time: HH:MM:SS'."""
    if not ts:
        return ""
    s = str(ts).strip()
    if not s:
        return ""
    # Common format from API: '2026-01-31 22:33:30'
    try:
        dt = datetime.datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
        return f"Date: {dt:%m/%d/%Y} Time: {dt:%H:%M:%S}"
    except Exception:
        # Best-effort fallback: if it already contains a date and time, just label it.
        return f"Date/Time: {s}"


def _fmt_dice_list(raw: List[int], kept: Optional[List[int]] = None) -> str:
    """
    Format dice results. If kept is provided, dropped dice are strikethrough.
    This is a best-effort visualization; ties may keep/drop in stable order from the API.
    """
    if not isinstance(raw, list):
        return str(raw)

    if not raw:
        return "[]"

    if not kept:
        return "[" + ", ".join(str(x) for x in raw) + "]"

    # Use multiset matching so duplicates are handled.
    kept_pool: Dict[int, int] = {}
    for k in kept:
        kept_pool[int(k)] = kept_pool.get(int(k), 0) + 1

    out = []
    for r in raw:
        rv = int(r)
        if kept_pool.get(rv, 0) > 0:
            out.append(str(rv))
            kept_pool[rv] -= 1
        else:
            out.append(f"~~{rv}~~")
    return "[" + ", ".join(out) + "]"


class RollWatcher:
    """
    RollWatcher continuously polls the API's /game/rolls endpoint and announces new rolls.

    Channel routing:
    - Uses Redis key 'rq_text_channel_id' (string) when available.
    - Falls back to in-memory last_channel_id if provided.

    Deduping:
    - Uses Redis key 'rq_last_seen_roll_epoch' and 'rq_last_seen_roll_id' (optional).
    """

    def __init__(
        self,
        bot: discord.Client,
        api_url: str,
        redis_client=None,
        poll_interval: float = 2.0,
        limit: int = 50,
        channel_id_getter=None,
    ):
        self.bot = bot
        self.api_url = api_url.rstrip("/")
        self.r = redis_client
        self.poll_interval = max(0.8, float(poll_interval))
        self.limit = max(5, min(int(limit), 200))
        self._channel_id_getter = channel_id_getter
        self._env_channel_id = _safe_int(os.getenv("RQ_TEXT_CHANNEL_ID") or os.getenv("REALMQUEST_TEXT_CHANNEL_ID") or "")
        self._task: Optional[asyncio.Task] = None
        self._stop = asyncio.Event()

    def start(self):
        if self._task and not self._task.done():
            return
        self._stop.clear()
        self._task = asyncio.create_task(self._run(), name="rq_roll_watcher")

    async def stop(self):
        self._stop.set()
        if self._task:
            try:
                await asyncio.wait_for(self._task, timeout=5.0)
            except Exception:
                pass

    def _get_text_channel_id(self) -> Optional[int]:
        # 0) Env override (stable channel binding across restarts)
        if getattr(self, "_env_channel_id", None):
            return self._env_channel_id
        # 1) In-memory getter (set by Listen/buttons), 2) Redis canonical storage
        if self._channel_id_getter:
            try:
                cid = self._channel_id_getter()
                if cid:
                    return _safe_int(cid)
            except Exception:
                pass
        if self.r:
            try:
                cid = self.r.get("rq_text_channel_id")
                if cid:
                    return _safe_int(cid)
            except Exception:
                pass
        return None

    def _get_last_seen_epoch(self) -> float:
        if self.r:
            try:
                v = self.r.get("rq_last_seen_roll_epoch")
                if v:
                    return float(v)
            except Exception:
                pass
        return 0.0

    def _set_last_seen(self, epoch: float, roll_id: Optional[str] = None):
        if not self.r:
            return
        try:
            self.r.set("rq_last_seen_roll_epoch", str(epoch))
            if roll_id:
                self.r.set("rq_last_seen_roll_id", roll_id)
        except Exception:
            pass

    async def _fetch_rolls(self) -> List[Dict[str, Any]]:
        url = f"{self.api_url}/game/rolls?limit={self.limit}"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=8)) as resp:
                    if resp.status != 200:
                        return []
                    data = await resp.json()
                    if isinstance(data, list):
                        return data
        except Exception as e:
            logger.debug(f"poll failed: {e}")
        return []

    def _detect_nat(self, ev: Dict[str, Any]) -> Optional[str]:
        """
        Detect nat 20 / nat 1 for a kept d20.
        Works for normal and adv/dis (2d20kh1/kl1).
        """
        try:
            # Prefer kept array (flattened) if present
            kept = ev.get("kept") or None
            sides = int(ev.get("sides") or 0)
            if sides != 20:
                return None
            if kept and isinstance(kept, list) and kept:
                # if any kept die is 20 or 1, report
                vals = [int(x) for x in kept]
                if 20 in vals:
                    return "nat20"
                if 1 in vals:
                    return "nat1"
            # Fallback: single roll
            rolls = ev.get("rolls") or []
            dice_count = int(ev.get("dice_count") or 0)
            if dice_count == 1 and isinstance(rolls, list) and rolls:
                if int(rolls[0]) == 20:
                    return "nat20"
                if int(rolls[0]) == 1:
                    return "nat1"
        except Exception:
            return None
        return None

    def _detect_adv_dis(self, ev: Dict[str, Any]) -> Optional[str]:
        """Detect 5e advantage/disadvantage (2d20 keep-high/keep-low 1)."""
        try:
            expr = ev.get("expression")
            if isinstance(expr, dict):
                terms = expr.get("terms") or []
                if isinstance(terms, list) and terms:
                    t0 = terms[0] or {}
                    c = int(t0.get("count") or 0)
                    s = int(t0.get("sides") or 0)
                    kd = t0.get("keep_drop")
                    kdn = t0.get("keep_drop_n")
                    try:
                        kdn_i = int(kdn) if kdn is not None else 0
                    except Exception:
                        kdn_i = 0
                    if c == 2 and s == 20 and kdn_i == 1 and kd in ("kh", "kl"):
                        return "Advantage" if kd == "kh" else "Disadvantage"

            # Fallback: notation parse
            notation = str(ev.get("notation") or "").lower()
            if "2d20" in notation and "kh1" in notation:
                return "Advantage"
            if "2d20" in notation and "kl1" in notation:
                return "Disadvantage"
        except Exception:
            return None
        return None


    def _pretty_context_label(self, ctx: str) -> str:
        """Convert portal-supplied context into a clean, human label."""
        raw = (ctx or "").strip()
        if not raw:
            return ""
        low = raw.lower().strip()

        # Common checks / actions (extend safely; defaults remain readable)
        mapping = {
            "initiative": "Initiative",
            "stealth": "Stealth Check",
            "perception": "Perception Check",
            "insight": "Insight Check",
            "athletics": "Athletics Check",
            "acrobatics": "Acrobatics Check",
            "sleight of hand": "Sleight of Hand Check",
            "sleight": "Sleight of Hand Check",
            "investigation": "Investigation Check",
            "arcana": "Arcana Check",
            "history": "History Check",
            "nature": "Nature Check",
            "religion": "Religion Check",
            "survival": "Survival Check",
            "medicine": "Medicine Check",
            "animal handling": "Animal Handling Check",
            "deception": "Deception Check",
            "intimidation": "Intimidation Check",
            "performance": "Performance Check",
            "persuasion": "Persuasion Check",
        }
        if low in mapping:
            return mapping[low]

        # Ability shorthand
        abil = {"str": "STR", "dex": "DEX", "con": "CON", "int": "INT", "wis": "WIS", "cha": "CHA"}
        if low in abil:
            return f"{abil[low]} Check"

        # If already contains 'check' or looks like a phrase, Title Case it lightly
        # Preserve known acronyms
        def smart_title(s: str) -> str:
            parts = [p for p in re.split(r"(\s+)", s) if p != ""]
            out = []
            for p in parts:
                if p.isspace():
                    out.append(p)
                    continue
                pl = p.lower()
                if pl in ("of", "the", "and", "or", "to", "in", "on", "at", "for", "a", "an"):
                    out.append(pl)
                elif pl in ("str","dex","con","int","wis","cha","ac","hp","dc"):
                    out.append(pl.upper())
                else:
                    out.append(p[:1].upper() + p[1:])
            # Ensure first token capitalized
            txt = "".join(out).strip()
            if txt:
                txt = txt[:1].upper() + txt[1:]
            return txt

        return smart_title(raw)

    def _explain_notation(self, ev: Dict[str, Any]) -> str:
        """Provide a short, newbie-friendly explanation of special notations."""
        adv_dis = self._detect_adv_dis(ev)
        notation = str(ev.get("notation") or "").strip()
        if adv_dis == "Advantage":
            return "Advantage (2d20 keep-high 1)"
        if adv_dis == "Disadvantage":
            return "Disadvantage (2d20 keep-low 1)"

        # Percentile
        expr = ev.get("expression")
        if isinstance(expr, dict) and expr.get("is_percentile"):
            return "Percentile (d%)"

        # Stat blocks
        roll_type = (ev.get("roll_type") or "").strip()
        if roll_type == "stat_block":
            return "Stat Block (4d6 drop-lowest 1 ×6)"

        # No special explanation needed
        return notation or "—"

    def _format_dice_display(self, ev: Dict[str, Any]) -> str:
        """Format dice results; show kept vs dropped (strikethrough) when available."""
        kept = ev.get("kept")
        dropped = ev.get("dropped")
        rolls = ev.get("rolls") or []

        def fmt_list(nums):
            return " ".join([f"[{int(n)}]" for n in nums]) if nums else ""

        try:
            if isinstance(kept, list) and isinstance(dropped, list) and (kept or dropped):
                kept_txt = fmt_list(kept)
                dropped_txt = " ".join([f"~~[{int(n)}]~~" for n in dropped]) if dropped else ""
                return (kept_txt + (" " if kept_txt and dropped_txt else "") + dropped_txt).strip() or "—"
        except Exception:
            pass

        # Fallback: raw rolls
        try:
            if isinstance(rolls, list) and rolls:
                return fmt_list(rolls)
        except Exception:
            pass

        return "—"

    def _format_embed(self, ev: Dict[str, Any]) -> discord.Embed:
        character = ev.get("character_name") or "Unknown"
        roll_type_raw = ev.get("roll_type") or "roll"
        roll_type_disp = roll_type_raw
        adv_dis = self._detect_adv_dis(ev)
        if adv_dis and roll_type_raw != "stat_block":
            roll_type_disp = f"{roll_type_raw} • {adv_dis}"
        visibility = ev.get("visibility") or "public"
        notation = ev.get("notation") or f'{ev.get("dice_count","?")}d{ev.get("sides","?")}'
        total = ev.get("grand_total")
        ts = ev.get("created_at") or ""
        campaign = _human_campaign_name(ev.get("campaign_id", ""))

        nat = self._detect_nat(ev)
        title = "🎲 Roll"
        if nat == "nat20":
            title = "🎲 Roll • CRIT!"
        elif nat == "nat1":
            title = "🎲 Roll • FUMBLE!"

        embed = discord.Embed(title=title)
        # Subtle visual polish: color accent for crit/fumble (no extra spam)
        if nat == "nat20":
            embed.color = 0xF1C40F  # gold
        elif nat == "nat1":
            embed.color = 0xE74C3C  # red
        else:
            embed.color = 0x9B59B6  # purple
        embed.add_field(name="🧙 Character", value=str(character), inline=True)
        embed.add_field(name="🧭 Type", value=str(roll_type_disp), inline=True)
        embed.add_field(name="🧮 Notation", value=str(notation), inline=False)
        embed.add_field(name="📜 Formula", value=str(self._explain_notation(ev)), inline=False)

        # Stat block special view
        if roll_type_raw == "stat_block":
            ctx = ev.get("context") or {}
            stats = ctx.get("stats") if isinstance(ctx, dict) else None
            if isinstance(stats, list) and stats:
                lines = []
                for s in stats[:12]:
                    idx = s.get("index")
                    raw = s.get("rolls") or []
                    kept = s.get("kept") or []
                    val = s.get("total")
                    lines.append(f"{idx}) {_fmt_dice_list(raw, kept)} = **{val}**")
                embed.add_field(name="Stats", value="\n".join(lines)[:1024], inline=False)
                embed.add_field(name="🧾 Sum", value=f"**{total if total is not None else '?'}**", inline=True)
                embed.add_field(name="👁️ Visibility", value=str(visibility), inline=True)
            else:
                embed.add_field(name="🎯 Total", value=f"**{total if total is not None else '?'}**", inline=True)
                embed.add_field(name="👁️ Visibility", value=str(visibility), inline=True)
        else:
            dice_str = self._format_dice_display(ev)

            # Modifier breakdown
            mod = int(ev.get("modifier") or 0)
            bonus = int(ev.get("bonus") or 0)
            breakdown = []
            if mod:
                breakdown.append(f"{mod:+d}")
            if bonus:
                breakdown.append(f"{bonus:+d}")
            breakdown_str = " ".join(breakdown) if breakdown else "—"

            embed.add_field(name="🎲 Dice", value=dice_str, inline=True)
            embed.add_field(name="➕ Mods", value=breakdown_str, inline=True)
            embed.add_field(name="Total", value=str(total if total is not None else "?"), inline=True)
            embed.add_field(name="Visibility", value=str(visibility), inline=True)

            # If there is an expression breakdown with multiple terms, show a compact detail line.
            expr = ev.get("expression")
            try:
                if isinstance(expr, dict):
                    terms = expr.get("terms") or []
                    if isinstance(terms, list) and len(terms) > 1:
                        mini = []
                        for t in terms[:4]:
                            sign = "-" if int(t.get("sign") or 1) < 0 else "+"
                            c = t.get("count")
                            s = t.get("sides")
                            kd = t.get("keep_drop")
                            kdn = t.get("keep_drop_n")
                            tag = f"{c}d{s}"
                            if kd and kdn:
                                tag += f"{kd}{kdn}"
                            mini.append(f"{sign}{tag}")
                        embed.add_field(name="🧩 Breakdown", value=(" ".join(mini)).lstrip("+")[:1024], inline=False)
            except Exception:
                pass

            # Optional context string
            ctx = ev.get("context") or None
            if isinstance(ctx, str) and ctx.strip():
                embed.add_field(name="🗣️ Context", value=self._pretty_context_label(ctx.strip())[:1024], inline=False)

        if ts or campaign:
            ts_fmt = _format_footer_timestamp(ts)
            camp = campaign or "Unknown"
            if ts_fmt:
                embed.set_footer(text=f"{ts_fmt} • Campaign: {camp}")
            else:
                embed.set_footer(text=f"Campaign: {camp}")
        return embed

    async def _announce(self, channel_id: int, events: List[Dict[str, Any]]):
        channel = self.bot.get_channel(channel_id)
        if channel is None:
            try:
                channel = await self.bot.fetch_channel(channel_id)
            except Exception:
                return

        for ev in events:
            try:
                await channel.send(embed=self._format_embed(ev))
            except Exception as e:
                logger.warning(f"Discord send failed for roll_id={ev.get('roll_id')}: {e}")

    async def _run(self):
        await self.bot.wait_until_ready()
        logger.info("🎲 RollWatcher online.")

        # Avoid replaying historical rolls on fresh start unless explicitly desired.
        try:
            if self._get_last_seen_epoch() <= 0.0:
                self._set_last_seen(time.time(), None)
        except Exception:
            pass

        while not self._stop.is_set():
            channel_id = self._get_text_channel_id()
            if not channel_id:
                # If no channel is bound, we can't announce. Log occasionally.
                try:
                    now = time.time()
                    last = getattr(self, "_last_nochan_log", 0.0)
                    if now - last > 30.0:
                        logger.info("🎲 RollWatcher waiting for rq_text_channel_id (or RQ_TEXT_CHANNEL_ID env) to be set...")
                        self._last_nochan_log = now
                except Exception:
                    pass
                await asyncio.sleep(self.poll_interval)
                continue

            last_epoch = self._get_last_seen_epoch()
            rolls = await self._fetch_rolls()

            new_events = []
            newest_epoch = last_epoch
            newest_id = None

            for ev in rolls:
                try:
                    ev_epoch = float(ev.get("created_at_epoch") or 0.0)
                except Exception:
                    ev_epoch = 0.0
                if ev_epoch > last_epoch + 1e-6:
                    new_events.append(ev)
                if ev_epoch > newest_epoch:
                    newest_epoch = ev_epoch
                    newest_id = ev.get("roll_id")

            if new_events:
                new_events.sort(key=lambda x: float(x.get("created_at_epoch") or 0.0))
                await self._announce(channel_id, new_events)
                self._set_last_seen(newest_epoch, newest_id)

            await asyncio.sleep(self.poll_interval)
