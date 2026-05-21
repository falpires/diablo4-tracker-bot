import logging
import time
import aiohttp

log = logging.getLogger(__name__)
_DB = "https://helltides-7e530-r1.firebaseio.com"
TIMEOUT = aiohttp.ClientTimeout(total=8)

_helltide_cache: dict = {"data": None, "ts": 0.0}
_boss_cache: dict = {"data": None, "ts": 0.0}
_FB_TTL = 30.0


async def fetch_helltide_a() -> dict | None:
    """Helltide A (spawns :00 UTC) — zone, startTime, endTime, id."""
    now = time.monotonic()
    if _helltide_cache["ts"] > 0 and now - _helltide_cache["ts"] < _FB_TTL:
        log.debug("fetch_helltide_a: cache hit")
        return _helltide_cache["data"]
    log.debug("fetch_helltide_a: GET %s/helltide.json", _DB)
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{_DB}/helltide.json", timeout=TIMEOUT) as resp:
            if resp.status != 200:
                log.warning("fetch_helltide_a: HTTP %d", resp.status)
                _helltide_cache.update({"data": None, "ts": time.monotonic()})
                return None
            data = await resp.json()
            result = data if isinstance(data, dict) else None
            _helltide_cache.update({"data": result, "ts": time.monotonic()})
            return result


async def fetch_world_boss_firebase() -> dict | None:
    now = time.monotonic()
    if _boss_cache["ts"] > 0 and now - _boss_cache["ts"] < _FB_TTL:
        log.debug("fetch_world_boss_firebase: cache hit")
        return _boss_cache["data"]
    log.debug("fetch_world_boss_firebase: GET %s/world_boss.json", _DB)
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{_DB}/world_boss.json", timeout=TIMEOUT) as resp:
            if resp.status != 200:
                log.warning("fetch_world_boss_firebase: HTTP %d", resp.status)
                _boss_cache.update({"data": None, "ts": time.monotonic()})
                return None
            data = await resp.json()
            result = data if isinstance(data, dict) else None
            _boss_cache.update({"data": result, "ts": time.monotonic()})
            return result
