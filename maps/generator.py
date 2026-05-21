"""
Generates Diablo 4 zone maps for Discord embeds using real zone images from helltides.com.
Helltide: returns the zone map image (already has red helltide shading).
Boss: returns the same image desaturated — removes helltide coloring, keeps geography.
"""
import io
from pathlib import Path

from PIL import Image, ImageEnhance

from maps.zones import ZONE_NAME_TO_ID

ASSETS = Path(__file__).parent / "assets"
OUTPUT_WIDTH = 800  # resize all maps to this width for Discord


def _load_zone_image(zone_id: str) -> Image.Image | None:
    path = ASSETS / f"{zone_id}.png"
    if not path.exists():
        return None
    return Image.open(path).convert("RGB")


def _resize(img: Image.Image) -> Image.Image:
    w, h = img.size
    new_h = int(h * OUTPUT_WIDTH / w)
    return img.resize((OUTPUT_WIDTH, new_h), Image.LANCZOS)


def _to_buf(img: Image.Image) -> io.BytesIO:
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    buf.seek(0)
    return buf


def _zone_image(zone_name: str | None) -> Image.Image | None:
    if not zone_name:
        return None
    zone_id = ZONE_NAME_TO_ID.get(zone_name)
    if not zone_id:
        return None
    return _load_zone_image(zone_id)


def generate_helltide_map(zone_name: str | None) -> io.BytesIO | None:
    """Return the zone map image with helltide shading from helltides.com."""
    img = _zone_image(zone_name)
    if img is None:
        return None
    return _to_buf(_resize(img))


def generate_boss_map(zone_name: str | None) -> io.BytesIO | None:
    """Return the zone map desaturated — strips helltide red shading."""
    img = _zone_image(zone_name)
    if img is None:
        return None
    img = ImageEnhance.Color(_resize(img)).enhance(0.0)
    return _to_buf(img)
