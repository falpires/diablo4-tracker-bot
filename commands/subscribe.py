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
        data = json.loads(SUBS_FILE.read_text())
        # Migrate old list[int] format to dict[str, str|None]
        subs = data.get("subscriptions", {})
        for event, val in subs.items():
            if isinstance(val, list):
                subs[event] = {str(c): None for c in val}
        return data
    return {"subscriptions": {e: {} for e in ALL_EVENTS}, "last_messages": {}}


def _save(data: dict) -> None:
    SUBS_FILE.write_text(json.dumps(data, indent=2))


def get_channel_entries(event_type: str) -> list[tuple[int, str | None]]:
    """Return (channel_id, custom_message) pairs for an event."""
    subs = _load()["subscriptions"].get(event_type, {})
    return [(int(cid), msg) for cid, msg in subs.items()]


def get_channels(event_type: str) -> list[int]:
    return [cid for cid, _ in get_channel_entries(event_type)]


def get_last_message(event_type: str, channel_id: int) -> int | None:
    return _load().get("last_messages", {}).get(f"{event_type}:{channel_id}")


def set_last_message(event_type: str, channel_id: int, message_id: int) -> None:
    data = _load()
    data.setdefault("last_messages", {})[f"{event_type}:{channel_id}"] = message_id
    _save(data)


def add_subscription(channel_id: int, event_type: str, message: str | None = None) -> None:
    data = _load()
    subs = data.setdefault("subscriptions", {e: {} for e in ALL_EVENTS})
    subs.setdefault(event_type, {})[str(channel_id)] = message
    _save(data)


def remove_subscription(channel_id: int, event_type: str) -> None:
    data = _load()
    data.get("subscriptions", {}).get(event_type, {}).pop(str(channel_id), None)
    _save(data)


def list_subscriptions(channel_id: int) -> list[tuple[str, str | None]]:
    """Return (event_type, custom_message) for each active subscription in this channel."""
    data = _load()
    subs = data.get("subscriptions", {})
    return [
        (event, entries.get(str(channel_id)))
        for event, entries in subs.items()
        if str(channel_id) in entries
    ]


class SubscribeCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="subscribe", description="Subscribe this channel to 15-min spawn alerts")
    @app_commands.describe(
        event="Event type to subscribe to",
        message="Optional message to send with the alert (e.g. @everyone or a role ping)",
    )
    @app_commands.choices(event=EVENT_CHOICES)
    @app_commands.default_permissions(manage_channels=True)
    async def subscribe(
        self,
        interaction: discord.Interaction,
        event: str = "all",
        message: str | None = None,
    ) -> None:
        targets = ALL_EVENTS if event == "all" else [event]
        for t in targets:
            add_subscription(interaction.channel_id, t, message)
        names = ", ".join(t.capitalize() for t in targets)
        suffix = f" with message: {message}" if message else ""
        await interaction.response.send_message(
            f"✅ This channel will receive **{names}** alerts 15 min before spawn{suffix}.",
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
            lines = []
            for event, msg in sorted(subs):
                line = event.capitalize()
                if msg:
                    line += f" — {msg}"
                lines.append(line)
            await interaction.response.send_message("\n".join(lines), ephemeral=True)
        else:
            await interaction.response.send_message("No active alerts in this channel.", ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(SubscribeCog(bot))
