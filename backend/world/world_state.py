"""
 In-memory world state manager with Redis persistence.

Responsibilities:
- Parse LLM-generated world JSON into typed model objects
- Store and retrieve game sessions (Redis for speed, JSON serialised)
- Provide clean read/write helpers for the API layer

Design decision: a simple dict-in-memory store.
Redis persistence is wired in so sessions survive server restarts.

"""

from __future__ import annotations

import json
import logging
from datetime import datetime

import redis.asyncio as aioredis

from config import get_settings
from models.schemas import (
    GameSession,
    Location,
    NPC,
    NPCPersonality,
    NPCDisposition,
    Player,
    PlayerCreate,
    PlayerStats,
    Quest,
    QuestStatus,
)

logger = logging.getLogger(__name__)
settings = get_settings()

SESSION_TTL_SECONDS = 60 * 60 * 24 * 7   # 7 days


class WorldStateManager:
    """
    Central manager for all game session state.

    One instance per app (singleton via dependency injection).
    Holds sessions in memory and syncs to Redis for persistence.
    """

    def __init__(self) -> None:
        self._sessions: dict[str, GameSession] = {}
        self._redis: aioredis.Redis | None = None
        self._redis_available: bool = True   # set False after first connection failure

    async def get_redis(self) -> aioredis.Redis:
        if self._redis is None:
            self._redis = await aioredis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
        return self._redis


    # Session lifecycle


    async def create_session(
        self,
        player_data: PlayerCreate,
        world_data: dict,
    ) -> GameSession:
        """
        Create a full GameSession from:
          - player_data: PlayerCreate from the API request
          - world_data: dict parsed from DM's world generation JSON

        Returns the fully initialised GameSession.
        """
        player = Player(
            name=player_data.name,
            player_class=player_data.player_class,
            backstory=player_data.backstory,
            stats=PlayerStats(),
        )

        session = GameSession(player=player)

        # Parse locations
        start_loc_data = world_data.get("starting_location", {})
        if start_loc_data:
            loc = self._parse_location(start_loc_data)
            session.locations[loc.id] = loc
            player.current_location_id = loc.id

        for nearby in world_data.get("nearby_locations", []):
            loc = self._parse_location(nearby)
            session.locations[loc.id] = loc

        # Parse NPCs
        for npc_data in world_data.get("starting_npcs", []):
            npc = self._parse_npc(npc_data)
            session.npcs[npc.id] = npc
            # Register NPC at their location
            if npc.location_id in session.locations:
                loc = session.locations[npc.location_id]
                if npc.id not in loc.npc_ids:
                    loc.npc_ids.append(npc.id)

        # Parse quests
        for quest_data in world_data.get("starting_quests", []):
            quest = self._parse_quest(quest_data)
            session.quests[quest.id] = quest

        # Persist to memory + Redis
        self._sessions[session.id] = session
        await self._save_to_redis(session)

        logger.info(
            "Session created: %s | player=%s | locations=%d | npcs=%d",
            session.id,
            player.name,
            len(session.locations),
            len(session.npcs),
        )
        return session

    async def get_session(self, session_id: str) -> GameSession | None:
        """Load session from memory cache, falling back to Redis."""
        if session_id in self._sessions:
            return self._sessions[session_id]

        # Try Redis
        try:
            redis = await self.get_redis()
            raw = await redis.get(f"session:{session_id}")
            if raw:
                data = json.loads(raw)
                session = GameSession.model_validate(data)
                self._sessions[session_id] = session
                logger.debug("Session %s loaded from Redis", session_id)
                return session
        except Exception:
            pass  # Redis unavailable — session not found

        return None

    async def save_session(self, session: GameSession) -> None:
        """Persist session state after a mutation."""
        session.last_action_at = datetime.utcnow()
        self._sessions[session.id] = session
        await self._save_to_redis(session)

    async def delete_session(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)
        try:
            redis = await self.get_redis()
            await redis.delete(f"session:{session_id}")
        except Exception as exc:
            logger.error("Redis delete failed: %s", exc)

    async def _save_to_redis(self, session: GameSession) -> None:
        if not self._redis_available:
            return  # already know Redis is down — skip silently
        try:
            redis = await self.get_redis()
            await redis.setex(
                f"session:{session.id}",
                SESSION_TTL_SECONDS,
                session.model_dump_json(),
            )
        except Exception as exc:
            self._redis_available = False
            logger.debug(
                "Redis unavailable (sessions kept in memory only): %s", exc
            )

    # Helpers

    def _parse_location(self, data: dict) -> Location:
        return Location(
            id=data["id"],
            name=data.get("name", data["id"].replace("_", " ").title()),
            description=data.get("description", ""),
            biome=data.get("biome", "unknown"),
            connected_locations=data.get("connected_locations", []),
            is_dangerous=data.get("is_dangerous", False),
        )

    def _parse_npc(self, data: dict) -> NPC:
        p_data = data.get("personality", {})
        disp_str = p_data.get("disposition_toward_strangers", "neutral")
        try:
            disp = NPCDisposition(disp_str)
        except ValueError:
            disp = NPCDisposition.NEUTRAL

        personality = NPCPersonality(
            traits=p_data.get("traits", []),
            speech_style=p_data.get("speech_style", "plain"),
            motivation=p_data.get("motivation", "survive"),
            secret=p_data.get("secret", ""),
            disposition_toward_strangers=disp,
        )
        return NPC(
            id=data["id"],
            name=data.get("name", "Unknown"),
            role=data.get("role", "villager"),
            appearance=data.get("appearance", ""),
            location_id=data.get("location_id", "starting_village"),
            personality=personality,
            backstory=data.get("backstory", ""),
            disposition_toward_player=disp,
        )

    def _parse_quest(self, data: dict) -> Quest:
        return Quest(
            id=data.get("id", f"quest_{data.get('title', 'unknown').lower().replace(' ', '_')}"),
            title=data.get("title", "Unknown Quest"),
            description=data.get("description", ""),
            giver_npc_id=data.get("giver_npc_id"),
            objectives=data.get("objectives", []),
            reward_gold=data.get("reward_gold", 0),
            reward_items=data.get("reward_items", []),
            status=QuestStatus.AVAILABLE,
        )

    # Read helpers used by API routes

    def get_npcs_at_location(
        self, session: GameSession, location_id: str
    ) -> list[NPC]:
        loc = session.locations.get(location_id)
        if not loc:
            return []
        return [
            session.npcs[nid]
            for nid in loc.npc_ids
            if nid in session.npcs
        ]

    def get_active_quests(self, session: GameSession) -> list[Quest]:
        return [q for q in session.quests.values() if q.status == QuestStatus.ACTIVE]
