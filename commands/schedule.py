import time
import discord
from discord import app_commands
from discord.ext import commands

from api.diablo4life import fetch_events
from maps.zones import HELLTIDE_CYCLE_MS, HELLTIDE_ROTATION, HELLTIDE_ANCHOR_MS, HELLTIDE_ANCHOR_INDEX, get_boss_spawn, BOSS_INTERVAL_MS
from utils.formatters import dt, dt_time, ts, is_active, HELLTIDE_DURATION_MS

LEGION_INTERVAL_MS = 25 * 60 * 1000


def _helltide_schedule(api_next_ms: int, count: int = 4) -> list[tuple[int, str, bool]]:
    """Return (spawn_ms, zone, active) tuples starting from current or next spawn."""
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
            api_next_ms = data.get("helltide", {}).get("time", 0)
            lines = []
            for spawn_ms, zone, active in _helltide_schedule(api_next_ms or now_ms):
                prefix = "**🔴 NOW**" if active else dt(spawn_ms)
                suffix = " *(+base)*" if zone in ("Nahantu", "Skovos") else ""
                lines.append(f"{prefix} {dt_time(spawn_ms)} — {zone}{suffix}")
            embed.add_field(name="🔥 Helltide", value="\n".join(lines) or "No data", inline=False)

        if event in ("all", "worldboss"):
            boss, zones, spawn_ms, next_boss, next_zones, next_spawn_ms = get_boss_spawn(now_ms)
            from utils.formatters import is_active
            lines = []
            if is_active(spawn_ms, 15 * 60 * 1000):
                lines.append(f"**🟣 ALIVE** {dt_time(spawn_ms)} — {boss}")
            else:
                lines.append(f"{dt(spawn_ms)} {dt_time(spawn_ms)} — {boss}")
            lines.append(f"{dt(next_spawn_ms)} {dt_time(next_spawn_ms)} — {next_boss}")
            embed.add_field(name="👹 World Boss", value="\n".join(lines), inline=False)

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
