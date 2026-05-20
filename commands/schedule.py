import asyncio
import time
from datetime import datetime

import discord
from discord import app_commands
from discord.ext import commands

from api.diablo4life import fetch_events
from api.firebase import fetch_helltide_a
from maps.zones import HELLTIDE_CYCLE_MS, HELLTIDE_ROTATION, HELLTIDE_ANCHOR_MS, HELLTIDE_ANCHOR_INDEX, get_boss_spawn, BOSS_INTERVAL_MS
from utils.formatters import dt, dt_time, ts, is_active, HELLTIDE_DURATION_MS

LEGION_INTERVAL_MS = 25 * 60 * 1000


def _helltide_schedule(api_next_ms: int, count: int = 4) -> list[tuple[int, str, bool]]:
    """Return (spawn_ms, zone, active) tuples for Helltide B rotation."""
    prev_ms = api_next_ms - HELLTIDE_CYCLE_MS
    base_ms = prev_ms if is_active(prev_ms, HELLTIDE_DURATION_MS) else api_next_ms

    results = []
    for i in range(count):
        spawn_ms = base_ms + i * HELLTIDE_CYCLE_MS
        cycles = int((spawn_ms - HELLTIDE_ANCHOR_MS) // HELLTIDE_CYCLE_MS)
        idx = (HELLTIDE_ANCHOR_INDEX + cycles) % len(HELLTIDE_ROTATION)
        active = is_active(spawn_ms, HELLTIDE_DURATION_MS)
        results.append((spawn_ms, HELLTIDE_ROTATION[idx], active))
    return results


def _parse_firebase_helltide(fb: dict) -> tuple[int, int, str | None]:
    zone = fb.get("zone")
    start_raw = fb.get("startTime") or fb.get("id")
    end_raw = fb.get("endTime")
    if isinstance(start_raw, str):
        start_ms = int(datetime.fromisoformat(start_raw.replace("Z", "+00:00")).timestamp() * 1000)
    else:
        start_ms = int(start_raw) * 1000 if start_raw else 0
    if isinstance(end_raw, str):
        end_ms = int(datetime.fromisoformat(end_raw.replace("Z", "+00:00")).timestamp() * 1000)
    else:
        end_ms = start_ms + HELLTIDE_DURATION_MS
    return start_ms, end_ms, zone


class ScheduleCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="schedule", description="Upcoming event schedule (~3 hours)")
    @app_commands.describe(event="Filter by event type")
    @app_commands.choices(event=[
        app_commands.Choice(name="All", value="all"),
        app_commands.Choice(name="Helltide", value="helltide"),
        app_commands.Choice(name="World Boss", value="worldboss"),
        app_commands.Choice(name="Legion", value="legion"),
    ])
    async def schedule(self, interaction: discord.Interaction, event: str = "all") -> None:
        await interaction.response.defer()

        data, fb = await asyncio.gather(
            fetch_events(),
            fetch_helltide_a(),
            return_exceptions=True,
        )
        if isinstance(data, Exception):
            data = {}
        if isinstance(fb, Exception):
            fb = None

        now_ms = int(time.time() * 1000)

        embed = discord.Embed(title="📅 Event Schedule", color=discord.Color.from_rgb(60, 30, 80))

        if event in ("all", "helltide"):
            lines = []

            # Helltide A from Firebase (spawns :00 UTC)
            if fb and isinstance(fb, dict):
                ht_a_start_ms, ht_a_end_ms, ht_a_zone = _parse_firebase_helltide(fb)
                ht_a_active = ht_a_start_ms <= now_ms <= ht_a_end_ms
                prefix = "**🔴 NOW**" if ht_a_active else dt(ht_a_start_ms)
                zone_label = ht_a_zone or "Unknown"
                suffix = " *(+base)*" if zone_label in ("Nahantu", "Skovos") else ""
                lines.append(f"A: {prefix} {dt_time(ht_a_start_ms)} — {zone_label}{suffix}")

                # Next A spawn
                next_a_ms = ht_a_start_ms + HELLTIDE_CYCLE_MS
                next_a_cycles = int((next_a_ms - HELLTIDE_ANCHOR_MS) // HELLTIDE_CYCLE_MS)
                next_a_idx = (HELLTIDE_ANCHOR_INDEX + next_a_cycles) % len(HELLTIDE_ROTATION)
                next_a_zone = HELLTIDE_ROTATION[next_a_idx]
                next_a_suffix = " *(+base)*" if next_a_zone in ("Nahantu", "Skovos") else ""
                lines.append(f"A: {dt(next_a_ms)} {dt_time(next_a_ms)} — {next_a_zone}{next_a_suffix}")

            # Helltide B from diablo4.life (spawns :55 UTC)
            api_next_ms = data.get("helltide", {}).get("time", 0) if isinstance(data, dict) else 0
            if api_next_ms:
                for spawn_ms, zone, active in _helltide_schedule(api_next_ms, count=3):
                    prefix = "**🔴 NOW**" if active else dt(spawn_ms)
                    suffix = " *(+base)*" if zone in ("Nahantu", "Skovos") else ""
                    lines.append(f"B: {prefix} {dt_time(spawn_ms)} — {zone}{suffix}")

            embed.add_field(name="🔥 Helltide", value="\n".join(lines) or "No data", inline=False)

        if event in ("all", "worldboss"):
            boss, zones, spawn_ms, next_boss, next_zones, next_spawn_ms = get_boss_spawn(now_ms)
            if is_active(spawn_ms, 15 * 60 * 1000):
                val = f"**🟣 ALIVE** {dt_time(spawn_ms)} — {boss}"
            else:
                val = f"{dt(next_spawn_ms)} {dt_time(next_spawn_ms)} — {next_boss}"
            embed.add_field(name="👹 World Boss", value=val, inline=False)

        if event in ("all", "legion"):
            ze = (data.get("zoneEvent", {}) if isinstance(data, dict) else {})
            ts_ms = ze.get("time", 0)
            lines = []
            if ts_ms:
                lines.append(f"{dt(ts_ms)} {dt_time(ts_ms)}")
                next_ms = ts_ms + LEGION_INTERVAL_MS
                lines.append(f"{dt(next_ms)} {dt_time(next_ms)}")
            embed.add_field(name="⚔️ Legion", value="\n".join(lines) or "No data", inline=False)

        embed.set_footer(text="helltides.com + diablo4.life")
        await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ScheduleCog(bot))
