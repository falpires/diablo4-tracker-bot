import time
import discord


def _ms_diff(ts_ms: int) -> int:
    return int(ts_ms / 1000 - time.time())


def ts(ts_ms: int) -> int:
    """Unix seconds from milliseconds."""
    return ts_ms // 1000


def dt(ts_ms: int) -> str:
    """Discord relative timestamp — shows 'in Xm' or 'X minutes ago', user's local time."""
    return f"<t:{ts(ts_ms)}:R>"


def dt_time(ts_ms: int) -> str:
    """Discord short time — shows '9:41 PM' in user's local timezone."""
    return f"<t:{ts(ts_ms)}:t>"


def time_until(ts_ms: int) -> str:
    """Plain countdown string for non-embed contexts (e.g. schedule table)."""
    diff = _ms_diff(ts_ms)
    if diff <= 0:
        return "now"
    if diff < 60:
        return f"{diff}s"
    if diff < 3600:
        return f"{diff // 60}m {diff % 60}s"
    h, rem = divmod(diff, 3600)
    return f"{h}h {rem // 60}m"


def is_active(ts_ms: int, duration_ms: int) -> bool:
    now_ms = int(time.time() * 1000)
    return ts_ms <= now_ms <= ts_ms + duration_ms


HELLTIDE_DURATION_MS = 55 * 60 * 1000


def helltide_embed(data: dict, zone: str | None) -> discord.Embed:
    ts_ms = data.get("time", 0)
    chest_ms = data.get("chestRespawn", 0)
    active = is_active(ts_ms, HELLTIDE_DURATION_MS)

    if active:
        end_ms = ts_ms + HELLTIDE_DURATION_MS
        desc = f"**Active** — ends {dt(end_ms)} ({dt_time(end_ms)})"
        color = discord.Color.from_rgb(180, 30, 30)
    else:
        desc = f"Starts {dt(ts_ms)} ({dt_time(ts_ms)})"
        color = discord.Color.from_rgb(80, 80, 80)

    embed = discord.Embed(title="🔥 Helltide", description=desc, color=color)

    if zone:
        embed.add_field(name="Zone", value=zone, inline=True)
    if chest_ms:
        embed.add_field(
            name="Chest Respawn",
            value=f"{dt(chest_ms)} ({dt_time(chest_ms)})",
            inline=True,
        )
    embed.set_footer(text="diablo4.life")
    return embed


def worldboss_embed(data: dict) -> discord.Embed:
    boss = data.get("worldBoss", {})
    next_boss = data.get("nextWorldBoss", {})
    ts_ms = boss.get("time", 0)
    name = boss.get("name", "Unknown")
    active = is_active(ts_ms, 15 * 60 * 1000)

    if active:
        end_ms = ts_ms + 15 * 60 * 1000
        desc = f"**{name}** is **alive** — despawns {dt(end_ms)} ({dt_time(end_ms)})"
        color = discord.Color.from_rgb(160, 0, 160)
    else:
        desc = f"**{name}** spawns {dt(ts_ms)} ({dt_time(ts_ms)})"
        color = discord.Color.from_rgb(80, 80, 80)

    embed = discord.Embed(title="👹 World Boss", description=desc, color=color)

    next_name = next_boss.get("name", "")
    next_ts_ms = next_boss.get("time", 0)
    if next_name and next_ts_ms and next_ts_ms != ts_ms:
        embed.add_field(
            name="Next",
            value=f"{next_name} — {dt(next_ts_ms)} ({dt_time(next_ts_ms)})",
            inline=False,
        )

    embed.set_footer(text="diablo4.life")
    return embed


def legion_embed(data: dict) -> discord.Embed:
    zone_event = data.get("zoneEvent", {})
    ts_ms = zone_event.get("time", 0)
    active = is_active(ts_ms, 20 * 60 * 1000)

    if active:
        end_ms = ts_ms + 20 * 60 * 1000
        desc = f"**Active** — ends {dt(end_ms)} ({dt_time(end_ms)})"
        color = discord.Color.from_rgb(30, 100, 200)
    else:
        desc = f"Starts {dt(ts_ms)} ({dt_time(ts_ms)})"
        color = discord.Color.from_rgb(80, 80, 80)

    embed = discord.Embed(title="⚔️ Legion", description=desc, color=color)
    embed.set_footer(text="diablo4.life")
    return embed
