import asyncio
import logging
import discord
from discord.ext import commands

from config import DISCORD_TOKEN, GUILD_ID

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("diablo-bot")

COGS = [
    "commands.helltide",
    "commands.worldboss",
    "commands.legion",
    "commands.schedule",
    "commands.sound",
    "commands.subscribe",
    "commands.status",
    "tasks.notifier",
]


class DiabloBot(commands.Bot):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self) -> None:
        for cog in COGS:
            await self.load_extension(cog)
            log.info("Loaded cog: %s", cog)

        if GUILD_ID:
            guild = discord.Object(id=GUILD_ID)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            log.info("Synced commands to guild %d", GUILD_ID)
        else:
            await self.tree.sync()
            log.info("Synced commands globally (may take up to 1h)")

    async def on_ready(self) -> None:
        log.info("Logged in as %s (ID: %s)", self.user, self.user.id)


async def main() -> None:
    bot = DiabloBot()
    async with bot:
        await bot.start(DISCORD_TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
