"""One-shot script to verify diablo4.life API data. Run: python test_api.py"""
import asyncio
import json
import time
from api.d4armory import fetch_events


def fmt_countdown(ts_ms: int) -> str:
    if not ts_ms:
        return "N/A"
    now_ms = int(time.time() * 1000)
    diff_s = (ts_ms - now_ms) // 1000
    if abs(diff_s) < 60:
        return f"{diff_s}s"
    sign = "" if diff_s >= 0 else "-"
    diff_s = abs(diff_s)
    if diff_s < 3600:
        return f"{sign}{diff_s // 60}m {diff_s % 60}s"
    h, rem = divmod(diff_s, 3600)
    return f"{sign}{h}h {rem // 60}m"


async def main():
    print("Fetching diablo4.life events...\n")
    data = await fetch_events()

    print("=== RAW JSON ===")
    print(json.dumps(data, indent=2))
    print()

    if helltide := data.get("helltide"):
        ts_ms = helltide.get("time", 0)
        loc = helltide.get("location", "Unknown")
        print("=== HELLTIDE ===")
        print(f"  Location:  {loc}")
        print(f"  Spawn:     {fmt_countdown(ts_ms)}")
        print()

    if boss := data.get("worldBoss"):
        ts_ms = boss.get("time", 0)
        print("=== WORLD BOSS ===")
        print(f"  Name:      {boss.get('name', 'N/A')}")
        print(f"  Spawn:     {fmt_countdown(ts_ms)}")
        print()

    if next_boss := data.get("nextWorldBoss"):
        ts_ms = next_boss.get("time", 0)
        print("=== NEXT WORLD BOSS ===")
        print(f"  Name:      {next_boss.get('name', 'N/A')}")
        print(f"  Spawn:     {fmt_countdown(ts_ms)}")
        print()

    if zone := data.get("zoneEvent"):
        ts_ms = zone.get("time", 0)
        print("=== ZONE EVENT (LEGION) ===")
        print(f"  Spawn:     {fmt_countdown(ts_ms)}")
        print()

    if chest := data.get("chestRespawn"):
        print(f"=== CHEST RESPAWN ===")
        print(f"  In:        {fmt_countdown(chest)}")
        print()


asyncio.run(main())
