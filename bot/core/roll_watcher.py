#===============================================================
#Script Name: roll_watcher.py
#Script Location: /opt/RealmQuest/bot/core/roll_watcher.py
#Date: 01/31/2026
#Created By: T03KNEE
#Github: https://github.com/To3Knee/RealmQuest
#Version: 1.0.1
#About: Polls the API roll feed and posts new roll events to the same Discord text channel used for narration/listening. Additive, no UI drift.
#===============================================================

import asyncio
import json
import logging
import time
from typing import Any, Dict, List, Optional

import aiohttp
import discord


logger = logging.getLogger("rq.roll_watcher")


def _safe_int(v: Any) -> Optional[int]:
    try:
        return int(v)
    except Exception:
        return None


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
        # 1) In-memory getter (set by Listen/buttons), 2) Redis canonical storage
        if self._channel_id_getter:
            try:
                cid = self._channel_id_getter()
                if cid:
                    return _safe_int(cid)
            except Exception:
                pass
        # Redis is the canonical storage (persists across restarts)
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

    def _format_embed(self, ev: Dict[str, Any]) -> discord.Embed:
        character = ev.get("character_name") or "Unknown"
        notation = ev.get("notation") or f'{ev.get("dice_count","?")}d{ev.get("sides","?")}'
        rolls = ev.get("rolls") or []
        total = ev.get("grand_total")
        roll_type = ev.get("roll_type") or "roll"
        visibility = ev.get("visibility") or "public"
        ctx = (ev.get("context") or "").strip()

        # Nat 20 / Nat 1 flair (single d20)
        nat = None
        try:
            if int(ev.get("sides") or 0) == 20 and int(ev.get("dice_count") or 0) == 1 and isinstance(rolls, list) and rolls:
                if int(rolls[0]) == 20:
                    nat = "nat20"
                elif int(rolls[0]) == 1:
                    nat = "nat1"
        except Exception:
            pass

        title = "🎲 Roll"
        if nat == "nat20":
            title = "🎲✨ Natural 20!"
        elif nat == "nat1":
            title = "🎲💀 Natural 1!"

        embed = discord.Embed(title=title, color=0x9b59b6)
        embed.add_field(name="Character", value=str(character), inline=True)
        embed.add_field(name="Type", value=str(roll_type), inline=True)
        embed.add_field(name="Notation", value=str(notation), inline=False)

        # Rolls detail
        try:
            rolls_str = ", ".join(str(x) for x in rolls) if isinstance(rolls, list) else str(rolls)
        except Exception:
            rolls_str = str(rolls)
        embed.add_field(name="Dice", value=f"[{rolls_str}]", inline=True)
        embed.add_field(name="Total", value=str(total if total is not None else "?"), inline=True)
        embed.add_field(name="Visibility", value=str(visibility), inline=True)

        if ctx:
            embed.add_field(name="Context", value=ctx[:1024], inline=False)

        ts = ev.get("created_at") or ""
        if ts:
            embed.set_footer(text=f"{ts} • Campaign: {ev.get('campaign_id','')}")
        return embed

    async def _announce(self, channel_id: int, events: List[Dict[str, Any]]):
        channel = self.bot.get_channel(channel_id)
        if channel is None:
            try:
                channel = await self.bot.fetch_channel(channel_id)
            except Exception:
                return

        # Post in chronological order
        for ev in events:
            try:
                await channel.send(embed=self._format_embed(ev))
            except Exception as e:
                logger.debug(f"send failed: {e}")

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
                await asyncio.sleep(self.poll_interval)
                continue

            last_epoch = self._get_last_seen_epoch()
            rolls = await self._fetch_rolls()

            # Identify new events by epoch timestamp
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
                # Sort ascending by created_at_epoch to preserve order
                new_events.sort(key=lambda x: float(x.get("created_at_epoch") or 0.0))
                await self._announce(channel_id, new_events)
                self._set_last_seen(newest_epoch, newest_id)

            await asyncio.sleep(self.poll_interval)