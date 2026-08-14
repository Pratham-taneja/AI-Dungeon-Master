"""
The Dungeon Master LLM agent.

Implements the core ReAct-style loop:
  Observe (world state) → Think (LLM) → Act (stream narrative) → Update (parse JSON)

Responsibilities:
- Generate the opening narrative when a new game starts
- Process every player action and stream a narrative response
- Parse structured world-state updates from the LLM output
- Maintain the conversation history (sliding window)

"""

from __future__ import annotations

import json
import logging
import re
from typing import AsyncIterator

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from agents.prompts import (
    DM_CONTEXT_NO_EVENTS,
    DM_CONTEXT_NO_NPCS,
    DM_CONTEXT_NO_QUESTS,
    DM_CONTEXT_TEMPLATE,
    DM_SYSTEM_PROMPT,
    WORLD_GENERATION_PROMPT,
)
from config import get_settings
from models.schemas import (
    ConversationTurn,
    GameSession,
    Location,
    NPC,
    NPCDisposition,
    Quest,
    QuestStatus,
    WorldUpdatePayload,
)

logger = logging.getLogger(__name__)
settings = get_settings()

_JSON_BLOCK_RE = re.compile(r"```json\s*(.*?)\s*```", re.DOTALL)


def _deep_get(d: dict, key: str) -> object | None:
    """Recursively search a nested dict for *key* and return its value."""
    if key in d:
        return d[key]
    for v in d.values():
        if isinstance(v, dict):
            found = _deep_get(v, key)
            if found is not None:
                return found
    return None


def _normalise_json_str(raw: str) -> str:
    """
    LLMs sometimes echo {{ / }} from the prompt example.
    Replace them with single braces so json.loads works.
    Only do this outside of string values (simple heuristic: global replace is
    safe here because our JSON values never contain literal {{ or }}).
    """
    return raw.replace("{{", "{").replace("}}", "}")


def _extract_json_block(text: str) -> dict:
    # Try the fully-fenced case first (both opening and closing ```)
    match = _JSON_BLOCK_RE.search(text)
    if match:
        raw = _normalise_json_str(match.group(1))
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            repaired = _repair_truncated_json(raw)
            if repaired:
                return repaired

    # Fallback: opening ```json fence present, but no closing fence —
    # take everything after the opening marker, then apply brace-matching
    # extraction so any trailing prose after the JSON is correctly ignored.
    open_marker = "```json"
    idx = text.find(open_marker)
    if idx != -1:
        after_marker = text[idx + len(open_marker):]
        candidate = _normalise_json_str(after_marker)
        try:
            start = candidate.find("{")
            end = candidate.rfind("}")
            if start != -1 and end != -1 and start < end:
                return json.loads(candidate[start:end + 1])
        except json.JSONDecodeError:
            pass
        repaired = _repair_truncated_json(candidate)
        if repaired:
            return repaired

    # Last resort: no fence markers at all — brace-match the whole text.
    repaired = _repair_truncated_json(text)
    if repaired:
        return repaired

    logger.warning("DM JSON parse failed | raw: %s", text[:200])
    return {}


def _strip_json_block(text: str) -> str:
    cleaned = _JSON_BLOCK_RE.sub("", text)
    if cleaned == text:
        start = text.find("{")
        if start != -1:
            cleaned = text[:start]
    return cleaned.strip()


def _repair_truncated_json(text: str) -> dict | None:
    """
    Attempt to repair a JSON string truncated mid-stream by the LLM.
    Closes any open strings, arrays, and objects, then tries to parse.
    Returns None if still unparseable after repair.
    """
    if not text.strip():
        return None

    start = text.find("{")
    if start == -1:
        return None
    text = text[start:]

    depth_brace = 0
    depth_bracket = 0
    in_string = False
    escape_next = False
    last_complete_pos = 0

    for i, ch in enumerate(text):
        if escape_next:
            escape_next = False
            continue
        if ch == "\\" and in_string:
            escape_next = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            depth_brace += 1
        elif ch == "}":
            depth_brace -= 1
            if depth_brace == 0 and depth_bracket == 0:
                last_complete_pos = i + 1
        elif ch == "[":
            depth_bracket += 1
        elif ch == "]":
            depth_bracket -= 1

    candidate = text[:last_complete_pos] if last_complete_pos else text
    if in_string:
        candidate += '"'
    candidate += "]" * depth_bracket
    candidate += "}" * depth_brace

    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        return None


