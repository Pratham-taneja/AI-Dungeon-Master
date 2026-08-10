"""
Multimodal asset generation pipeline.

Generates:
  - Location maps (top-down fantasy style) via NVIDIA NIM (Flux.1-schnell)
  - NPC character portraits (cinematic dark fantasy style)
  - Dynamic scene illustrations per game turn

Assets are saved locally to ./static/assets/ and served via FastAPI StaticFiles.
URLs are stored back on Location.map_image_url and NPC.portrait_url.

Design: generation is async and non-blocking. The game never waits for images —
they are generated in the background and the frontend polls or receives the URL
via a dedicated endpoint once ready.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import logging
from pathlib import Path
from urllib.parse import quote

import httpx

from config import get_settings
from models.schemas import Location, NPC

logger = logging.getLogger(__name__)

#  Asset storage 
ASSETS_DIR = Path(__file__).parent.parent / "static" / "assets"
MAPS_DIR = ASSETS_DIR / "maps"
PORTRAITS_DIR = ASSETS_DIR / "portraits"

MAPS_DIR.mkdir(parents=True, exist_ok=True)
PORTRAITS_DIR.mkdir(parents=True, exist_ok=True)

# Style anchors (keep visual consistency across all generated images)
MAP_STYLE_PREFIX = (
    "A highly detailed, top-down tactical RPG map of a dark fantasy location. "
    "Drawn on weathered parchment paper with muted earth tones, intricate line art, "
    "fine ink hatching, and a subtle aged-paper vignette at the edges. "
    "No text, no labels, no compass markers, no legends. The map depicts: "
)

PORTRAIT_STYLE_PREFIX = (
    "A stunning, photorealistic dark fantasy character portrait, head-and-shoulders framing, "
    "facing slightly off-camera. Cinematic studio lighting with dramatic shadow, highly detailed "
    "facial features and clothing texture, muted colour palette, dark blurred background. "
    "The character is: "
)

#  NVIDIA NIM Image Generation API (Flux.1-schnell) 
NVIDIA_IMAGE_URL = "https://ai.api.nvidia.com/v1/genai/black-forest-labs/flux.1-schnell"

async def _generate_placeholder_image(width: int, height: int) -> bytes:
    """Fallback if API fails completely (generates a 1x1 transparent PNG)."""
    return base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=")

async def generate_image_bytes(prompt: str, width: int = 512, height: int = 512) -> bytes | None:
    """
    Call NVIDIA NIM Flux.1-schnell API and return raw image bytes.
    Returns None on failure so callers can fall back to placeholders.
    """
    settings = get_settings()
    api_key = settings.nvidia_api_key
    if not api_key:
        logger.warning("No NVIDIA_API_KEY found. Skipping image generation.")
        return None

    payload = {
        "prompt": prompt,
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    async with httpx.AsyncClient() as client:
        for attempt in range(3):
            try:
                logger.info("Requesting image from NVIDIA Flux.1-schnell (attempt %d)...", attempt + 1)
                resp = await client.post(NVIDIA_IMAGE_URL, json=payload, headers=headers, timeout=60.0)
                resp.raise_for_status()

                data = resp.json()
                # NVIDIA returns different formats depending on the model:
                #   {"artifacts": [{"base64": "...", "finishReason": "SUCCESS"}]}
                #   {"image": "base64..."} or {"b64_json": "base64..."}
                b64_str = None
                artifacts = data.get("artifacts", [])
                if artifacts and artifacts[0].get("base64"):
                    b64_str = artifacts[0]["base64"]
                else:
                    b64_str = data.get("image") or data.get("b64_json")

                if b64_str:
                    return base64.b64decode(b64_str)

                logger.warning("NVIDIA response missing image data: %s", data)

            except Exception as e:
                logger.warning("NVIDIA Flux.1-schnell failed (attempt %d): %s", attempt + 1, str(e))
                if attempt == 2:
                    break
                await asyncio.sleep(2)

    logger.warning("All NVIDIA image generation attempts failed. Returning None.")
    return None


def _generate_placeholder_svg(label: str, width: int = 400, height: int = 400) -> bytes:
    """
    Generate an SVG placeholder image when the API is unavailable.
    Returns bytes of a dark-fantasy themed SVG placeholder.
    """
    label_safe = label[:30].replace("<", "&lt;").replace(">", "&gt;").replace("&", "&amp;")
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <defs>
    <radialGradient id="bg" cx="50%" cy="50%" r="50%">
      <stop offset="0%" style="stop-color:#2d2010;stop-opacity:1" />
      <stop offset="100%" style="stop-color:#1a1208;stop-opacity:1" />
    </radialGradient>
  </defs>
  <rect width="{width}" height="{height}" fill="url(#bg)"/>
  <rect width="{width}" height="{height}" fill="none" stroke="#c9962a" stroke-width="3" stroke-opacity="0.4"/>
  <rect x="12" y="12" width="{width-24}" height="{height-24}" fill="none" stroke="#c9962a" stroke-width="1" stroke-opacity="0.2" stroke-dasharray="8 4"/>
  <text x="{width//2}" y="{height//2 - 20}" font-family="Georgia, serif" font-size="36" fill="#c9962a" fill-opacity="0.6" text-anchor="middle">⚔</text>
  <text x="{width//2}" y="{height//2 + 15}" font-family="Georgia, serif" font-size="14" fill="#e8d4a8" fill-opacity="0.8" text-anchor="middle">{label_safe}</text>
  <text x="{width//2}" y="{height//2 + 35}" font-family="Georgia, serif" font-size="10" fill="#c9962a" fill-opacity="0.5" text-anchor="middle">[ Image generating... ]</text>
</svg>"""
    return svg.encode("utf-8")


