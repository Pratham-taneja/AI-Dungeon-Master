"""
Game API routes.

Endpoints:
  POST /game/start          — Create a new game session
  POST /game/action/stream  — Stream DM narrative response (SSE)
  POST /game/npc/talk       — Talk to a specific NPC (SSE)
  GET  /game/state/{id}     — Get current world state
  DELETE /game/{id}         — Delete session
"""

from __future__ import annotations

import json
import logging

from database import AsyncSessionLocal
from world.world_graph import WorldGraphDB

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from agents.dm_agent import DungeonMasterAgent
from agents.npc_agent import NPCAgent
from dependencies import get_dm_agent, get_memory_registry, get_world_manager
from models.schemas import (
    GameEventType,
    NarrativeChunk,
    PlayerActionRequest,
    StartGameRequest,
    StartGameResponse,
    StreamEvent,
    WorldStateResponse,
)
from world.world_state import WorldStateManager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/game", tags=["game"])
world_graph_db = WorldGraphDB()

# Helpers

def _sse_line(event: StreamEvent) -> str:
    """Format a single SSE message."""
    return f"data: {event.model_dump_json()}\n\n"


async def _require_session(session_id: str, wm: WorldStateManager):
    session = await wm.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
    return session



# POST /game/start

@router.post("/start", response_model=StartGameResponse, status_code=201)
async def start_game(
    request: StartGameRequest,
    wm: WorldStateManager = Depends(get_world_manager),
    dm: DungeonMasterAgent = Depends(get_dm_agent),
):
    """
    Create a new game session.
    Generates the world via LLM and returns the opening narrative + session ID.
    """
    try:
        world_data = await dm.generate_world(
            player_name=request.player.name,
            player_class=request.player.player_class.value,
            player_backstory=request.player.backstory,
            world_seed=request.world_seed,
        )
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    session = await wm.create_session(request.player, world_data)

    current_location = session.locations.get(session.player.current_location_id)
    if not current_location:
        raise HTTPException(status_code=500, detail="World generation error: no starting location")

    return StartGameResponse(
        session_id=session.id,
        player=session.player,
        opening_narrative=world_data.get("opening_narrative", "Your adventure begins..."),
        current_location=current_location,
    )


# POST /game/action/stream  (SSE)

@router.post("/action/stream")
async def stream_player_action(
    request: PlayerActionRequest,
    wm: WorldStateManager = Depends(get_world_manager),
    dm: DungeonMasterAgent = Depends(get_dm_agent),
):
    """
    Process a player action and stream the DM narrative via Server-Sent Events.

    SSE event types:
      narrative  — text chunk to display (stream these token by token)
      world_update — structured world state change (parse and update UI)
      done — stream is finished
      error — something went wrong
    """
    session = await _require_session(request.session_id, wm)

    async def event_generator():
        try:
            async for text_chunk, world_update in dm.stream_action(session, request.action):

                if text_chunk:
                    chunk_payload = NarrativeChunk(text=text_chunk, is_final=False)
                    yield _sse_line(StreamEvent(
                        event_type=GameEventType.NARRATIVE,
                        data=chunk_payload.model_dump(),
                        session_id=session.id,
                        turn=session.turn_count,
                    ))

                if world_update is not None:
                    # Persist updated session state
                    await wm.save_session(session)
                    try:
                        async with AsyncSessionLocal() as db:
                            await world_graph_db.sync_session_to_db(db, session)
                            await db.commit()
                    except Exception as exc:
                        logger.warning("Postgres sync failed for session %s: %s", session.id, exc)
                        
                    yield _sse_line(StreamEvent(
                        event_type=GameEventType.WORLD_UPDATE,
                        data=world_update.model_dump(),
                        session_id=session.id,
                        turn=session.turn_count,
                    ))

            # Signal stream completion
            yield _sse_line(StreamEvent(
                event_type=GameEventType.DONE,
                session_id=session.id,
                turn=session.turn_count,
            ))

        except Exception as exc:
            logger.exception("Error in stream_player_action: %s", exc)
            yield _sse_line(StreamEvent(
                event_type=GameEventType.ERROR,
                data={"message": str(exc)},
                session_id=request.session_id,
            ))

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


