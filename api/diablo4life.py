import logging
import time
import aiohttp

log = logging.getLogger(__name__)
BASE = "https://diablo4.life"
TIMEOUT = aiohttp.ClientTimeout(total=10)

_events_cache: dict = {"data": None, "ts": 0.0}
_EVENTS_TTL = 45.0


async def fetch_events(helltide_location: str | None = None) -> dict:
    now = time.monotonic()
    if _events_cache["ts"] > 0 and now - _events_cache["ts"] < _EVENTS_TTL:
        log.debug("fetch_events: cache hit")
        return _events_cache["data"]
    params = {"helltideLocationOverride": helltide_location} if helltide_location else {}
    log.debug("fetch_events: GET %s/api/trackers/list", BASE)
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{BASE}/api/trackers/list", params=params, timeout=TIMEOUT) as resp:
            if resp.status != 200:
                log.warning("fetch_events: HTTP %d", resp.status)
                resp.raise_for_status()
            result = await resp.json()
            _events_cache.update({"data": result, "ts": time.monotonic()})
            return result


async def fetch_report_history(tracker: str) -> list[dict]:
    log.debug("fetch_report_history: GET %s/api/trackers/%s/reportHistory", BASE, tracker)
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{BASE}/api/trackers/{tracker}/reportHistory", timeout=TIMEOUT) as resp:
            resp.raise_for_status()
            data = await resp.json()
            return data.get("reports", [])