def _asset_url(relative_path: str) -> str:
    """Convert a local file path to a URL served by FastAPI StaticFiles."""
    return f"/static/assets/{relative_path}"


def _cache_key(text: str) -> str:
    return hashlib.md5(text.encode()).hexdigest()[:16]


# Map Generation

def _build_map_prompt(location: Location) -> str:
    biome_hints = {
        "village": "medieval village, thatched roofs, muddy paths",
        "forest": "dark forest, gnarled trees, misty",
        "dungeon": "stone dungeon, torchlit corridors",
        "city": "walled city, market squares, towers",
        "ruins": "ancient ruins, vines, broken columns",
        "tavern": "medieval tavern interior, fireplace",
        "cave": "underground cave, stalactites, dark pools",
    }

    biome_desc = biome_hints.get(location.biome, location.biome)
    danger_hint = "ominous and foreboding atmosphere, " if location.is_dangerous else "calm and inviting atmosphere, "

    return (
        f"{MAP_STYLE_PREFIX}"
        f"{danger_hint}"
        f"{biome_desc}, "
        f"{location.name}, "
        f"{location.description[:80]}"
    )


async def generate_location_map(location: Location) -> str | None:
    """
    Generate a map image for a location.
    """
    cache_key = _cache_key(location.id + location.name)
    filename = f"map_{cache_key}.png"
    filepath = MAPS_DIR / filename

    if filepath.exists():
        logger.debug("Map cache hit for location %s", location.id)
        return _asset_url(f"maps/{filename}")

    prompt = _build_map_prompt(location)
    logger.info("Generating map for location: %s", location.name)

    image_bytes = await generate_image_bytes(prompt, width=512, height=512)
    if image_bytes:
        filepath.write_bytes(image_bytes)
        logger.info("Map saved: %s (%d bytes)", filename, len(image_bytes))
        return _asset_url(f"maps/{filename}")

    svg_filename = f"map_{cache_key}.svg"
    svg_filepath = MAPS_DIR / svg_filename
    svg_bytes = _generate_placeholder_svg(location.name, width=400, height=400)
    svg_filepath.write_bytes(svg_bytes)
    logger.info("Map placeholder saved: %s", svg_filename)
    return _asset_url(f"maps/{svg_filename}")


#  NPC Portrait Generation 