# POST /game/npc/talk  (SSE)


@router.post("/npc/talk")
async def talk_to_npc(
    request: PlayerActionRequest,
    wm: WorldStateManager = Depends(get_world_manager),
):
    """
    Direct NPC conversation with persistent memory.
    Streams the NPC's in-character dialogue response.

    Requires request.target_npc_id to be set.

    SSE event types:
      narrative  — NPC dialogue chunk
      npc_reaction — structured disposition/trust change
      done
      error
    """
    if not request.target_npc_id:
        raise HTTPException(
            status_code=422,
            detail="target_npc_id is required for NPC conversations",
        )

    session = await _require_session(request.session_id, wm)

    npc = session.npcs.get(request.target_npc_id)
    if not npc:
        raise HTTPException(
            status_code=404,
            detail=f"NPC '{request.target_npc_id}' not found in session",
        )

    memory_registry = get_memory_registry(request.session_id)
    memory_store = memory_registry.get_store(request.target_npc_id)
    npc_agent = NPCAgent(npc=npc, memory_store=memory_store)

    async def event_generator():
        try:
            async for text_chunk in npc_agent.stream_response(
                player_input=request.action,
                player_name=session.player.name,
            ):
                if text_chunk:
                    yield _sse_line(StreamEvent(
                        event_type=GameEventType.NARRATIVE,
                        data=NarrativeChunk(text=text_chunk).model_dump(),
                        session_id=session.id,
                        turn=session.turn_count,
                    ))

            # Apply disposition / trust changes to session
            await npc_agent.apply_interaction_result()
            interaction_result = await npc_agent.get_interaction_result()

            await wm.save_session(session)
            try:
                async with AsyncSessionLocal() as db:
                    await world_graph_db.sync_session_to_db(db, session)
                    await db.commit()
            except Exception as exc:
                logger.warning("Postgres sync failed for session %s: %s", session.id, exc)

            yield _sse_line(StreamEvent(
                event_type=GameEventType.NPC_REACTION,
                data={
                    "npc_id": npc.id,
                    "npc_name": npc.name,
                    "trust_level": npc.trust_level,
                    "disposition": npc.disposition_toward_player.value,
                    "interaction_result": interaction_result,
                },
                session_id=session.id,
                turn=session.turn_count,
            ))

            yield _sse_line(StreamEvent(
                event_type=GameEventType.DONE,
                session_id=session.id,
            ))

        except Exception as exc:
            logger.exception("Error in talk_to_npc: %s", exc)
            yield _sse_line(StreamEvent(
                event_type=GameEventType.ERROR,
                data={"message": str(exc)},
                session_id=request.session_id,
            ))

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


# GET /game/state/{session_id}

@router.get("/state/{session_id}", response_model=WorldStateResponse)
async def get_world_state(
    session_id: str,
    wm: WorldStateManager = Depends(get_world_manager),
):
    """Return the current world state for a session."""
    session = await _require_session(session_id, wm)

    current_location = session.locations.get(session.player.current_location_id)
    if not current_location:
        raise HTTPException(status_code=500, detail="Current location not found in session")

    npcs_present = wm.get_npcs_at_location(session, session.player.current_location_id)
    active_quests = wm.get_active_quests(session)

    return WorldStateResponse(
        session_id=session_id,
        player=session.player,
        current_location=current_location,
        npcs_present=npcs_present,
        active_quests=active_quests,
        turn_count=session.turn_count,
    )


# DELETE /game/{session_id}

@router.delete("/{session_id}", status_code=204)
async def delete_session(
    session_id: str,
    wm: WorldStateManager = Depends(get_world_manager),
):
    """Delete a game session and its NPC memories."""
    registry = get_memory_registry(session_id)
    await registry.bulk_clear()
    await wm.delete_session(session_id)
