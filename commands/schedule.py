import asyncio
import time
from datetime import datetime

import discord
from discord import app_commands
from discord.ext import commands

from api.diablo4life import fetch_events
from api.firebase import fetch_helltide_a, fetch_world_boss_firebase
from maps.zones import HELLTIDE_CYCLE_MS, HELLTIDE_ROTATION, HELLTIDE_ANCHOR_MS, HELLTIDE_ANCHOR_INDEX
from utils.formatters import dt, dt_time, is_active, HELLTIDE_DURATION_MS

LEGION_INTERVAL_MS = 25 * 60 * 1000
EXPANSION_ZONES = {"Nahantu", "Skovos"}


def _parse_firebase(fb: dict) -> tuple[int, int, str | None]:
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


def _helltide_future_zones(anchor_spawn_ms: int, count: int = 3) -> list[tuple[int, str]]:
    """Given the confirmed current spawn_ms, return next `count` spawns with zones."""
    results = []
    for i in range(1, count + 1):
        spawn_ms = anchor_spawn_ms + i * HELLTIDE_CYCLE_MS
        cycles = int((spawn_ms - HELLTIDE_ANCHOR_MS) // HELLTIDE_CYCLE_MS)
        idx = (HELLTIDE_ANCHOR_INDEX + cycles) % len(HELLTIDE_ROTATION)
        results.append((spawn_ms, HELLTIDE_ROTATION[idx]))
    return results


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

        fb, fb_boss, data = await asyncio.gather(
            fetch_helltide_a(),
            fetch_world_boss_firebase(),
            fetch_events(),
            return_exceptions=True,
        )
        if isinstance(fb, Exception):
            fb = None
        if isinstance(fb_boss, Exception):
            fb_boss = None
        if isinstance(data, Exception):
            data = {}

        now_ms = int(time.time() * 1000)
        embed = discord.Embed(title="📅 Event Schedule", color=discord.Color.from_rgb(60, 30, 80))

        if event in ("all", "helltide"):
            lines = []

            if fb and isinstance(fb, dict):
                start_ms, end_ms, zone = _parse_firebase(fb)
                active = start_ms <= now_ms <= end_ms
                zone_label = zone.title() if zone else "Unknown"
                suffix = " *(+base)*" if zone and zone.lower() in {z.lower() for z in EXPANSION_ZONES} else ""
                prefix = "**🔴 NOW**" if active else dt(start_ms)
                lines.append(f"{prefix} {dt_time(start_ms)} — {zone_label}{suffix}")

                # Future spawns from deterministic rotation
                for spawn_ms, next_zone in _helltide_future_zones(start_ms, count=3):
                    next_suffix = " *(+base)*" if next_zone in EXPANSION_ZONES else ""
                    lines.append(f"{dt(spawn_ms)} {dt_time(spawn_ms)} — {next_zone}{next_suffix}")
            else:
                # Fallback to diablo4.life
                api_next_ms = data.get("helltide", {}).get("time", 0) if isinstance(data, dict) else 0
                if api_next_ms:
                    prev_ms = api_next_ms - HELLTIDE_CYCLE_MS
                    base_ms = prev_ms if is_active(prev_ms, HELLTIDE_DURATION_MS) else api_next_ms
                    for i in range(4):
                        spawn_ms = base_ms + i * HELLTIDE_CYCLE_MS
                        cycles = int((spawn_ms - HELLTIDE_ANCHOR_MS) // HELLTIDE_CYCLE_MS)
                        idx = (HELLTIDE_ANCHOR_INDEX + cycles) % len(HELLTIDE_ROTATION)
                        zone = HELLTIDE_ROTATION[idx]
                        active = is_active(spawn_ms, HELLTIDE_DURATION_MS)
                        suffix = " *(+base)*" if zone in EXPANSION_ZONES else ""
                        prefix = "**🔴 NOW**" if active else dt(spawn_ms)
                        lines.append(f"{prefix} {dt_time(spawn_ms)} — {zone}{suffix}")

            embed.add_field(name="🔥 Helltide", value="\n".join(lines) or "No data", inline=False)

        if event in ("all", "worldboss"):
            if fb_boss and isinstance(fb_boss, dict):
                from commands.worldboss import _parse_world_boss
                d4_wb = data.get("worldBoss", {}) if isinstance(data, dict) else {}
                pairs, spawn_ms, next_spawn_ms = _parse_world_boss(fb_boss, d4_wb)
                spawns_str = " / ".join(f"{boss} ({zone})" for zone, boss in pairs) if pairs else "Unknown"
                if is_active(spawn_ms, 15 * 60 * 1000):
                    val = f"**🟣 ALIVE** {dt_time(spawn_ms)} — {spawns_str}"
                else:
                    val = f"{dt(spawn_ms)} {dt_time(spawn_ms)} — {spawns_str}"
            else:
                val = "No data"
            embed.add_field(name="👹 World Boss", value=val, inline=False)

        if event in ("all", "legion"):
            ze = data.get("zoneEvent", {}) if isinstance(data, dict) else {}
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
