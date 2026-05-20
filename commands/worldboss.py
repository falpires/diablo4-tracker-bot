import discord
from discord import app_commands
from discord.ext import commands

from api.diablo4life import fetch_events, fetch_report_history
from maps.generator import generate_boss_map
from maps.zones import ZONE_NAME_TO_ID
from utils.formatters import worldboss_embed

# Known spawn zones per boss (cycles through these 3 deterministically)
BOSS_ZONES: dict[str, list[str]] = {
    "Ashava the Pestilent": ["Fractured Peaks", "Scosglen", "Kehjistan"],
    "Wandering Death, Death Given Life": ["Scosglen", "Hawezar", "Fractured Peaks"],
    "Avarice, the Gold Cursed": ["Hawezar", "Kehjistan", "Scosglen"],
}


def _guess_zone(boss_name: str, report_location: str | None) -> str | None:
    """Best-effort zone from community report or known spawn list."""
    if report_location:
        for zone in ZONE_NAME_TO_ID:
            if zone.lower() in report_location.lower():
                return zone
    # Fall back to first known zone for this boss
    zones = BOSS_ZONES.get(boss_name)
    return zones[0] if zones else None


class WorldBossCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="worldboss", description="Current World Boss status and spawn map")
    async def worldboss(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        data = await fetch_events()
        embed = worldboss_embed(data)

        boss_name = data.get("worldBoss", {}).get("name", "")
        boss_ts = data.get("worldBoss", {}).get("time", 0)

        # Try to get zone from most recent community report
        report_location = None
        try:
            reports = await fetch_report_history("worldBoss")
            if reports:
                # Match report closest to current boss spawn time (within 30 min)
                for r in reports:
                    if abs(r.get("spawnTime", 0) - boss_ts) < 30 * 60 * 1000:
                        report_location = r.get("location")
                        break
        except Exception:
            pass

        zone = _guess_zone(boss_name, report_location)
        possible_zones = BOSS_ZONES.get(boss_name, [])

        if possible_zones and not report_location:
            embed.add_field(
                name="Possible Locations",
                value=" · ".join(possible_zones),
                inline=False,
            )

        map_buf = generate_boss_map(zone)
        if map_buf:
            file = discord.File(map_buf, filename="boss_map.png")
            embed.set_image(url="attachment://boss_map.png")
            await interaction.followup.send(embed=embed, file=file)
        else:
            await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(WorldBossCog(bot))