def _build_npc_summary(npcs: list[NPC]) -> str:
    if not npcs:
        return DM_CONTEXT_NO_NPCS
    lines = []
    for npc in npcs:
        lines.append(
            f"  • {npc.name} ({npc.role}) — "
            f"disposition: {npc.disposition_toward_player.value}, "
            f"trust: {npc.trust_level}"
        )
    return "\n".join(lines)


def _build_quest_summary(quests: list[Quest]) -> str:
    active = [q for q in quests if q.status == QuestStatus.ACTIVE]
    if not active:
        return DM_CONTEXT_NO_QUESTS
    return "\n".join(f"  • [{q.title}]: {', '.join(q.objectives)}" for q in active)


class DungeonMasterAgent:
    """
    The central DM agent that drives the entire game narrative.

    One instance per game session. Holds the conversation history
    and injects the world state into every prompt.
    """

    def __init__(self) -> None:
        self._llm = ChatOpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=settings.nvidia_api_key,
            model=settings.llm_model,
            max_tokens=settings.llm_max_tokens,
            temperature=settings.llm_temperature,
            streaming=True,
        )
        # Separate non-streaming LLM for world generation (we want full JSON)
        self._gen_llm = ChatOpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=settings.nvidia_api_key,
            model=settings.llm_model, # Kept original model for world gen
            temperature=0.9,
            max_tokens=8192,
            streaming=False,
        )

    # World Generation (called once at session start)

    async def generate_world(
        self,
        player_name: str,
        player_class: str,
        player_backstory: str,
        world_seed: str | None = None,
    ) -> dict:
        """
        Generate the complete starting world as a JSON blob.
        Returns the parsed dict that world/world_state.py will consume.

        Includes retry logic and truncation repair for robustness against
        LLMs that occasionally cut off long JSON responses.
        """
        prompt = WORLD_GENERATION_PROMPT.format(
            player_name=player_name,
            player_class=player_class,
            player_backstory=player_backstory,
            world_seed=world_seed or "random",
        )

        last_exc: Exception | None = None

        for attempt in range(1, 4):          # up to 3 attempts
            try:
                result = await self._gen_llm.ainvoke([HumanMessage(content=prompt)])
                raw: str = result.content    # type: ignore[assignment]

                # Strip markdown fence if present
                clean = _strip_json_block(raw) if "```" in raw else raw.strip()

                # Attempt 1: parse as-is
                try:
                    return json.loads(clean)
                except json.JSONDecodeError:
                    pass

                # Attempt 2: repair truncated JSON then parse
                repaired = _repair_truncated_json(clean)
                if repaired:
                    return repaired

                logger.warning(
                    "World gen attempt %d: JSON still invalid, retrying full generation...",
                    attempt,
                )

            except Exception as exc:
                last_exc = exc
                logger.warning("World gen attempt %d failed: %s", attempt, exc)

        raise ValueError(
            "World generation failed after 3 attempts — could not get valid JSON from LLM"
        ) from last_exc

    
    # Context Building

    def _build_context(self, session: GameSession) -> str:
        """Build the world-state context block injected into every turn."""
        player = session.player
        location = session.locations.get(player.current_location_id)
        location_name = location.name if location else "Unknown"
        location_desc = location.description if location else ""

        # NPCs at current location
        npcs_here: list[NPC] = []
        if location:
            npcs_here = [
                session.npcs[nid]
                for nid in location.npc_ids
                if nid in session.npcs
            ]

        return DM_CONTEXT_TEMPLATE.format(
            player_name=player.name,
            player_level=player.stats.level,
            player_class=player.player_class.value,
            player_health=player.stats.health,
            player_max_health=player.stats.max_health,
            player_gold=player.gold,
            location_name=location_name,
            location_desc=location_desc,
            location_description=location_desc,
            npcs_summary=_build_npc_summary(npcs_here),
            quests_summary=_build_quest_summary(list(session.quests.values())),
            inventory=", ".join(player.inventory) if player.inventory else "empty",
            world_events=(
                "\n".join(f"  • {e}" for e in session.world_events[-5:])
                if session.world_events
                else DM_CONTEXT_NO_EVENTS
            ),
        )

    def _build_message_history(
        self, session: GameSession
    ) -> list[HumanMessage | AIMessage]:
        """
        Convert session conversation history to LangChain message objects.
        Uses a sliding window to keep token count manageable.
        """
        history = session.conversation_history[-settings.max_history_turns * 2 :]
        messages: list[HumanMessage | AIMessage] = []
        for turn in history:
            if turn.role == "user":
                messages.append(HumanMessage(content=turn.content))
            else:
                messages.append(AIMessage(content=turn.content))
        return messages

    
    # Core Action Processing (streaming)
    

    async def stream_action(
        self,
        session: GameSession,
        player_action: str,
    ) -> AsyncIterator[tuple[str, WorldUpdatePayload | None]]:
        """
        Process a player action and stream the DM narrative response.

        Yields:
            (text_chunk, None) — for each narrative token chunk
            ("", world_update) — once at the end with parsed world changes

        The final yield always has an empty string and the WorldUpdatePayload.
        """
        context = self._build_context(session)
        system = f"{DM_SYSTEM_PROMPT}\n\n{context}"

        history_messages = self._build_message_history(session)

        all_messages = (
            [SystemMessage(content=system)]
            + history_messages
            + [HumanMessage(content=player_action)]
        )

        full_response_parts: list[str] = []
        # pending holds chars we haven't yielded yet (watching for ``` sentinel)
        pending = ""
        in_json_block = False

        async for chunk in self._llm.astream(all_messages):
            token: str = chunk.content
            full_response_parts.append(token)
            pending += token

            if in_json_block:
                continue

            # Check for standard markdown fences
            if "```json" in pending or "```" in pending:
                split_token = "```json" if "```json" in pending else "```"
                before, rest = pending.split(split_token, 1)
                if before:
                    yield (before, None)
                in_json_block = True
                continue
            
            # Fallback: look for the start of a raw JSON object, typically preceded by newline
            # We look for a `{` that isn't immediately preceded by a quote (which would be narrative dialog).
            idx = pending.find("{")
            if idx != -1:
                before = pending[:idx]
                # If there's no quote right before it, assume it's the start of the final JSON block
                if '"' not in before[-2:]:
                    if before:
                        yield (before, None)
                    in_json_block = True
                    continue

            # Safe to yield all but the last 5 chars (in case we're midway through typing "```js")
            if len(pending) > 5:
                yield (pending[:-5], None)
                pending = pending[-5:]

        # Yield any remaining pending text if we never hit a JSON block
        if pending and not in_json_block:
            # If it's just a hanging brace or tick, don't yield it
            if not ("{" in pending or "`" in pending):
                yield (pending, None)

        full_response = "".join(full_response_parts)
        structured = _extract_json_block(full_response)
        narrative_only = _strip_json_block(full_response)

        # Persist this turn to conversation history
        session.conversation_history.append(
            ConversationTurn(role="user", content=player_action)
        )
        session.conversation_history.append(
            ConversationTurn(role="assistant", content=narrative_only)
        )
        session.turn_count += 1

        # Build and yield the world update payload
        world_update = self._parse_world_update(structured, session, narrative_only)
        yield ("", world_update)

    
    # World Update Parsing
   

    def _parse_world_update(
        self, structured: dict, session: GameSession, narrative: str = ""
    ) -> WorldUpdatePayload:
        """
        Parse the structured JSON from the DM response into a WorldUpdatePayload
        and immediately apply safe mutations to the session.
        """
        update = WorldUpdatePayload()

        #  Scene mood & image prompt FIRST (always set, even on errors) 
        # Use _deep_get because the LLM sometimes nests these fields
        # inside npc_disposition_changes instead of at the top level.
        scene_mood = _deep_get(structured, "scene_mood") if structured else None
        if isinstance(scene_mood, str) and scene_mood.strip():
            update.scene_mood = scene_mood.strip()
        else:
            update.scene_mood = "neutral"

        scene_image_prompt = _deep_get(structured, "scene_image_prompt") if structured else None
        if isinstance(scene_image_prompt, str) and scene_image_prompt.strip():
            update.scene_image_prompt = scene_image_prompt.strip()
        else:
            # Build a rich fallback from the narrative text + location info
            update.scene_image_prompt = self._build_fallback_scene_prompt(
                narrative, session
            )

        logger.info("Scene fields — mood: %s, prompt: %s", update.scene_mood, update.scene_image_prompt)

        if not structured:
            return update

        # All other processing (wrapped in try-except for safety) 
        # imp: location_changed logic may still reference fields only from
        # top-level structured dict (not deeply nested)
        try:
            # Location change 
            if structured.get("location_changed") and structured.get("new_location_id"):
                new_loc_id: str = structured["new_location_id"]

                if new_loc_id not in session.locations:
                    new_loc = Location(
                        id=new_loc_id,
                        name=structured.get("new_location_name", new_loc_id.replace("_", " ").title()),
                        description=structured.get("new_location_description", ""),
                        biome=structured.get("new_location_biome", "unknown"),
                    )
                    session.locations[new_loc_id] = new_loc

                session.player.current_location_id = new_loc_id
                update.location_changed = True
                update.new_location = session.locations[new_loc_id]

            # NPC disposition changes 
            disposition_changes: dict = structured.get("npc_disposition_changes", {})
            for npc_id, new_disp_str in disposition_changes.items():
                if npc_id in session.npcs:
                    try:
                        new_disp = NPCDisposition(new_disp_str)
                        session.npcs[npc_id].disposition_toward_player = new_disp
                        update.npc_disposition_changes[npc_id] = new_disp
                    except ValueError:
                        logger.warning("Unknown disposition: %s", new_disp_str)

            # Items
            raw_items = structured.get("items_gained", [])
            items_gained: list[str] = [
                str(i) for i in (raw_items if isinstance(raw_items, list) else [])
                if i and not isinstance(i, dict)
            ]
            for item in items_gained:
                session.player.inventory.append(item)
            update.items_gained = items_gained

            # Player stats 
            health_delta: int = int(structured.get("player_health_delta", 0) or 0)
            gold_delta: int = int(structured.get("player_gold_delta", 0) or 0)

            if health_delta:
                session.player.stats.health = max(
                    0,
                    min(
                        session.player.stats.max_health,
                        session.player.stats.health + health_delta,
                    ),
                )
                update.player_stats_delta["health"] = health_delta

            if gold_delta:
                session.player.gold = max(0, session.player.gold + gold_delta)
                update.player_stats_delta["gold"] = gold_delta

            # World events 
            raw_events = structured.get("world_events", [])
            new_events: list[str] = [
                str(e) for e in (raw_events if isinstance(raw_events, list) else [])
                if e and isinstance(e, str)
            ]
            session.world_events.extend(new_events)

            # Quest updates 
            quest_updates: list[dict] = structured.get("quest_updates", [])
            if not isinstance(quest_updates, list):
                quest_updates = []

            for qu in quest_updates:
                if not isinstance(qu, dict):
                    continue

                qid: str = qu.get("quest_id") or qu.get("id") or ""

                if qid and qid not in session.quests:
                    try:
                        new_quest = Quest(
                            id=qid,
                            title=qu.get("quest_name") or qu.get("title") or qid,
                            description=qu.get("description") or qu.get("quest_description") or "",
                            objectives=qu.get("objectives", []),
                            reward_gold=int(
                                (qu.get("rewards") or {}).get("gold", 0)
                                or qu.get("reward_gold", 0)
                            ),
                            status=QuestStatus.AVAILABLE,
                        )
                        session.quests[qid] = new_quest
                        logger.debug("New quest registered from DM: %s", new_quest.title)
                    except Exception as exc:
                        logger.warning("Could not register new quest from DM: %s | %s", qu, exc)

                elif qid and qid in session.quests:
                    new_status_str = qu.get("status")
                    if new_status_str:
                        try:
                            session.quests[qid].status = QuestStatus(new_status_str)
                        except ValueError:
                            pass

            update.quest_updates = quest_updates

        except Exception as exc:
            logger.error("Error processing world update (scene fields preserved): %s", exc, exc_info=True)

        return update

 
    # Fallback Scene Prompt Generation

    @staticmethod
    def _build_fallback_scene_prompt(
        narrative: str, session: GameSession
    ) -> str:
        """
        Build a descriptive scene prompt from the narrative text when the
        LLM doesn't include scene_image_prompt in its JSON output.
        """
        # Take first two sentences of narrative (much better than generic fallback)
        if narrative:
            # Split on sentence-ending punctuation
            import re as _re
            sentences = _re.split(r'(?<=[.!?])\s+', narrative.strip())
            # Take first 2 sentences, cap at ~40 words
            snippet = " ".join(sentences[:2])
            words = snippet.split()
            if len(words) > 40:
                snippet = " ".join(words[:40])
        else:
            snippet = ""

        loc = (
            session.locations.get(session.player.current_location_id)
            if session.player
            else None
        )
        biome = loc.biome if loc and loc.biome else "fantasy landscape"
        loc_name = loc.name if loc and loc.name else "unknown location"

        if snippet:
            return f"{snippet}, dark fantasy {biome} atmosphere"
        else:
            return f"{biome} scene, {loc_name}, atmospheric dark fantasy"

