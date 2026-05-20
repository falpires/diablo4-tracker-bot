import aiohttp

BASE = "https://diablo4.life"
TIMEOUT = aiohttp.ClientTimeout(total=10)


async def fetch_events(helltide_location: str | None = None) -> dict:
    params = {"helltideLocationOverride": helltide_location} if helltide_location else {}
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{BASE}/api/trackers/list", params=params, timeout=TIMEOUT) as resp:
            resp.raise_for_status()
            return await resp.json()


async def fetch_report_history(tracker: str) -> list[dict]:
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{BASE}/api/trackers/{tracker}/reportHistory", timeout=TIMEOUT) as resp:
            resp.raise_for_status()
            data = await resp.json()
            return data.get("reports", [])
