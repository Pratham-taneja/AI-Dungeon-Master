"""
 PostgreSQL-backed world state graph manager.

replaces the pure in-memory approach with full DB persistence.
The WorldStateManager still holds sessions in memory for speed,
but now syncs every mutation to PostgreSQL for durability.

The session object remains the single source of truth in memory —
DB is write-through, used for persistence across server restarts.
"""

from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models.schemas import (
    GameSession,
    Location,
    NPC,
    Quest,
    QuestStatus,
)
from world.db_models import (
    DBLocation,
    DBNPC,
    DBQuest,
    DBSession,
    DBWorldEvent,
)

logger = logging.getLogger(__name__)


class WorldGraphDB:
    """
    Handles all PostgreSQL read/write for world state.
    Used by WorldStateManager as its persistence layer.

    All methods take an AsyncSession from FastAPI dependency injection.
    """

    # Session

    async def upsert_session(
        self, db: AsyncSession, session: GameSession
    ) -> None:
        """Write-through: persist the full session state to DB."""
        existing = await db.get(DBSession, session.id)
        player_data = session.player.model_dump(mode="json")

        if existing:
            existing.player_data = player_data
            existing.turn_count = session.turn_count
            existing.last_action_at = datetime.utcnow()
        else:
            db_session = DBSession(
                id=session.id,
                player_name=session.player.name,
                player_class=session.player.player_class.value,
                player_data=player_data,
                turn_count=session.turn_count,
            )
            db.add(db_session)

        await db.flush()

    async def load_session_metadata(
        self, db: AsyncSession, session_id: str
    ) -> DBSession | None:
        return await db.get(DBSession, session_id)

    async def deactivate_session(
        self, db: AsyncSession, session_id: str
    ) -> None:
        await db.execute(
            update(DBSession)
            .where(DBSession.id == session_id)
            .values(is_active=False)
        )

    # Locations

    async def upsert_location(
        self, db: AsyncSession, session_id: str, location: Location
    ) -> None:
        existing = await db.get(DBLocation, location.id)
        if existing:
            existing.name = location.name
            existing.description = location.description
            existing.biome = location.biome
            existing.connected_locations = location.connected_locations
            existing.npc_ids = location.npc_ids
            existing.items_present = location.items_present
            existing.is_dangerous = location.is_dangerous
            existing.map_image_url = location.map_image_url
        else:
            db.add(DBLocation(
                id=location.id,
                session_id=session_id,
                name=location.name,
                description=location.description,
                biome=location.biome,
                connected_locations=location.connected_locations,
                npc_ids=location.npc_ids,
                items_present=location.items_present,
                is_dangerous=location.is_dangerous,
                map_image_url=location.map_image_url,
            ))

    async def get_all_locations(
        self, db: AsyncSession, session_id: str
    ) -> list[DBLocation]:
        result = await db.execute(
            select(DBLocation).where(DBLocation.session_id == session_id)
        )
        return list(result.scalars().all())

    async def update_location_map_url(
        self, db: AsyncSession, location_id: str, map_url: str
    ) -> None:
        await db.execute(
            update(DBLocation)
            .where(DBLocation.id == location_id)
            .values(map_image_url=map_url)
        )

    # NPCs

    async def upsert_npc(
        self, db: AsyncSession, session_id: str, npc: NPC
    ) -> None:
        existing = await db.get(DBNPC, npc.id)
        npc_data = npc.model_dump(mode="json")
        if existing:
            existing.disposition = npc.disposition_toward_player.value
            existing.trust_level = npc.trust_level
            existing.portrait_url = npc.portrait_url
            existing.npc_data = npc_data
            existing.last_interaction = npc.last_interaction
        else:
            db.add(DBNPC(
                id=npc.id,
                session_id=session_id,
                name=npc.name,
                role=npc.role,
                location_id=npc.location_id,
                disposition=npc.disposition_toward_player.value,
                trust_level=npc.trust_level,
                portrait_url=npc.portrait_url,
                npc_data=npc_data,
            ))

    async def update_npc_portrait(
        self, db: AsyncSession, npc_id: str, portrait_url: str
    ) -> None:
        await db.execute(
            update(DBNPC)
            .where(DBNPC.id == npc_id)
            .values(portrait_url=portrait_url)
        )

    async def get_npcs_at_location(
        self, db: AsyncSession, session_id: str, location_id: str
    ) -> list[DBNPC]:
        result = await db.execute(
            select(DBNPC).where(
                DBNPC.session_id == session_id,
                DBNPC.location_id == location_id,
            )
        )
        return list(result.scalars().all())

    # Quests 

    async def upsert_quest(
        self, db: AsyncSession, session_id: str, quest: Quest
    ) -> None:
        existing = await db.get(DBQuest, quest.id)
        if existing:
            existing.status = quest.status.value
            existing.objectives = quest.objectives
        else:
            db.add(DBQuest(
                id=quest.id,
                session_id=session_id,
                title=quest.title,
                description=quest.description,
                status=quest.status.value,
                giver_npc_id=quest.giver_npc_id,
                objectives=quest.objectives,
                reward_gold=quest.reward_gold,
                reward_items=quest.reward_items,
            ))

    async def get_active_quests(
        self, db: AsyncSession, session_id: str
    ) -> list[DBQuest]:
        result = await db.execute(
            select(DBQuest).where(
                DBQuest.session_id == session_id,
                DBQuest.status == QuestStatus.ACTIVE.value,
            )
        )
        return list(result.scalars().all())

    # World Events

    async def log_event(
        self,
        db: AsyncSession,
        session_id: str,
        event_text: str,
        event_type: str = "narrative",
        turn_number: int = 0,
    ) -> None:
        db.add(DBWorldEvent(
            session_id=session_id,
            event_text=event_text,
            event_type=event_type,
            turn_number=turn_number,
        ))

    async def get_recent_events(
        self,
        db: AsyncSession,
        session_id: str,
        limit: int = 10,
    ) -> list[DBWorldEvent]:
        result = await db.execute(
            select(DBWorldEvent)
            .where(DBWorldEvent.session_id == session_id)
            .order_by(DBWorldEvent.created_at.desc())
            .limit(limit)
        )
        return list(reversed(result.scalars().all()))

    # Bulk sync

    async def sync_session_to_db(
        self, db: AsyncSession, session: GameSession
    ) -> None:
        """
        Full write-through sync of an in-memory GameSession to PostgreSQL.
        Called after every player action and world event.
        """
        await self.upsert_session(db, session)

        for location in session.locations.values():
            await self.upsert_location(db, session.id, location)

        for npc in session.npcs.values():
            await self.upsert_npc(db, session.id, npc)

        for quest in session.quests.values():
            await self.upsert_quest(db, session.id, quest)

        await db.flush()
        logger.debug("Session %s synced to DB", session.id)
