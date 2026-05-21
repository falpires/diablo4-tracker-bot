import asyncio

import discord
from discord import app_commands
from discord.ext import commands

from pathlib import Path

from api.diablo4life import fetch_events
from api.firebase import fetch_world_boss_firebase
from constants import BOSS_WINDOW_MS
from utils.formatters import worldboss_embed, parse_api_timestamp

_BOSS_ICON = Path(__file__).parent.parent / "maps" / "assets" / "World-Boss.png"


def _parse_world_boss(fb: dict, d4life: dict) -> tuple[list[tuple[str, str]], int, int]:
    """Return (zone_boss_pairs, spawn_ms, next_spawn_ms).
    zone_boss_pairs: list of (zone_name, boss_full_name) — one entry per spawning boss.
    """
    start_raw = fb.get("startTime") or fb.get("id")
    next_raw = fb.get("nextTime")
    spawn_ms = parse_api_timestamp(start_raw)
    next_spawn_ms = parse_api_timestamp(next_raw) if next_raw else spawn_ms + 12600 * 1000

    fb_zones = fb.get("zone", [])
    main_boss = fb.get("boss", "")
    if fb_zones:
        # Filter to zones matching the top-level boss — Firebase now reports concurrent bosses
        pairs = [
            (z["name"], _full_boss_name(z.get("boss", "")))
            for z in fb_zones if z.get("name") and z.get("boss") == main_boss
        ]
        if not pairs:
            pairs = [(z["name"], _full_boss_name(z.get("boss", ""))) for z in fb_zones if z.get("name")]
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
    @app_commands.checks.cooldown(1, 10.0, key=lambda i: (i.guild_id, i.user.id))
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

        if not fb and not data:
            await interaction.followup.send("⚠️ Unable to fetch World Boss data. Try again shortly.", ephemeral=True)
            return

        d4_wb = data.get("worldBoss", {}) if isinstance(data, dict) else {}
        pairs, spawn_ms, next_spawn_ms = _parse_world_boss(fb, d4_wb)

        embed = worldboss_embed(pairs, spawn_ms, next_spawn_ms)

        if _BOSS_ICON.exists():
            file = discord.File(str(_BOSS_ICON), filename="boss.png")
            embed.set_thumbnail(url="attachment://boss.png")
            await interaction.followup.send(embed=embed, file=file)
        else:
            await interaction.followup.send(embed=embed)

    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError) -> None:
        if isinstance(error, app_commands.CommandOnCooldown):
            await interaction.response.send_message(
                f"Slow down! Try again in {error.retry_after:.0f}s.", ephemeral=True
            )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(WorldBossCog(bot))
