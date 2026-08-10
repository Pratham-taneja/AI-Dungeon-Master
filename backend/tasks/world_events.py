"""
Celery async tasks for autonomous world simulation.

the world evolves even when the player is idle.

Tasks:
  generate_world_event  — LLM generates a random world event for a session
  schedule_world_events — periodic beat task that fires events for active sessions
  process_npc_aging     — NPCs shift disposition over time based on unresolved quests

These run in a separate Celery worker process. The FastAPI app triggers them
via .delay() and they communicate results back via Redis.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys

from celery import Celery

# Ensure backend/ is on path when worker starts
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

# Celery app
celery_app = Celery(
    "rpg_tasks",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    beat_schedule={
        "autonomous-world-events": {
            "task": "tasks.world_events.schedule_world_events",
            "schedule": settings.world_event_interval_seconds,
        },
    },
)


# Prompt for autonomous events
AUTONOMOUS_EVENT_PROMPT = """You are generating a spontaneous world event for a dark fantasy RPG.

Current world context:
Player name: {player_name}
Player location: {location_name}
Recent world events: {recent_events}
Active quests: {active_quests}

Generate ONE brief, impactful world event that happens WITHOUT player involvement.
Examples: a fire breaks out, a traveller arrives with news, bandits raid a nearby farm,
a mysterious figure is spotted, an NPC dies, political turmoil erupts.

The event should:
- Feel organic and consequential
- Connect loosely to existing quests or NPCs when possible
- Avoid contradicting or resolving any active quest — events should create texture and tension, not finish the player's objectives for them
- Avoid repeating the theme or subject of the most recent world events listed above
- Be 1-2 sentences max
- Be written as a news bulletin / rumour the player might hear

Output ONLY the event text, nothing else. No JSON, no explanation."""


def _run_async(coro):
    """Helper to run async code from a sync Celery task."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


async def _sync_session_data_to_db(session_id: str, session_data: dict) -> None:
    """
    Push the current Redis session dict into Postgres.

    Creates a fresh, short-lived engine scoped to the current event loop —
    _run_async creates and closes a new loop per task call, so a shared
    app-wide engine/session factory (bound to FastAPI's long-running loop)
    would end up attached to a closed loop between calls. Correctness over
    reuse here, since these tasks are infrequent.
    """
    try:
        from sqlalchemy.ext.asyncio import (
            AsyncSession,
            async_sessionmaker,
            create_async_engine,
        )

        from models.schemas import GameSession
        from world.world_graph import WorldGraphDB

        game_session = GameSession.model_validate(session_data)

        engine = create_async_engine(settings.database_url)
        session_factory = async_sessionmaker(
            bind=engine, class_=AsyncSession, expire_on_commit=False
        )
        world_graph_db = WorldGraphDB()

        try:
            async with session_factory() as db:
                await world_graph_db.sync_session_to_db(db, game_session)
                await db.commit()
        finally:
            await engine.dispose()

        logger.debug("Postgres sync succeeded for session %s (background task)", session_id)

    except Exception as exc:
        logger.warning(
            "Postgres sync failed for session %s (background task): %s", session_id, exc
        )


# Tasks

@celery_app.task(
    name="tasks.world_events.generate_world_event",
    bind=True,
    max_retries=2,
    default_retry_delay=10,
)
def generate_world_event(self, session_id: str) -> dict:
    """
    Generate and store one autonomous world event for the given session.

    Returns:
        {"session_id": ..., "event_text": ..., "success": bool}
    """
    try:
        result = _run_async(_generate_event_async(session_id))
        return result
    except Exception as exc:
        logger.error("World event generation failed for session %s: %s", session_id, exc)
        raise self.retry(exc=exc)


