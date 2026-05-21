import time

import discord
from discord import app_commands
from discord.ext import commands

from api.diablo4life import fetch_events
from api.firebase import fetch_helltide_a
from commands.subscribe import get_channel_entries, ALL_EVENTS

_start_time = time.monotonic()


class StatusCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="status", description="Bot health: uptime, latency, API status, subscriptions")
    async def status(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)

        uptime_s = int(time.monotonic() - _start_time)
        h, rem = divmod(uptime_s, 3600)
        m, s = divmod(rem, 60)
        uptime_str = f"{h}h {m}m {s}s"

        d4_ok = True
        fb_ok = True
        try:
            await fetch_events()
        except Exception:
            d4_ok = False
        try:
            await fetch_helltide_a()
        except Exception:
            fb_ok = False

        sub_lines = [
            f"{event.capitalize()}: {len(get_channel_entries(event))}"
            for event in ALL_EVENTS
        ]

        embed = discord.Embed(title="🤖 Bot Status", color=discord.Color.blurple())
        embed.add_field(name="Uptime", value=uptime_str, inline=True)
        embed.add_field(name="Latency", value=f"{self.bot.latency * 1000:.0f}ms", inline=True)
        embed.add_field(
            name="APIs",
            value=f"diablo4.life: {'✅' if d4_ok else '❌'}\nhelltides.com: {'✅' if fb_ok else '❌'}",
            inline=True,
        )
        embed.add_field(name="Subscriptions", value="\n".join(sub_lines), inline=False)
        await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(StatusCog(bot))
