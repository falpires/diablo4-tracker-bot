"""
Generates Diablo 4 zone maps for Discord embeds using real zone images from helltides.com.

Helltide: returns the zone map image (already has red helltide shading).
World boss: returns the zone map with circles on boss spawn path centroids.
"""
import io
import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from maps.zones import ZONE_NAME_TO_ID, get_zone_info, get_boss_path_centroids

ASSETS = Path(__file__).parent / "assets"

OUTPUT_WIDTH = 800  # resize all maps to this width for Discord

BOSS_CIRCLE_COLOR = (220, 20, 220)     # magenta circle
BOSS_CIRCLE_OUTLINE = (255, 255, 255)
BOSS_CIRCLE_RADIUS = 18
WATERMARK_COLOR = (200, 180, 160, 160)


def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
    ]:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


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


def generate_helltide_map(zone_name: str | None) -> io.BytesIO | None:
    """Return the zone map image. Already has red helltide shading from helltides.com."""
    if not zone_name:
        return None
    zone_id = ZONE_NAME_TO_ID.get(zone_name)
    if not zone_id:
        return None
    img = _load_zone_image(zone_id)
    if img is None:
        return None
    return _to_buf(_resize(img))


def generate_boss_map(zone_name: str | None) -> io.BytesIO | None:
    """Return zone map with magenta circles on every boss spawn path centroid."""
    if not zone_name:
        return None
    zone_id = ZONE_NAME_TO_ID.get(zone_name)
    if not zone_id:
        return None
    img = _load_zone_image(zone_id)
    if img is None:
        return None

    info = get_zone_info(zone_id)
    centroids = get_boss_path_centroids(zone_id)

    if centroids and info:
        orig_w, orig_h = info["width"], info["height"]
        # Scale to OUTPUT_WIDTH
        scale = OUTPUT_WIDTH / orig_w
        img = _resize(img)
        draw = ImageDraw.Draw(img, "RGBA")
        font = _load_font(14)

        for i, (cx, cy) in enumerate(centroids):
            px = int(cx * scale)
            py = int(cy * scale)
            r = BOSS_CIRCLE_RADIUS
            draw.ellipse(
                [px - r, py - r, px + r, py + r],
                fill=(*BOSS_CIRCLE_COLOR, 200),
                outline=BOSS_CIRCLE_OUTLINE,
                width=2,
            )
            label = f"Spawn {i+1}" if len(centroids) > 1 else "Boss"
            draw.text((px, py + r + 3), label, font=font, fill=(255, 255, 255), anchor="mt")
    else:
        img = _resize(img)

    return _to_buf(img)
