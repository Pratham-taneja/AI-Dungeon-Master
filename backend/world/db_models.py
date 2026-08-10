"""
SQLAlchemy ORM models for persistent world state.

Full PostgreSQL persistence for:
  - GameSession metadata
  - Location graph nodes
  - NPC records
  - Quest records
  - WorldEvent log
  - Player state

JSON columns store the rich nested data (personality, stats, inventory)
while scalar columns enable fast indexed queries.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.utcnow()


## Session 
class DBSession(Base):
    __tablename__ = "game_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    player_name: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    player_class: Mapped[str] = mapped_column(String(32), nullable=False)
    player_data: Mapped[dict] = mapped_column(JSONB, nullable=False)       # full Player schema
    turn_count: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    last_action_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)

    locations: Mapped[list[DBLocation]] = relationship(
        "DBLocation", back_populates="session", cascade="all, delete-orphan"
    )
    npcs: Mapped[list[DBNPC]] = relationship(
        "DBNPC", back_populates="session", cascade="all, delete-orphan"
    )
    quests: Mapped[list[DBQuest]] = relationship(
        "DBQuest", back_populates="session", cascade="all, delete-orphan"
    )
    world_events: Mapped[list[DBWorldEvent]] = relationship(
        "DBWorldEvent", back_populates="session", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<DBSession id={self.id} player={self.player_name}>"



# Location (world graph node)


class DBLocation(Base):
    __tablename__ = "locations"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("game_sessions.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    biome: Mapped[str] = mapped_column(String(32), default="unknown")
    connected_locations: Mapped[list] = mapped_column(JSONB, default=list)  # list[str] of location ids
    npc_ids: Mapped[list] = mapped_column(JSONB, default=list)
    items_present: Mapped[list] = mapped_column(JSONB, default=list)
    is_dangerous: Mapped[bool] = mapped_column(Boolean, default=False)
    map_image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    discovered_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    session: Mapped[DBSession] = relationship("DBSession", back_populates="locations")

    def __repr__(self) -> str:
        return f"<DBLocation id={self.id} name={self.name}>"


# NPC


class DBNPC(Base):
    __tablename__ = "npcs"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("game_sessions.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    role: Mapped[str] = mapped_column(String(64), nullable=False)
    location_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    disposition: Mapped[str] = mapped_column(String(32), default="neutral")
    trust_level: Mapped[int] = mapped_column(Integer, default=0)
    portrait_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    npc_data: Mapped[dict] = mapped_column(JSONB, nullable=False)           # full NPC schema
    last_interaction: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    session: Mapped[DBSession] = relationship("DBSession", back_populates="npcs")

    def __repr__(self) -> str:
        return f"<DBNPC id={self.id} name={self.name}>"



# Quest


class DBQuest(Base):
    __tablename__ = "quests"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("game_sessions.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(32), default="available", index=True)
    giver_npc_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    objectives: Mapped[list] = mapped_column(JSONB, default=list)
    reward_gold: Mapped[int] = mapped_column(Integer, default=0)
    reward_items: Mapped[list] = mapped_column(JSONB, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    session: Mapped[DBSession] = relationship("DBSession", back_populates="quests")

    def __repr__(self) -> str:
        return f"<DBQuest id={self.id} title={self.title} status={self.status}>"



# World Event Log


class DBWorldEvent(Base):
    __tablename__ = "world_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("game_sessions.id", ondelete="CASCADE"), index=True
    )
    event_text: Mapped[str] = mapped_column(Text, nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), default="narrative")  # narrative | autonomous | combat
    turn_number: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now, index=True)

    session: Mapped[DBSession] = relationship("DBSession", back_populates="world_events")

    def __repr__(self) -> str:
        return f"<DBWorldEvent id={self.id} session={self.session_id}>"
