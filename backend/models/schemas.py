"""
All Pydantic schemas used across the application.

Covers:
  - Player / Session models
  - World state models (Location, Item, Quest)
  - NPC models (with personality schema)
  - Action request / response models
  - Streaming event models
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# Enums

class PlayerClass(str, Enum):
    WARRIOR = "warrior"
    MAGE = "mage"
    ROGUE = "rogue"
    CLERIC = "cleric"
    RANGER = "ranger"
    BARD = "bard"


class QuestStatus(str, Enum):
    AVAILABLE = "available"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"


class NPCDisposition(str, Enum):
    FRIENDLY = "friendly"
    NEUTRAL = "neutral"
    SUSPICIOUS = "suspicious"
    HOSTILE = "hostile"
    FEARFUL = "fearful"


class GameEventType(str, Enum):
    NARRATIVE = "narrative"
    WORLD_UPDATE = "world_update"
    NPC_REACTION = "npc_reaction"
    QUEST_UPDATE = "quest_update"
    ITEM_GAINED = "item_gained"
    COMBAT_START = "combat_start"
    ERROR = "error"
    DONE = "done"


# Player Models

class PlayerStats(BaseModel):
    health: int = Field(default=100, ge=0, le=100)
    max_health: int = Field(default=100, ge=1)
    mana: int = Field(default=50, ge=0)
    max_mana: int = Field(default=50, ge=0)
    strength: int = Field(default=10, ge=1, le=20)
    intelligence: int = Field(default=10, ge=1, le=20)
    dexterity: int = Field(default=10, ge=1, le=20)
    charisma: int = Field(default=10, ge=1, le=20)
    level: int = Field(default=1, ge=1)
    experience: int = Field(default=0, ge=0)


class PlayerCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=32)
    player_class: PlayerClass = PlayerClass.WARRIOR
    backstory: str = Field(
        default="A traveller seeking fortune and glory.",
        max_length=500,
    )


class Player(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    player_class: PlayerClass
    backstory: str
    stats: PlayerStats = Field(default_factory=PlayerStats)
    inventory: list[str] = Field(default_factory=list)
    gold: int = Field(default=10, ge=0)
    current_location_id: str = "starting_village"
    created_at: datetime = Field(default_factory=datetime.utcnow)


# Location Models

class Location(BaseModel):
    id: str
    name: str
    description: str
    biome: str = "village"                       # village | dungeon | forest | city | ruins
    connected_locations: list[str] = Field(default_factory=list)
    npc_ids: list[str] = Field(default_factory=list)
    items_present: list[str] = Field(default_factory=list)
    is_dangerous: bool = False
    map_image_url: str | None = None             # filled in Phase 4
    discovered_at: datetime = Field(default_factory=datetime.utcnow)


# NPC Models 


class NPCPersonality(BaseModel):
    """
    Personality schema injected into every NPC prompt.
    Keeping this structured forces the LLM to stay consistent.
    """
    traits: list[str] = Field(
        default_factory=list,
        description="e.g. ['greedy', 'cowardly', 'secretly kind']",
        max_length=5,
    )
    speech_style: str = Field(
        default="plain",
        description="e.g. 'archaic formal', 'gruff and short', 'flowery poetic'",
    )
    motivation: str = Field(
        default="survive and prosper",
        description="Core goal driving this NPC's behaviour",
    )
    secret: str = Field(
        default="",
        description="A secret the NPC hides — revealed only if trust is high",
    )
    disposition_toward_strangers: NPCDisposition = NPCDisposition.NEUTRAL


class NPCCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=64)
    role: str = Field(..., description="e.g. 'blacksmith', 'innkeeper', 'corrupt guard'")
    appearance: str = Field(default="", max_length=300)
    location_id: str
    personality: NPCPersonality = Field(default_factory=NPCPersonality)
    backstory: str = Field(default="", max_length=500)


class NPC(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    role: str
    appearance: str
    location_id: str
    personality: NPCPersonality
    backstory: str
    disposition_toward_player: NPCDisposition = NPCDisposition.NEUTRAL
    trust_level: int = Field(default=0, ge=-100, le=100)   # -100 = enemy, 100 = devoted ally
    portrait_url: str | None = None                        # filled in Phase 4
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_interaction: datetime | None = None


# Quest Models

class Quest(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    description: str
    giver_npc_id: str | None = None
    status: QuestStatus = QuestStatus.AVAILABLE
    objectives: list[str] = Field(default_factory=list)
    reward_gold: int = 0
    reward_items: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)


# Game Session Models


class ConversationTurn(BaseModel):
    role: str                            # "user" | "assistant"
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class GameSession(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    player: Player
    locations: dict[str, Location] = Field(default_factory=dict)
    npcs: dict[str, NPC] = Field(default_factory=dict)
    quests: dict[str, Quest] = Field(default_factory=dict)
    conversation_history: list[ConversationTurn] = Field(default_factory=list)
    world_events: list[str] = Field(default_factory=list)
    turn_count: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_action_at: datetime = Field(default_factory=datetime.utcnow)


# API Request / Response Models

class StartGameRequest(BaseModel):
    player: PlayerCreate
    world_seed: str | None = None           # optional seed for deterministic worlds


class StartGameResponse(BaseModel):
    session_id: str
    player: Player
    opening_narrative: str
    current_location: Location


class PlayerActionRequest(BaseModel):
    session_id: str
    action: str = Field(..., min_length=1, max_length=1000)
    target_npc_id: str | None = None        # set when action targets a specific NPC


class WorldStateResponse(BaseModel):
    session_id: str
    player: Player
    current_location: Location
    npcs_present: list[NPC]
    active_quests: list[Quest]
    turn_count: int


# Streaming Event Models (SSE payloads)

class StreamEvent(BaseModel):
    """
    Every SSE event sent to the frontend is one of these.
    The frontend discriminates on `event_type`.
    """
    event_type: GameEventType
    data: Any = None                        # narrative chunk | structured update
    session_id: str = ""
    turn: int = 0


class NarrativeChunk(BaseModel):
    text: str                               # partial token chunk
    is_final: bool = False


class WorldUpdatePayload(BaseModel):
    location_changed: bool = False
    new_location: Location | None = None
    npc_disposition_changes: dict[str, NPCDisposition] = Field(default_factory=dict)
    items_gained: list[str] = Field(default_factory=list)
    quest_updates: list[dict[str, Any]] = Field(default_factory=list)
    player_stats_delta: dict[str, int] = Field(default_factory=dict)
    scene_mood: str | None = None                           # peaceful | tense | dangerous | mysterious | dramatic | neutral
    scene_image_prompt: str | None = None                   # short visual description for scene image gen

