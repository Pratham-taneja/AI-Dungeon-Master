"""
 Asset generation API routes.

Endpoints:
  POST /assets/map/{session_id}/{location_id}    — generate map for a location
  POST /assets/portrait/{session_id}/{npc_id}    — generate portrait for an NPC
  POST /assets/generate-all/{session_id}         — generate all missing assets
  GET  /assets/status/{session_id}               — get asset status for session
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException

from assets.generator import (
    generate_assets_for_session,
    generate_location_map,
    generate_npc_portrait,
    generate_scene_image,
)
from dependencies import get_world_manager
from world.world_state import WorldStateManager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/assets", tags=["assets"])


async def _require_session(session_id: str, wm: WorldStateManager):
    session = await wm.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
    return session


@router.post("/map/{session_id}/{location_id}")
async def generate_map(
    session_id: str,
    location_id: str,
    wm: WorldStateManager = Depends(get_world_manager),
):
    """Generate and store a map image for a specific location."""
    session = await _require_session(session_id, wm)

    location = session.locations.get(location_id)
    if not location:
        raise HTTPException(status_code=404, detail=f"Location '{location_id}' not found")

    url = await generate_location_map(location)
    if not url:
        raise HTTPException(status_code=502, detail="Image generation failed")

    location.map_image_url = url
    await wm.save_session(session)

    return {"location_id": location_id, "map_url": url}


@router.post("/portrait/{session_id}/{npc_id}")
async def generate_portrait(
    session_id: str,
    npc_id: str,
    wm: WorldStateManager = Depends(get_world_manager),
):
    """Generate and store a portrait for a specific NPC."""
    session = await _require_session(session_id, wm)

    npc = session.npcs.get(npc_id)
    if not npc:
        raise HTTPException(status_code=404, detail=f"NPC '{npc_id}' not found")

    url = await generate_npc_portrait(npc)
    if not url:
        raise HTTPException(status_code=502, detail="Image generation failed")

    npc.portrait_url = url
    await wm.save_session(session)

    return {"npc_id": npc_id, "portrait_url": url}


@router.post("/generate-all/{session_id}")
async def generate_all_assets(
    session_id: str,
    wm: WorldStateManager = Depends(get_world_manager),
):
    """Generate all missing maps and portraits for a session."""
    session = await _require_session(session_id, wm)

    generated = await generate_assets_for_session(
        locations=list(session.locations.values()),
        npcs=list(session.npcs.values()),
    )

    await wm.save_session(session)

    return {
        "session_id": session_id,
        "assets_generated": len(generated),
        "assets": generated,
    }


@router.get("/status/{session_id}")
async def get_asset_status(
    session_id: str,
    wm: WorldStateManager = Depends(get_world_manager),
):
    """Return current asset URLs for all locations and NPCs in a session."""
    session = await _require_session(session_id, wm)

    return {
        "session_id": session_id,
        "locations": {
            loc_id: loc.map_image_url
            for loc_id, loc in session.locations.items()
        },
        "npcs": {
            npc_id: npc.portrait_url
            for npc_id, npc in session.npcs.items()
        },
    }


@router.post("/scene/{session_id}")
async def generate_scene(
    session_id: str,
    prompt: str,
):
    """Generate a scene image from a text prompt."""
    url = await generate_scene_image(prompt, session_id)
    if not url:
        raise HTTPException(status_code=502, detail="Scene image generation failed")
    return {"session_id": session_id, "scene_url": url}
