"""Initial schema — game_sessions, locations, npcs, quests, world_events



"""
from __future__ import annotations
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from alembic import op

revision: str = "initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    #  game_sessions 
    op.create_table(
        "game_sessions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("player_name", sa.String(64), nullable=False, index=True),
        sa.Column("player_class", sa.String(32), nullable=False),
        sa.Column("player_data", JSONB, nullable=False),
        sa.Column("turn_count", sa.Integer, default=0),
        sa.Column("is_active", sa.Boolean, default=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("last_action_at", sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    #  locations 
    op.create_table(
        "locations",
        sa.Column("id", sa.String(128), primary_key=True),
        sa.Column("session_id", sa.String(36), sa.ForeignKey("game_sessions.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("description", sa.Text, default=""),
        sa.Column("biome", sa.String(32), default="unknown"),
        sa.Column("connected_locations", JSONB, default=list),
        sa.Column("npc_ids", JSONB, default=list),
        sa.Column("items_present", JSONB, default=list),
        sa.Column("is_dangerous", sa.Boolean, default=False),
        sa.Column("map_image_url", sa.Text, nullable=True),
        sa.Column("discovered_at", sa.DateTime, server_default=sa.func.now()),
    )

    #  npcs 
    op.create_table(
        "npcs",
        sa.Column("id", sa.String(128), primary_key=True),
        sa.Column("session_id", sa.String(36), sa.ForeignKey("game_sessions.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("role", sa.String(64), nullable=False),
        sa.Column("location_id", sa.String(128), nullable=False, index=True),
        sa.Column("disposition", sa.String(32), default="neutral"),
        sa.Column("trust_level", sa.Integer, default=0),
        sa.Column("portrait_url", sa.Text, nullable=True),
        sa.Column("npc_data", JSONB, nullable=False),
        sa.Column("last_interaction", sa.DateTime, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    #  quests 
    op.create_table(
        "quests",
        sa.Column("id", sa.String(128), primary_key=True),
        sa.Column("session_id", sa.String(36), sa.ForeignKey("game_sessions.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("title", sa.String(256), nullable=False),
        sa.Column("description", sa.Text, default=""),
        sa.Column("status", sa.String(32), default="available", index=True),
        sa.Column("giver_npc_id", sa.String(128), nullable=True),
        sa.Column("objectives", JSONB, default=list),
        sa.Column("reward_gold", sa.Integer, default=0),
        sa.Column("reward_items", JSONB, default=list),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    #  world_events 
    op.create_table(
        "world_events",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("session_id", sa.String(36), sa.ForeignKey("game_sessions.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("event_text", sa.Text, nullable=False),
        sa.Column("event_type", sa.String(64), default="narrative"),
        sa.Column("turn_number", sa.Integer, default=0),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), index=True),
    )


def downgrade() -> None:
    op.drop_table("world_events")
    op.drop_table("quests")
    op.drop_table("npcs")
    op.drop_table("locations")
    op.drop_table("game_sessions")
