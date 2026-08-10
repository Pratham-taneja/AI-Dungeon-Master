"""
Terminal-based game loop.

Run this to verify the DM agent, world generation, and streaming all work
before wiring up the frontend. No server required.

Usage:
    python terminal_game.py

Requirements:
    - NVIDIA_API_KEY set in .env or environment
    - pip install -r requirements.txt
"""

from __future__ import annotations

import asyncio
import os
import sys


# Ensure backend/ is on the path when running from project root
sys.path.insert(0, os.path.dirname(__file__))

from database import AsyncSessionLocal
from world.world_graph import WorldGraphDB

from dotenv import load_dotenv
load_dotenv()

from agents.dm_agent import DungeonMasterAgent
from models.schemas import PlayerClass, PlayerCreate
from world.world_state import WorldStateManager

# ANSI colour helpers
RESET  = "\033[0m"
BOLD   = "\033[1m"
CYAN   = "\033[96m"
YELLOW = "\033[93m"
GREEN  = "\033[92m"
RED    = "\033[91m"
DIM    = "\033[2m"
MAGENTA = "\033[95m"


def c(text: str, colour: str) -> str:
    return f"{colour}{text}{RESET}"


def print_separator(char: str = "─", width: int = 70) -> None:
    print(c(char * width, DIM))


def print_header() -> None:
    print("\n")
    print(c("╔══════════════════════════════════════════════════════════════╗", GREEN))
    print(c("║           🎮  AI GAME MASTER — INFINITE RPG                  ║", GREEN))
    print(c("║                    Terminal Demo                             ║", GREEN))
    print(c("╚══════════════════════════════════════════════════════════════╝", GREEN))
    print()


def choose_class() -> PlayerClass:
    classes = list(PlayerClass)
    print(c("Choose your class:", YELLOW))
    for i, cls in enumerate(classes, 1):
        print(f"  {c(str(i), GREEN)}. {cls.value.title()}")
    while True:
        try:
            choice = int(input(c("\nEnter number: ", YELLOW))) - 1
            if 0 <= choice < len(classes):
                return classes[choice]
        except (ValueError, IndexError):
            pass
        print(c("Invalid choice, try again.", RED))


async def create_character() -> PlayerCreate:
    print(c("=== CHARACTER CREATION =+=\n", YELLOW))

    name = input(c("Enter your character's name: ", CYAN)).strip()
    while not name or len(name) < 2:
        print(c("Name must be at least 2 characters.", RED))
        name = input(c("Enter your character's name: ", CYAN)).strip()

    player_class = choose_class()

    print(c("\nWrite a short backstory (or press Enter for default):", YELLOW))
    backstory = input("> ").strip()
    if not backstory:
        backstory = f"A wandering {player_class.value} seeking adventure and fortune."

    return PlayerCreate(name=name, player_class=player_class, backstory=backstory)


async def main() -> None:
    print_header()

    # Validate API key
    from config import get_settings
    settings = get_settings()
    # Auth check 
    if not settings.nvidia_api_key or settings.nvidia_api_key.startswith("your-nvidia"):
        print(c("ERROR: Set NVIDIA_API_KEY in your .env file first.", RED))
        print("  1. Copy .env.example to .env")
        print("  2. Add your key from https://build.nvidia.com")
        sys.exit(1)
    #  Character creation 
    player_data = await create_character()

    print(c("\n⏳ Generating your world — this takes ~10 seconds...\n", DIM))

    dm = DungeonMasterAgent()
    wm = WorldStateManager()
    world_graph_db = WorldGraphDB()
    #  Generate world 
    try:
        world_data = await dm.generate_world(
            player_name=player_data.name,
            player_class=player_data.player_class.value,
            player_backstory=player_data.backstory,
        )
    except Exception as exc:
        print(c(f"\n World generation failed: {exc}", RED))
        sys.exit(1)

    session = await wm.create_session(player_data, world_data)

    #  Print opening 
    print_separator("═")
    print(c("\n YOUR STORY BEGINS...\n", MAGENTA))
    print(world_data.get("opening_narrative", "Your adventure begins..."))
    print_separator()

    loc = session.locations.get(session.player.current_location_id)
    if loc:
        print(c(f"\n Location: {loc.name}", CYAN))
        print(c(f"   {loc.description}", DIM))

    npcs_here = wm.get_npcs_at_location(session, session.player.current_location_id)
    if npcs_here:
        print(c("\n👥 People here:", YELLOW))
        for npc in npcs_here:
            print(f"   • {c(npc.name, GREEN)} — {npc.role}")

    quests = list(session.quests.values())
    if quests:
        print(c("\n Available quests:", YELLOW))
        for q in quests:
            print(f"   • {c(q.title, GREEN)}: {q.description}")

    print_separator("═")

    #  Game loop 
    print(c("\n Type your action and press Enter. Type 'quit' to exit.\n", DIM))

    while True:
        print()
        try:
            action = input(c(f"  {session.player.name} > ", YELLOW)).strip()
        except (EOFError, KeyboardInterrupt):
            print(c("\n\nFarewell, adventurer!", CYAN))
            break

        if not action:
            continue

        if action.lower() in ("quit", "exit", "q"):
            print(c("\nFarewell, adventurer! Your legend will be remembered.", CYAN))
            break

        if action.lower() == "status":
            p = session.player
            print(c(f"\n[{p.name} — Level {p.stats.level} {p.player_class.value.title()}]", CYAN))
            print(f"  HP: {p.stats.health}/{p.stats.max_health}  |  Gold: {p.gold}")
            print(f"  Inventory: {', '.join(p.inventory) or 'empty'}")
            loc = session.locations.get(p.current_location_id)
            if loc:
                print(f"  Location: {loc.name}")
            continue

        # Stream DM response 
        print()
        print(c(" Dungeon Master:", MAGENTA))
        print_separator()

        try:
            async for text_chunk, world_update in dm.stream_action(session, action):
                if text_chunk:
                    print(text_chunk, end="", flush=True)

                if world_update:
                    await wm.save_session(session)
                    if world_update:
                        try:
                            async with AsyncSessionLocal() as db:
                                await world_graph_db.sync_session_to_db(db, session)
                                await db.commit()
                        except Exception as exc:
                            print(c(f"\n  (Postgres sync failed: {exc})", DIM))

                    # Print structured changes summary
                    if world_update.location_changed and world_update.new_location:
                        print(c(f"\n\n You are now in: {world_update.new_location.name}", CYAN))

                    if world_update.items_gained:
                        print(c(f"\n✨ Items gained: {', '.join(world_update.items_gained)}", GREEN))

                    if world_update.player_stats_delta.get("health"):
                        delta = world_update.player_stats_delta["health"]
                        colour = GREEN if delta > 0 else RED
                        sign = "+" if delta > 0 else ""
                        print(c(f"\n  Health: {sign}{delta} (now {session.player.stats.health})", colour))

        except Exception as exc:
            print(c(f"\n\n Error: {exc}", RED))

        print()
        print_separator()

    await wm.delete_session(session.id)


if __name__ == "__main__":
    asyncio.run(main())
