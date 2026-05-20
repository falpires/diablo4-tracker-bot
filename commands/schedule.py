import time
import discord
from discord import app_commands
from discord.ext import commands

from api.diablo4life import fetch_events
from maps.zones import HELLTIDE_CYCLE_MS, HELLTIDE_ROTATION, HELLTIDE_ANCHOR_MS, HELLTIDE_ANCHOR_INDEX
from utils.formatters import time_until

# Event durations in ms
HELLTIDE_DURATION_MS = 55 * 60 * 1000
BOSS_INTERVAL_MS = 210 * 60 * 1000  # ~3.5h
LEGION_INTERVAL_MS = 25 * 60 * 1000


def _helltide_schedule(from_ms: int, count: int = 8) -> list[tuple[int, str]]:
    """Return next `count` helltide spawn times with zone names."""
    cycles = (from_ms - HELLTIDE_ANCHOR_MS) // HELLTIDE_CYCLE_MS
    # Find next spawn at or after from_ms
    next_spawn = HELLTIDE_ANCHOR_MS + (cycles + 1) * HELLTIDE_CYCLE_MS
    results = []
    for i in range(count):
        ts = next_spawn + i * HELLTIDE_CYCLE_MS
        idx = (HELLTIDE_ANCHOR_INDEX + int((ts - HELLTIDE_ANCHOR_MS) // HELLTIDE_CYCLE_MS)) % len(HELLTIDE_ROTATION)
        results.append((ts, HELLTIDE_ROTATION[idx]))
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
    async def schedule(
        self, interaction: discord.Interaction, event: str = "all"
    ) -> None:
        await interaction.response.defer()
        data = await fetch_events()
        now_ms = int(time.time() * 1000)

        embed = discord.Embed(
            title="📅 Event Schedule",
            color=discord.Color.from_rgb(60, 30, 80),
        )

        if event in ("all", "helltide"):
            upcoming = _helltide_schedule(now_ms, count=4)
            lines = []
            for ts, zone in upcoming:
                lines.append(f"`{time_until(ts):>8}` — {zone}")
            embed.add_field(
                name="🔥 Helltide",
                value="\n".join(lines) or "No data",
                inline=False,
            )

        if event in ("all", "worldboss"):
            boss = data.get("worldBoss", {})
            next_boss = data.get("nextWorldBoss", {})
            lines = []
            if boss.get("time"):
                lines.append(f"`{time_until(boss['time']):>8}` — {boss.get('name', '?')}")
            if next_boss.get("time") and next_boss.get("time") != boss.get("time"):
                lines.append(f"`{time_until(next_boss['time']):>8}` — {next_boss.get('name', '?')}")
            embed.add_field(
                name="👹 World Boss",
                value="\n".join(lines) or "No data",
                inline=False,
            )

        if event in ("all", "legion"):
            ze = data.get("zoneEvent", {})
            ts = ze.get("time", 0)
            lines = []
            if ts:
                lines.append(f"`{time_until(ts):>8}`")
                next_ts = ts + LEGION_INTERVAL_MS
                lines.append(f"`{time_until(next_ts):>8}`")
            embed.add_field(
                name="⚔️ Legion",
                value="\n".join(lines) or "No data",
                inline=False,
            )

        embed.set_footer(text="diablo4.life")
        await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ScheduleCog(bot))
