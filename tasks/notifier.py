import asyncio
import logging
import time
from datetime import datetime

import discord
from discord.ext import commands, tasks

from api.diablo4life import fetch_events
from api.firebase import fetch_world_boss_firebase
from commands.subscribe import get_channel_entries, get_last_message, set_last_message
from commands.worldboss import _parse_world_boss, _full_boss_name
from maps.zones import ZONE_ID_TO_NAME
from utils.formatters import dt, dt_time, HELLTIDE_DURATION_MS

log = logging.getLogger("diablo-bot.notifier")

ALERT_WINDOW_MS = 15 * 60 * 1000   # notify when this many ms remain until spawn
CHECK_TOLERANCE_MS = 90 * 1000     # fire if within ±90s of the 15-min mark


def _in_alert_window(spawn_ms: int, now_ms: int) -> bool:
    remaining = spawn_ms - now_ms
    return ALERT_WINDOW_MS - CHECK_TOLERANCE_MS <= remaining <= ALERT_WINDOW_MS + CHECK_TOLERANCE_MS


class NotifierCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._notified: set[tuple[str, int]] = set()
        self.check_loop.start()

    def cog_unload(self) -> None:
        self.check_loop.cancel()

    @tasks.loop(seconds=60)
    async def check_loop(self) -> None:
        try:
            await self._check_all()
        except Exception as e:
            log.exception("Notifier check failed: %s", e)

    @check_loop.before_loop
    async def before_check_loop(self) -> None:
        await self.bot.wait_until_ready()

    async def _check_all(self) -> None:
        now_ms = int(time.time() * 1000)

        fb_boss, data = await asyncio.gather(
            fetch_world_boss_firebase(),
            fetch_events(),
            return_exceptions=True,
        )

        await asyncio.gather(
            self._check_helltide(data, now_ms),
            self._check_worldboss(fb_boss, data, now_ms),
            self._check_legion(data, now_ms),
        )

        # Prune notified set — drop entries older than 2h
        cutoff = now_ms - 2 * 60 * 60 * 1000
        self._notified = {k for k in self._notified if k[1] > cutoff}

    async def _check_helltide(self, data, now_ms: int) -> None:
        # Use diablo4.life next-spawn time — Firebase startTime only updates after spawn starts
        if isinstance(data, Exception) or not data:
            return
        spawn_ms = data.get("helltide", {}).get("time", 0) if isinstance(data, dict) else 0
        if not spawn_ms or not _in_alert_window(spawn_ms, now_ms):
            return
        key = ("helltide", spawn_ms)
        if key in self._notified:
            return
        self._notified.add(key)

        from maps.zones import get_helltide_zone
        zone = get_helltide_zone(spawn_ms)
        embed = discord.Embed(
            title="🔥 Helltide Alert",
            description=f"Spawning {dt(spawn_ms)} ({dt_time(spawn_ms)})\n**Zone:** {zone}",
            color=discord.Color.from_rgb(180, 30, 30),
        )
        await self._broadcast("helltide", embed)

    async def _check_worldboss(self, fb, data, now_ms: int) -> None:
        if isinstance(fb, Exception) or not fb:
            return
        if isinstance(data, Exception):
            data = {}
        d4_wb = data.get("worldBoss", {}) if isinstance(data, dict) else {}
        pairs, spawn_ms, _ = _parse_world_boss(fb, d4_wb)
        if not spawn_ms or not _in_alert_window(spawn_ms, now_ms):
            return
        key = ("worldboss", spawn_ms)
        if key in self._notified:
            return
        self._notified.add(key)

        spawns_str = "\n".join(f"**{boss}** — {zone}" for zone, boss in pairs) if pairs else "Unknown"
        embed = discord.Embed(
            title="👹 World Boss Alert",
            description=f"Spawning {dt(spawn_ms)} ({dt_time(spawn_ms)})\n{spawns_str}",
            color=discord.Color.from_rgb(160, 0, 160),
        )
        await self._broadcast("worldboss", embed)

    async def _check_legion(self, data, now_ms: int) -> None:
        if isinstance(data, Exception) or not data:
            return
        ze = data.get("zoneEvent", {}) if isinstance(data, dict) else {}
        spawn_ms = ze.get("time", 0)
        if not spawn_ms or not _in_alert_window(spawn_ms, now_ms):
            return
        key = ("legion", spawn_ms)
        if key in self._notified:
            return
        self._notified.add(key)

        embed = discord.Embed(
            title="⚔️ Legion Alert",
            description=f"Spawning {dt(spawn_ms)} ({dt_time(spawn_ms)})",
            color=discord.Color.from_rgb(30, 100, 200),
        )
        await self._broadcast("legion", embed)

    async def _broadcast(self, event_type: str, embed: discord.Embed) -> None:
        for channel_id, custom_message in get_channel_entries(event_type):
            channel = self.bot.get_channel(channel_id)
            if not channel or not isinstance(channel, discord.TextChannel):
                continue
            # Delete previous alert for this event in this channel
            prev_msg_id = get_last_message(event_type, channel_id)
            if prev_msg_id:
                try:
                    prev_msg = await channel.fetch_message(prev_msg_id)
                    await prev_msg.delete()
                except (discord.NotFound, discord.Forbidden):
                    pass
            try:
                msg = await channel.send(content=custom_message, embed=embed)
                set_last_message(event_type, channel_id, msg.id)
            except discord.Forbidden:
                log.warning("No permission to send to channel %d", channel_id)
            except Exception as e:
                log.warning("Failed to send to channel %d: %s", channel_id, e)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(NotifierCog(bot))
