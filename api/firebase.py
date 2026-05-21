import aiohttp

_DB = "https://helltides-7e530-r1.firebaseio.com"
TIMEOUT = aiohttp.ClientTimeout(total=8)


async def fetch_helltide_a() -> dict | None:
    """Helltide A (spawns :00 UTC) — zone, startTime, endTime, id."""
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{_DB}/helltide.json", timeout=TIMEOUT) as resp:
            if resp.status != 200:
                return None
            data = await resp.json()
            return data if isinstance(data, dict) else None


async def fetch_world_boss_firebase() -> dict | None:
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{_DB}/world_boss.json", timeout=TIMEOUT) as resp:
            if resp.status != 200:
                return None
            data = await resp.json()
            return data if isinstance(data, dict) else None
