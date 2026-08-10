"""
dependencies.py — FastAPI dependency injection.

All shared singletons are created once and injected via Depends().
This keeps the app stateless at the route level.
"""

from functools import lru_cache

from agents.dm_agent import DungeonMasterAgent
from memory.npc_memory import SessionMemoryRegistry
from world.world_state import WorldStateManager

# Singletons 

_world_manager: WorldStateManager | None = None
_dm_agent: DungeonMasterAgent | None = None

# Registry is per-session — stored inside the world manager lookup
_session_registries: dict[str, SessionMemoryRegistry] = {}


def get_world_manager() -> WorldStateManager:
    global _world_manager
    if _world_manager is None:
        _world_manager = WorldStateManager()
    return _world_manager


def get_dm_agent() -> DungeonMasterAgent:
    global _dm_agent
    if _dm_agent is None:
        _dm_agent = DungeonMasterAgent()
    return _dm_agent


def get_memory_registry(session_id: str) -> SessionMemoryRegistry:
    if session_id not in _session_registries:
        _session_registries[session_id] = SessionMemoryRegistry(session_id)
    return _session_registries[session_id]
