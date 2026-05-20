import json
from pathlib import Path

# Zone name (API string) → zone ID (file/data key)
ZONE_NAME_TO_ID: dict[str, str] = {
    "Fractured Peaks": "fractured_peaks",
    "Scosglen": "scosglen",
    "Dry Steppes": "dry_steppes",
    "Hawezar": "hawezar",
    "Kehjistan": "kehjistan",
    "Nahantu": "nahantu",
    "Skovos": "skovos",
}

# Helltide zone rotation (Season 8 / 2026 — verify anchor if wrong)
# 60-minute cycle, 55 min active, 5 min downtime
HELLTIDE_CYCLE_MS = 60 * 60 * 1000

# Known anchor: the spawn at HELLTIDE_ANCHOR_MS was HELLTIDE_ROTATION[HELLTIDE_ANCHOR_INDEX]
# Best guess from user report: Hawezar (idx 2) + Skovos (idx 6) were simultaneously active
# at 2026-05-20 ~13:50 UTC (within cycle starting 12:55 UTC). Verify in-game to confirm.
HELLTIDE_ANCHOR_MS = 1779292500000
HELLTIDE_ANCHOR_INDEX = 2

# D4 runs two concurrent helltides. The second runs at this offset in the rotation.
# Derived from user report: when base=Hawezar(2), expansion=Skovos(6) → offset=4
HELLTIDE_SECOND_OFFSET = 4

HELLTIDE_ROTATION = [
    "Fractured Peaks",
    "Dry Steppes",
    "Hawezar",
    "Kehjistan",
    "Scosglen",
    "Nahantu",
    "Skovos",
]


def get_helltide_zone(spawn_time_ms: int) -> str:
    cycles = (spawn_time_ms - HELLTIDE_ANCHOR_MS) // HELLTIDE_CYCLE_MS
    idx = (HELLTIDE_ANCHOR_INDEX + int(cycles)) % len(HELLTIDE_ROTATION)
    return HELLTIDE_ROTATION[idx]


def get_helltide_second_zone(spawn_time_ms: int) -> str:
    """Return the zone for the second concurrent helltide (expansion zones)."""
    cycles = (spawn_time_ms - HELLTIDE_ANCHOR_MS) // HELLTIDE_CYCLE_MS
    idx = (HELLTIDE_ANCHOR_INDEX + int(cycles) + HELLTIDE_SECOND_OFFSET) % len(HELLTIDE_ROTATION)
    return HELLTIDE_ROTATION[idx]


# Loaded from the extracted helltides.com zone data
_ZONE_DATA_PATH = Path(__file__).parent / "assets" / "zone_data.json"
_zone_data_cache: dict[str, dict] | None = None


def _load_zone_data() -> dict[str, dict]:
    global _zone_data_cache
    if _zone_data_cache is None:
        if _ZONE_DATA_PATH.exists():
            with open(_ZONE_DATA_PATH) as f:
                raw = json.load(f)
            _zone_data_cache = {z["id"]: z for z in raw}
        else:
            _zone_data_cache = {}
    return _zone_data_cache


def get_zone_info(zone_id: str) -> dict | None:
    return _load_zone_data().get(zone_id)


def get_boss_path_centroids(zone_id: str) -> list[tuple[float, float]]:
    """Return pixel (x, y) centroid for each boss path in a zone."""
    info = get_zone_info(zone_id)
    if not info:
        return []
    h = info["height"]
    centroids = []
    for path in info.get("bossPaths", []):
        if not path:
            continue
        cx = sum(p[1] for p in path) / len(path)  # lng → pixel x
        cy = h - sum(p[0] for p in path) / len(path)  # lat → pixel y (inverted)
        centroids.append((cx, cy))
    return centroids
