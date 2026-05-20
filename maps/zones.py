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
# Anchor index 6 = Skovos confirmed: cycle 1 from anchor gives FP (idx 0), user confirmed FP active.
# D4 sometimes runs a second concurrent helltide but with no reliable API data for it.
HELLTIDE_ANCHOR_MS = 1779292500000
HELLTIDE_ANCHOR_INDEX = 6

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


# World boss deterministic rotation (verified from helltides.com, 2026-05-20)
# 12-slot cycle, 12600s (3.5h) per slot. Boss + zone(s) per slot.
BOSS_INTERVAL_MS = 12600 * 1000
BOSS_ANCHOR_MS = 1779307200 * 1000  # slot 0: Ashava, Dry Steppes

BOSS_ROTATION: list[tuple[str, list[str]]] = [
    ("Ashava the Pestilent",              ["Dry Steppes"]),
    ("Ashava the Pestilent",              ["Fractured Peaks"]),
    ("Ashava the Pestilent",              ["Kehjistan", "Nahantu"]),
    ("Wandering Death, Death Given Life", ["Scosglen"]),
    ("Wandering Death, Death Given Life", ["Kehjistan"]),
    ("Avarice, the Gold Cursed",          ["Scosglen"]),
    ("Avarice, the Gold Cursed",          ["Kehjistan", "Nahantu"]),
    ("Avarice, the Gold Cursed",          ["Scosglen"]),
    ("Ashava the Pestilent",              ["Kehjistan"]),
    ("Ashava the Pestilent",              ["Scosglen"]),
    ("Wandering Death, Death Given Life", ["Dry Steppes", "Nahantu"]),
    ("Wandering Death, Death Given Life", ["Fractured Peaks"]),
]


def get_boss_spawn(now_ms: int) -> tuple[str, list[str], int, str, list[str], int]:
    """Return (boss, zones, spawn_ms, next_boss, next_zones, next_spawn_ms)."""
    slot = int((now_ms - BOSS_ANCHOR_MS) // BOSS_INTERVAL_MS)
    spawn_ms = BOSS_ANCHOR_MS + slot * BOSS_INTERVAL_MS
    next_spawn_ms = spawn_ms + BOSS_INTERVAL_MS
    boss, zones = BOSS_ROTATION[slot % len(BOSS_ROTATION)]
    next_boss, next_zones = BOSS_ROTATION[(slot + 1) % len(BOSS_ROTATION)]
    return boss, zones, spawn_ms, next_boss, next_zones, next_spawn_ms


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