def _build_portrait_prompt(npc: NPC) -> str:
    appearance = npc.appearance[:80] if npc.appearance else "mysterious figure"
    traits = ", ".join(npc.personality.traits[:2]) if npc.personality.traits else "neutral"
    disposition_hint = {
        "friendly": "warm, welcoming expression",
        "neutral": "composed, unreadable expression",
        "suspicious": "wary, narrowed eyes",
        "hostile": "cold, threatening expression",
        "fearful": "nervous, guarded expression",
    }.get(npc.disposition_toward_player.value, "neutral expression")
    
    return (
        f"{PORTRAIT_STYLE_PREFIX}"
        f"{npc.role}, {appearance}, {traits}, {disposition_hint}"
    )


async def generate_npc_portrait(npc: NPC) -> str | None:
    """
    Generate a portrait image for an NPC.
    """
    cache_key = _cache_key(npc.id + npc.name)
    filename = f"portrait_{cache_key}.png"
    filepath = PORTRAITS_DIR / filename

    if filepath.exists():
        logger.debug("Portrait cache hit for NPC %s", npc.id)
        return _asset_url(f"portraits/{filename}")

    prompt = _build_portrait_prompt(npc)
    logger.info("Generating portrait for NPC: %s", npc.name)

    image_bytes = await generate_image_bytes(prompt, width=384, height=512)
    if image_bytes:
        filepath.write_bytes(image_bytes)
        logger.info("Portrait saved: %s (%d bytes)", filename, len(image_bytes))
        return _asset_url(f"portraits/{filename}")

    svg_filename = f"portrait_{cache_key}.svg"
    svg_filepath = PORTRAITS_DIR / svg_filename
    svg_bytes = _generate_placeholder_svg(npc.name, width=300, height=400)
    svg_filepath.write_bytes(svg_bytes)
    logger.info("Portrait placeholder saved: %s", svg_filename)
    return _asset_url(f"portraits/{svg_filename}")


#  Bulk generation 

async def generate_assets_for_session(
    locations: list[Location],
    npcs: list[NPC],
) -> dict[str, str]:
    """
    Generate all missing assets for a session (called after world creation).
    Returns a dict mapping entity_id -> asset_url for everything generated.
    """
    results: dict[str, str] = {}

    for location in locations:
        if not location.map_image_url:
            url = await generate_location_map(location)
            if url:
                location.map_image_url = url
                results[location.id] = url

    for npc in npcs:
        if not npc.portrait_url:
            url = await generate_npc_portrait(npc)
            if url:
                npc.portrait_url = url
                results[npc.id] = url

    return results


#  Scene Image Generation (dynamic per-turn backgrounds) 

SCENE_STYLE_PREFIX = (
    "A gorgeous, wide-angle cinematic shot of a dark fantasy landscape. "
    "Highly detailed, photorealistic, atmospheric lighting, volumetric depth, "
    "color grading matching the scene's emotional tone. The scene shows: "
)

SCENES_DIR = ASSETS_DIR / "scenes"
SCENES_DIR.mkdir(parents=True, exist_ok=True)


async def generate_scene_image(prompt: str, session_id: str) -> str | None:
    """
    Generate a scene illustration from the DM's scene_image_prompt.
    Returns the URL or None on failure.
    Uses wider aspect ratio (768x432) for background display.
    """
    full_prompt = SCENE_STYLE_PREFIX + prompt
    cache_key = _cache_key(session_id + prompt)
    filename = f"scene_{cache_key}.png"
    filepath = SCENES_DIR / filename

    if filepath.exists():
        logger.debug("Scene cache hit: %s", filename)
        return _asset_url(f"scenes/{filename}")

    logger.info("Generating scene image: %s", prompt[:60])
    image_bytes = await generate_image_bytes(full_prompt, width=768, height=432)

    if image_bytes:
        filepath.write_bytes(image_bytes)
        logger.info("Scene saved: %s (%d bytes)", filename, len(image_bytes))
        return _asset_url(f"scenes/{filename}")

    logger.warning("Scene generation failed for: %s", prompt[:60])
    return None