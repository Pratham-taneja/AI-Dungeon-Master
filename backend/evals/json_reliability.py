"""
DM structured-output reliability eval.

Measures how often the DungeonMasterAgent's structured JSON block:
  - parses cleanly on the first attempt ("clean")
  - fails to parse cleanly but is recovered by the truncation-repair pass ("repaired")
  - fails entirely, even after repair ("failed")
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from langchain_core.messages import HumanMessage, SystemMessage

from agents.dm_agent import (
    DungeonMasterAgent,
    _extract_json_block,
    _strip_json_block,
    _JSON_BLOCK_RE,
)
from models.schemas import PlayerClass, PlayerCreate, ConversationTurn
from world.world_state import WorldStateManager
from agents.prompts import DM_SYSTEM_PROMPT

SAMPLE_ACTIONS = [
    "I look around the room carefully.",
    "I draw my weapon and attack the nearest enemy.",
    "I try to persuade the guard to let me pass.",
    "I search the chest for anything valuable.",
    "I walk north toward the forest.",
    "I ask the innkeeper about rumors in town.",
    "I attempt to pick the lock on the door.",
    "I rest by the fire to recover my strength.",
    "I try to fly to the moon using my sword as a rocket.",
    "I offer the merchant my gold for information.",
    "I sneak past the sleeping dragon.",
    "I shout a challenge to anyone listening.",
    "I examine the strange runes on the wall.",
    "I drink the unknown potion I found earlier.",
    "I retreat and set up camp for the night.",
]


@dataclass
class EvalResult:
    total: int = 0
    clean: int = 0
    repaired: int = 0
    failed: int = 0
    failures: list[str] = field(default_factory=list)

    def record(self, status: str, raw_snippet: str = "") -> None:
        self.total += 1
        if status == "clean":
            self.clean += 1
        elif status == "repaired":
            self.repaired += 1
        else:
            self.failed += 1
            self.failures.append(raw_snippet)

    def summary(self) -> dict:
        if self.total == 0:
            return {"total": 0}
        return {
            "total": self.total,
            "clean": self.clean,
            "clean_pct": round(100 * self.clean / self.total, 1),
            "repaired": self.repaired,
            "repaired_pct": round(100 * self.repaired / self.total, 1),
            "failed": self.failed,
            "failed_pct": round(100 * self.failed / self.total, 1),
        }


def _classify_json_output(raw_response: str) -> str:
    result = _extract_json_block(raw_response)
    if not result:
        return "failed"
    match = _JSON_BLOCK_RE.search(raw_response)
    if match:
        try:
            json.loads(match.group(1).replace("{{", "{").replace("}}", "}"))
            return "clean"
        except json.JSONDecodeError:
            return "repaired"
    return "repaired"


async def run_eval(num_turns: int) -> EvalResult:
    dm = DungeonMasterAgent()
    result = EvalResult()

    print("Generating a fresh world for the eval session...\n")
    world_data = await dm.generate_world(
        player_name="EvalRunner",
        player_class=PlayerClass.WARRIOR.value,
        player_backstory="A test character used purely for evaluation.",
    )

    wm = WorldStateManager()
    player = PlayerCreate(
        name="EvalRunner", player_class=PlayerClass.WARRIOR,
        backstory="A test character used purely for evaluation.",
    )
    session = await wm.create_session(player, world_data)

    actions = (SAMPLE_ACTIONS * ((num_turns // len(SAMPLE_ACTIONS)) + 1))[:num_turns]

    for i, action in enumerate(actions, 1):
        context = dm._build_context(session)
        full_system = f"{DM_SYSTEM_PROMPT}\n\n{context}"
        history_messages = dm._build_message_history(session)

        messages = (
            [SystemMessage(content=full_system)]
            + history_messages
            + [HumanMessage(content=action)]
        )

        try:
            response = await dm._llm.ainvoke(messages)
            raw_text: str = response.content
        except Exception as exc:
            print(f"  [{i}/{num_turns}] LLM call failed: {exc}")
            result.record("failed", str(exc))
            continue

        status = _classify_json_output(raw_text)
        result.record(status, raw_text)

        narrative_only = _strip_json_block(raw_text)
        session.conversation_history.append(ConversationTurn(role="user", content=action))
        session.conversation_history.append(ConversationTurn(role="assistant", content=narrative_only))
        session.turn_count += 1

        print(f"  [{i}/{num_turns}] action={action[:40]!r:42} -> {status}")

    await wm.delete_session(session.id)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="DM structured-output JSON reliability eval")
    parser.add_argument("--turns", type=int, default=20, help="Number of turns to sample")
    args = parser.parse_args()

    result = asyncio.run(run_eval(args.turns))

    print("\n" + "=" * 60)
    print("JSON RELIABILITY EVAL — RESULTS")
    print("=" * 60)
    summary = result.summary()
    print(f"  Total turns sampled : {summary['total']}")
    print(f"  Clean parse         : {summary['clean']} ({summary['clean_pct']}%)")
    print(f"  Repaired (truncated): {summary['repaired']} ({summary['repaired_pct']}%)")
    print(f"  Failed entirely     : {summary['failed']} ({summary['failed_pct']}%)")
    print("=" * 60)

    if result.failures:
        print("\nFull failed responses:")
        for f in result.failures[:5]:
            print(f"\n--- FAILURE ---\n{f}\n")

    out_path = Path(__file__).parent / "json_reliability_results.json"
    out_path.write_text(json.dumps(summary, indent=2))
    print(f"\nSaved summary to {out_path}")


if __name__ == "__main__":
    main()