async def _generate_event_async(session_id: str) -> dict:
    """Async implementation called from the sync Celery task."""
    import redis.asyncio as aioredis
    from langchain_core.messages import HumanMessage
    from langchain_openai import ChatOpenAI

    settings = get_settings()
    llm = ChatOpenAI(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=settings.nvidia_api_key,
        model=settings.llm_model,
        max_tokens=200,
        temperature=0.9,
    )
    redis = await aioredis.from_url(settings.redis_url, decode_responses=True)

    # Load session from Redis
    raw = await redis.get(f"session:{session_id}")
    if not raw:
        logger.warning("Session %s not found in Redis for world event", session_id)
        await redis.aclose()
        return {"session_id": session_id, "event_text": "", "success": False}

    session_data = json.loads(raw)
    player_name = session_data.get("player", {}).get("name", "Unknown")
    current_loc_id = session_data.get("player", {}).get("current_location_id", "")
    locations = session_data.get("locations", {})
    location_name = locations.get(current_loc_id, {}).get("name", "Unknown")
    recent_events = session_data.get("world_events", [])[-3:]
    quests = session_data.get("quests", {})
    active_quests = [
        q["title"] for q in quests.values()
        if q.get("status") == "active"
    ]

    prompt = AUTONOMOUS_EVENT_PROMPT.format(
        player_name=player_name,
        location_name=location_name,
        recent_events=", ".join(recent_events) if recent_events else "none",
        active_quests=", ".join(active_quests) if active_quests else "none",
    )

    result = await llm.ainvoke([HumanMessage(content=prompt)])
    event_text: str = result.content.strip()  # type: ignore[union-attr]

    # Append event to session in Redis
    session_data["world_events"].append(event_text)
    # Keep only last 20 events in Redis
    session_data["world_events"] = session_data["world_events"][-20:]

    await redis.setex(
        f"session:{session_id}",
        60 * 60 * 24 * 7,
        json.dumps(session_data),
    )

    # Also push event to a pub/sub channel so live frontend can receive it
    await redis.publish(
        f"events:{session_id}",
        json.dumps({"type": "world_event", "text": event_text}),
    )

    await redis.aclose()

    # Persist the updated session (with the new world event) to Postgres too
    await _sync_session_data_to_db(session_id, session_data)

    logger.info("World event generated for session %s: %s", session_id, event_text[:60])
    return {"session_id": session_id, "event_text": event_text, "success": True}


@celery_app.task(name="tasks.world_events.schedule_world_events")
def schedule_world_events() -> dict:
    """
    Periodic beat task: fires generate_world_event for every active session.
    Discovers active sessions from Redis key scan.
    """
    result = _run_async(_schedule_events_async())
    return result


async def _schedule_events_async() -> dict:
    import redis.asyncio as aioredis

    redis = await aioredis.from_url(settings.redis_url, decode_responses=True)
    session_keys = await redis.keys("session:*")
    await redis.aclose()

    count = 0
    for key in session_keys:
        session_id = key.replace("session:", "")
        generate_world_event.delay(session_id)
        count += 1

    logger.info("Scheduled world events for %d active sessions", count)
    return {"sessions_triggered": count}


@celery_app.task(name="tasks.world_events.process_npc_aging")
def process_npc_aging(session_id: str) -> dict:
    """
    Shift NPC dispositions over time based on unresolved quests and time elapsed.
    NPCs slowly grow impatient if their quests stay unresolved.
    """
    result = _run_async(_npc_aging_async(session_id))
    return result


async def _npc_aging_async(session_id: str) -> dict:
    import redis.asyncio as aioredis

    redis = await aioredis.from_url(settings.redis_url, decode_responses=True)
    raw = await redis.get(f"session:{session_id}")
    if not raw:
        await redis.aclose()
        return {"session_id": session_id, "changes": 0}

    session_data = json.loads(raw)
    npcs = session_data.get("npcs", {})
    quests = session_data.get("quests", {})
    turn_count = session_data.get("turn_count", 0)
    changes = 0

    # Every 10 turns, NPCs who gave active quests grow a bit more impatient
    if turn_count > 0 and turn_count % 10 == 0:
        quest_givers_with_active = {
            q.get("giver_npc_id")
            for q in quests.values()
            if q.get("status") == "active" and q.get("giver_npc_id")
        }

        disposition_order = ["friendly", "neutral", "suspicious", "hostile"]

        for npc_id, npc in npcs.items():
            if npc_id in quest_givers_with_active:
                current = npc.get("disposition_toward_player", "neutral")
                if current in disposition_order:
                    idx = disposition_order.index(current)
                    if idx < len(disposition_order) - 1:
                        npc["disposition_toward_player"] = disposition_order[idx + 1]
                        changes += 1

        session_data["npcs"] = npcs
        await redis.setex(
            f"session:{session_id}",
            60 * 60 * 24 * 7,
            json.dumps(session_data),
        )

        if changes:
            await _sync_session_data_to_db(session_id, session_data)

    await redis.aclose()
    return {"session_id": session_id, "changes": changes}