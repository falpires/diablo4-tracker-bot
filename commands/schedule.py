import time
import discord
from discord import app_commands
from discord.ext import commands

from api.diablo4life import fetch_events
from maps.zones import HELLTIDE_CYCLE_MS, HELLTIDE_ROTATION, HELLTIDE_ANCHOR_MS, HELLTIDE_ANCHOR_INDEX
from utils.formatters import dt, dt_time, ts

LEGION_INTERVAL_MS = 25 * 60 * 1000


def _helltide_schedule(from_ms: int, count: int = 4) -> list[tuple[int, str]]:
    cycles = (from_ms - HELLTIDE_ANCHOR_MS) // HELLTIDE_CYCLE_MS
    next_spawn = HELLTIDE_ANCHOR_MS + (cycles + 1) * HELLTIDE_CYCLE_MS
    results = []
    for i in range(count):
        spawn_ms = next_spawn + i * HELLTIDE_CYCLE_MS
        idx = (HELLTIDE_ANCHOR_INDEX + int((spawn_ms - HELLTIDE_ANCHOR_MS) // HELLTIDE_CYCLE_MS)) % len(HELLTIDE_ROTATION)
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
        data = await fetch_events()
        now_ms = int(time.time() * 1000)

        embed = discord.Embed(title="📅 Event Schedule", color=discord.Color.from_rgb(60, 30, 80))

        if event in ("all", "helltide"):
            lines = [
                f"{dt(spawn_ms)} {dt_time(spawn_ms)} — {zone}"
                for spawn_ms, zone in _helltide_schedule(now_ms)
            ]
            embed.add_field(name="🔥 Helltide", value="\n".join(lines) or "No data", inline=False)

        if event in ("all", "worldboss"):
            boss = data.get("worldBoss", {})
            next_boss = data.get("nextWorldBoss", {})
            lines = []
            if boss.get("time"):
                lines.append(f"{dt(boss['time'])} {dt_time(boss['time'])} — {boss.get('name', '?')}")
            if next_boss.get("time") and next_boss.get("time") != boss.get("time"):
                lines.append(f"{dt(next_boss['time'])} {dt_time(next_boss['time'])} — {next_boss.get('name', '?')}")
            embed.add_field(name="👹 World Boss", value="\n".join(lines) or "No data", inline=False)

        if event in ("all", "legion"):
            ze = data.get("zoneEvent", {})
            ts_ms = ze.get("time", 0)
            lines = []
            if ts_ms:
                lines.append(f"{dt(ts_ms)} {dt_time(ts_ms)}")
                next_ms = ts_ms + LEGION_INTERVAL_MS
                lines.append(f"{dt(next_ms)} {dt_time(next_ms)}")
            embed.add_field(name="⚔️ Legion", value="\n".join(lines) or "No data", inline=False)

        embed.set_footer(text="diablo4.life")
        await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ScheduleCog(bot))
