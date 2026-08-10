"""
NPC dialogue agent with persistent memory.

Each NPC interaction:
1. Retrieves relevant memories from ChromaDB
2. Injects personality + memories into system prompt
3. Streams the NPC's in-character response
4. Parses structured JSON output to update disposition/trust
5. Stores a summarised memory of the interaction

"""

from __future__ import annotations

import json
import logging
import re
from typing import AsyncIterator

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from agents.prompts import (
    MEMORY_SUMMARISE_PROMPT,
    NPC_SYSTEM_PROMPT,
)
from config import get_settings
from memory.npc_memory import NPCMemoryStore
from models.schemas import NPC, NPCDisposition

logger = logging.getLogger("npc_agent")
settings = get_settings()

# JSON block regex — matches the ```json ... ``` block in model output
_JSON_BLOCK_RE = re.compile(r"```json\s+(.*?)\s+```", re.DOTALL)


def _normalise_json_str(raw: str) -> str:
    return raw.replace("{{", "{").replace("}}", "}")


def _extract_json_block(text: str) -> dict:
    """
    Extract and parse the structured JSON block from NPC response.
    Handles {{ }} escaping LLMs sometimes copy from prompt examples.
    Returns empty dict on any failure so the game never crashes.
    """
    match = _JSON_BLOCK_RE.search(text)
    if not match:
        return {}
    raw = _normalise_json_str(match.group(1))
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.warning("NPC JSON parse failed: %s", exc)
        return {}


def _strip_json_block(text: str) -> str:
    """Remove the JSON block from the narrative so frontend only sees dialogue."""
    return _JSON_BLOCK_RE.sub("", text).strip()


class NPCAgent:
    """
    Stateless agent that handles one NPC conversation turn.

    Usage:
        agent = NPCAgent(npc=npc_obj, memory_store=store)
        async for chunk in agent.stream_response(player_input, player_name):
            print(chunk, end="", flush=True)
        result = await agent.get_interaction_result()
    """

    def __init__(self, npc: NPC, memory_store: NPCMemoryStore) -> None:
        self.npc = npc
        self.memory_store = memory_store
        self._llm = ChatOpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=settings.nvidia_api_key,
            model=settings.llm_model,
            temperature=settings.llm_temperature,
            max_tokens=settings.llm_max_tokens,
            streaming=True,
        )
        self._summariser_llm = ChatOpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=settings.nvidia_api_key,
            model=settings.llm_summariser_model,
            temperature=0.2,
            max_tokens=80,
        )
        self._last_full_response: str = ""
        self._last_structured: dict = {}

    def _build_system_prompt(self, memories: list[str]) -> str:
        """Inject NPC data + memories into the system prompt template."""
        p = self.npc.personality
        memory_block = (
            "\n".join(f"- {m}" for m in memories)
            if memories
            else "  (no memories of this player yet)"
        )
        return NPC_SYSTEM_PROMPT.format(
            npc_name=self.npc.name,
            npc_role=self.npc.role,
            npc_appearance=self.npc.appearance or "nondescript",
            npc_backstory=self.npc.backstory or "Unknown origins.",
            personality_traits=", ".join(p.traits) if p.traits else "none notable",
            speech_style=p.speech_style,
            motivation=p.motivation,
            secret=p.secret or "none",
            disposition=self.npc.disposition_toward_player.value,
            trust_level=self.npc.trust_level,
            memories=memory_block,
        )

    async def stream_response(
        self,
        player_input: str,
        player_name: str,
    ) -> AsyncIterator[str]:
        """
        Stream the NPC's dialogue response token by token.
        Strips the JSON metadata block before yielding to frontend.

        Yields:
            Text chunks (dialogue only, no JSON).
        """
        memories = await self.memory_store.retrieve_relevant_memories(player_input)
        system_prompt = self._build_system_prompt(memories)

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"{player_name} says: {player_input}"),
        ]

        full_response_parts: list[str] = []
        buffer = ""

        async for chunk in self._llm.astream(messages):
            token: str = chunk.content  # type: ignore[assignment]
            full_response_parts.append(token)
            buffer += token

            # Yield tokens that are definitely not part of the JSON block.
            # We start buffering when we see ``` and flush when block ends.
            if "```" in buffer:
                # Split on the start of JSON block
                pre_json, *rest = buffer.split("```", 1)
                if pre_json:
                    yield pre_json
                buffer = "```" + (rest[0] if rest else "")
                # Once the closing ``` arrives, consume the whole block silently
                if buffer.count("```") >= 2:
                    buffer = ""
            elif "```" not in buffer and not buffer.startswith("`"):
                yield buffer
                buffer = ""

        # Flush any remaining buffer that didn't contain JSON
        if buffer and "```" not in buffer:
            yield buffer

        self._last_full_response = "".join(full_response_parts)
        self._last_structured = _extract_json_block(self._last_full_response)

        # Persist a summarised memory of this interaction
        await self._persist_memory(player_input, self._last_full_response)

    async def get_interaction_result(self) -> dict:
        """
        Return the structured metadata from the last interaction.
        Call this AFTER fully consuming stream_response().
        """
        return self._last_structured

    async def apply_interaction_result(self) -> None:
        """
        Apply disposition/trust changes from the last interaction to the NPC object.
        Mutates self.npc in place.
        """
        result = self._last_structured
        if not result:
            return

        trust_delta: int = result.get("trust_change", 0)
        new_trust = max(-100, min(100, self.npc.trust_level + trust_delta))
        self.npc.trust_level = new_trust

        disposition_delta: int = result.get("disposition_change", 0)
        if disposition_delta != 0:
            dispositions = list(NPCDisposition)
            current_idx = dispositions.index(self.npc.disposition_toward_player)
            new_idx = max(0, min(len(dispositions) - 1, current_idx + disposition_delta))
            self.npc.disposition_toward_player = dispositions[new_idx]

        logger.debug(
            "NPC %s updated: trust=%d disposition=%s",
            self.npc.name,
            self.npc.trust_level,
            self.npc.disposition_toward_player,
        )

    async def _persist_memory(
        self, player_input: str, full_npc_response: str
    ) -> None:
        """Summarise the interaction and store it in the NPC's memory."""
        try:
            dialogue_only = _strip_json_block(full_npc_response)
            interaction_text = (
                f"Player: {player_input}\n{self.npc.name}: {dialogue_only}"
            )

            summary_prompt = MEMORY_SUMMARISE_PROMPT.format(
                interaction_text=interaction_text
            )
            result = await self._summariser_llm.ainvoke(
                [HumanMessage(content=summary_prompt)]
            )
            summary: str = result.content.strip()  # type: ignore[union-attr]

            await self.memory_store.add_memory(
                summary,
                metadata={"player_input": player_input[:100]},
            )
        except Exception as exc:
            logger.error("Memory persistence failed for NPC %s: %s", self.npc.id, exc)
