import json
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands

SUBS_FILE = Path(__file__).parent.parent / "subscriptions.json"
ALL_EVENTS = ["helltide", "worldboss", "legion"]

EVENT_CHOICES = [
    app_commands.Choice(name="Helltide", value="helltide"),
    app_commands.Choice(name="World Boss", value="worldboss"),
    app_commands.Choice(name="Legion", value="legion"),
    app_commands.Choice(name="All", value="all"),
]


def _load() -> dict:
    if SUBS_FILE.exists():
        return json.loads(SUBS_FILE.read_text())
    return {"subscriptions": {e: [] for e in ALL_EVENTS}, "last_messages": {}}


def _save(data: dict) -> None:
    SUBS_FILE.write_text(json.dumps(data, indent=2))


def get_channels(event_type: str) -> list[int]:
    return _load()["subscriptions"].get(event_type, [])


def get_last_message(event_type: str, channel_id: int) -> int | None:
    data = _load()
    return data.get("last_messages", {}).get(f"{event_type}:{channel_id}")


def set_last_message(event_type: str, channel_id: int, message_id: int) -> None:
    data = _load()
    if "last_messages" not in data:
        data["last_messages"] = {}
    data["last_messages"][f"{event_type}:{channel_id}"] = message_id
    _save(data)


def add_subscription(channel_id: int, event_type: str) -> None:
    data = _load()
    subs = data.setdefault("subscriptions", {e: [] for e in ALL_EVENTS})
    if event_type not in subs:
        subs[event_type] = []
    if channel_id not in subs[event_type]:
        subs[event_type].append(channel_id)
    _save(data)


def remove_subscription(channel_id: int, event_type: str) -> None:
    data = _load()
    subs = data.get("subscriptions", {})
    if event_type in subs:
        subs[event_type] = [c for c in subs[event_type] if c != channel_id]
    _save(data)


def list_subscriptions(channel_id: int) -> list[str]:
    data = _load()
    subs = data.get("subscriptions", {})
    return [e for e, channels in subs.items() if channel_id in channels]


class SubscribeCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="subscribe", description="Subscribe this channel to 15-min spawn alerts")
    @app_commands.describe(event="Event type to subscribe to")
    @app_commands.choices(event=EVENT_CHOICES)
    @app_commands.default_permissions(manage_channels=True)
    async def subscribe(self, interaction: discord.Interaction, event: str = "all") -> None:
        targets = ALL_EVENTS if event == "all" else [event]
        for t in targets:
            add_subscription(interaction.channel_id, t)
        names = ", ".join(t.capitalize() for t in targets)
        await interaction.response.send_message(
            f"✅ This channel will receive **{names}** alerts 15 min before spawn.",
            ephemeral=True,
        )

    @app_commands.command(name="unsubscribe", description="Remove spawn alerts from this channel")
    @app_commands.describe(event="Event type to unsubscribe from")
    @app_commands.choices(event=EVENT_CHOICES)
    @app_commands.default_permissions(manage_channels=True)
    async def unsubscribe(self, interaction: discord.Interaction, event: str = "all") -> None:
        targets = ALL_EVENTS if event == "all" else [event]
        for t in targets:
            remove_subscription(interaction.channel_id, t)
        names = ", ".join(t.capitalize() for t in targets)
        await interaction.response.send_message(
            f"🔕 Removed **{names}** alerts from this channel.",
            ephemeral=True,
        )

    @app_commands.command(name="subscriptions", description="List active alerts in this channel")
    async def subscriptions(self, interaction: discord.Interaction) -> None:
        subs = list_subscriptions(interaction.channel_id)
        if subs:
            names = ", ".join(s.capitalize() for s in sorted(subs))
            await interaction.response.send_message(f"Active alerts: **{names}**", ephemeral=True)
        else:
            await interaction.response.send_message("No active alerts in this channel.", ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(SubscribeCog(bot))
