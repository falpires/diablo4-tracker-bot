import asyncio
import time
from datetime import datetime

import discord
from discord import app_commands
from discord.ext import commands

from api.diablo4life import fetch_events
from api.firebase import fetch_world_boss_firebase
from maps.generator import generate_boss_map
from utils.formatters import worldboss_embed, is_active

BOSS_WINDOW_MS = 15 * 60 * 1000


def _parse_world_boss(fb: dict, d4life: dict) -> tuple[list[tuple[str, str]], int, int]:
    """Return (zone_boss_pairs, spawn_ms, next_spawn_ms).
    zone_boss_pairs: list of (zone_name, boss_full_name) — one entry per spawning boss.
    """
    start_raw = fb.get("startTime") or fb.get("id")
    next_raw = fb.get("nextTime")

    if isinstance(start_raw, str):
        spawn_ms = int(datetime.fromisoformat(start_raw.replace("Z", "+00:00")).timestamp() * 1000)
    else:
        spawn_ms = int(start_raw) * 1000 if start_raw else 0

    if isinstance(next_raw, str):
        next_spawn_ms = int(datetime.fromisoformat(next_raw.replace("Z", "+00:00")).timestamp() * 1000)
    else:
        next_spawn_ms = spawn_ms + 12600 * 1000

    fb_zones = fb.get("zone", [])
    if fb_zones:
        # Firebase zone list has per-zone boss info
        pairs = [
            (z["name"], _full_boss_name(z.get("boss", "")))
            for z in fb_zones if z.get("name")
        ]
    else:
        # Fallback: single entry from d4life name or Firebase top-level boss
        d4_name = d4life.get("name", "")
        d4_time = d4life.get("time", 0)
        boss_name = d4_name if (d4_name and d4_time == spawn_ms) else _full_boss_name(fb.get("boss", "Unknown"))
        pairs = [("Unknown", boss_name)]

    return pairs, spawn_ms, next_spawn_ms


def _full_boss_name(short: str) -> str:
    return {
        "Ashava": "Ashava the Pestilent",
        "Avarice": "Avarice, the Gold Cursed",
        "Wandering Death": "Wandering Death, Death Given Life",
    }.get(short, short)


class WorldBossCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="worldboss", description="Current World Boss status and spawn map")
    async def worldboss(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()

        fb, data = await asyncio.gather(
            fetch_world_boss_firebase(),
            fetch_events(),
            return_exceptions=True,
        )
        if isinstance(fb, Exception) or not fb:
            fb = {}
        if isinstance(data, Exception):
            data = {}

        d4_wb = data.get("worldBoss", {}) if isinstance(data, dict) else {}
        pairs, spawn_ms, next_spawn_ms = _parse_world_boss(fb, d4_wb)

        embed = worldboss_embed(pairs, spawn_ms, next_spawn_ms)

        map_zone = pairs[0][0] if pairs else None
        map_buf = generate_boss_map(map_zone)
        if map_buf:
            file = discord.File(map_buf, filename="boss_map.png")
            embed.set_image(url="attachment://boss_map.png")
            await interaction.followup.send(embed=embed, file=file)
        else:
            await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(WorldBossCog(bot))
