import discord
from discord import app_commands
from discord.ext import commands

SOUND_ID = 1453003890654969926


class SoundCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="julian", description="Play a soundboard effect in your voice channel")
    async def sound(self, interaction: discord.Interaction) -> None:
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message(
                "You need to be in a voice channel.", ephemeral=True
            )
            return

        voice_channel = interaction.user.voice.channel

        route = discord.http.Route(
            "POST",
            "/channels/{channel_id}/send-soundboard-sound",
            channel_id=voice_channel.id,
        )
        await self.bot.http.request(
            route,
            json={
                "sound_id": str(SOUND_ID),
                "source_guild_id": str(interaction.guild_id),
            },
        )
        await interaction.response.send_message("🔊", ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(SoundCog(bot))
