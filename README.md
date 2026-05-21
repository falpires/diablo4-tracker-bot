# Diablo 4 Tracker Bot

Discord bot for tracking Diablo 4 live events — Helltide, World Boss, and Legion. Slash commands with zone maps and optional channel alerts.

> **Personal use only.** This bot is built for a private Discord server and is not intended for public use or distribution.

## Commands

| Command | Description |
|---|---|
| `/helltide` | Current Helltide status, zone, chest respawn timer, and zone map |
| `/worldboss` | Next World Boss spawn — boss name, zone(s), countdown, and zone map |
| `/legion` | Current Legion / Zone Event status and countdown |
| `/schedule` | Upcoming Helltide, World Boss, and Legion events (~3 hours) |
| `/subscribe` | Subscribe this channel to 15-min spawn alerts |
| `/unsubscribe` | Remove spawn alerts from this channel |
| `/subscriptions` | List active alerts configured in this channel |

### `/subscribe` options

- **event** — `Helltide`, `World Boss`, `Legion`, or `All`
- **message** — optional text sent with the alert (supports role pings, e.g. `@D4Events`)

`/subscribe` and `/unsubscribe` require **Manage Channels** permission.

## Data Sources

- **diablo4.life** — Helltide and Legion timing, World Boss name, chest respawn
- **helltides.com** — real-time Helltide zone and World Boss zone data (community-reported)

## Setup

### Requirements

- Python 3.10+
- `davey` library for voice support (optional, only needed for `/julian` sound command)

### Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Or with uv:

```bash
uv venv
uv pip install -r requirements.txt
```

### Environment

Create a `.env` file:

```env
DISCORD_TOKEN=your_bot_token_here
GUILD_ID=your_guild_id_here   # optional, omit for global command sync
```

### Run

```bash
python bot.py
```

## Bot Permissions

The bot requires:

- **Send Messages**
- **Embed Links**
- **Attach Files** (for zone map images)
- **Read Message History** (to delete previous alert messages)

## Project Structure

```
├── bot.py                  # Entry point
├── config.py               # Token and guild ID from .env
├── requirements.txt
├── subscriptions.json      # Auto-created on first /subscribe
├── api/
│   ├── diablo4life.py      # diablo4.life API client
│   └── firebase.py         # helltides.com Firebase client
├── commands/
│   ├── helltide.py
│   ├── worldboss.py
│   ├── legion.py
│   ├── schedule.py
│   └── subscribe.py
├── maps/
│   ├── generator.py        # Pillow zone map image generation
│   ├── zones.py            # Zone rotation data and lookup helpers
│   └── assets/             # Zone map images and boss path data
├── tasks/
│   └── notifier.py         # Background task for spawn alerts
└── utils/
    └── formatters.py       # Discord embed builders and time helpers
```
