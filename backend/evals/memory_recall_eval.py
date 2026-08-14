"""
NPC memory retrieval accuracy eval (recall@K).

Measures whether the ChromaDB-backed semantic memory store (memory/npc_memory.py)
actually retrieves the *relevant* memory for a differently-worded follow-up
query — the core promise of the RAG-style memory system: NPCs should recall
facts even when the player doesn't use the exact same wording that created
that memory.

For each test case:
  1. A memory is stored (as if the NPC learned this fact in an earlier turn).
  2. A related but differently-phrased query is issued.
  3. We check whether the *expected* memory is present in the top-K retrieved
     results — this is a recall@K measurement, not an exact-match check.

    No API key or database required — this eval only exercises the local
    HuggingFace embedding model + ChromaDB, entirely offline.
"""

from __future__ import annotations

import asyncio
import sys
import uuid
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from memory.npc_memory import NPCMemoryStore

# Each test case: a memory as it would actually be stored (a compressed,
# summarised sentence — matching what MEMORY_SUMMARISE_PROMPT produces),
# a follow-up query phrased differently from the memory text, and a keyword
# that must appear in a retrieved memory for the retrieval to count as a hit.
TEST_CASES = [
    {
        "memory": "The player paid double the room price and seemed wealthy, mentioning they'd sold a family heirloom.",
        "query": "Does this guest have money to spare?",
        "expect_keyword": "wealthy",
    },
    {
        "memory": "The player admitted to being afraid of the dark forest north of the village.",
        "query": "How does the player feel about traveling into dangerous woods?",
        "expect_keyword": "forest",
    },
    {
        "memory": "The player promised to return the stolen sword to the blacksmith by next week.",
        "query": "Did the player make any promises about returning items?",
        "expect_keyword": "sword",
    },
    {
        "memory": "The player revealed they used to serve in the king's guard before deserting.",
        "query": "What does the player's military background look like?",
        "expect_keyword": "guard",
    },
    {
        "memory": "The player asked suspicious questions about the mayor's whereabouts last night.",
        "query": "Has the player shown interest in the mayor?",
        "expect_keyword": "mayor",
    },
    {
        "memory": "The player gifted a rare healing herb, earning goodwill.",
        "query": "Has this visitor ever given me anything?",
        "expect_keyword": "herb",
    },
    {
        "memory": "The player threatened violence when refused service at the tavern.",
        "query": "Should I be cautious about this person's temper?",
        "expect_keyword": "threat",
    },
    {
        "memory": "The player mentioned they are searching for a missing sibling somewhere in the region.",
        "query": "Is the player looking for a family member?",
        "expect_keyword": "sibling",
    },
]


@dataclass
class RecallResult:
    total: int = 0
    hits: int = 0
    misses: list[dict] = field(default_factory=list)

    def record(self, hit: bool, case: dict, retrieved: list[str]) -> None:
        self.total += 1
        if hit:
            self.hits += 1
        else:
            self.misses.append({**case, "retrieved": retrieved})

    def summary(self) -> dict:
        if self.total == 0:
            return {"total": 0}
        return {
            "total": self.total,
            "hits": self.hits,
            "recall_at_k_pct": round(100 * self.hits / self.total, 1),
        }


async def run_eval(top_k: int = 3) -> RecallResult:
    result = RecallResult()
    session_id = f"eval_{uuid.uuid4().hex[:8]}"
    npc_id = "eval_npc"

    store = NPCMemoryStore(npc_id=npc_id, session_id=session_id)

    print(f"Running {len(TEST_CASES)} memory recall test cases (top_k={top_k})...\n")

    for i, case in enumerate(TEST_CASES, 1):
        # Store the memory (simulating an earlier interaction being summarised
        # and persisted, same as npc_agent.py's _persist_memory does).
        await store.add_memory(case["memory"])

        # Query with the differently-worded follow-up.
        retrieved = await store.retrieve_relevant_memories(case["query"], top_k=top_k)

        hit = any(case["expect_keyword"].lower() in mem.lower() for mem in retrieved)
        result.record(hit, case, retrieved)

        status = "HIT " if hit else "MISS"
        print(f"  [{i}/{len(TEST_CASES)}] {status} — query: {case['query'][:50]!r}")
        if not hit:
            print(f"           expected keyword: {case['expect_keyword']!r}")
            print(f"           retrieved: {retrieved}")

    await store.clear_memories()
    return result


def main() -> None:
    result = asyncio.run(run_eval())

    print("\n" + "=" * 60)
    print("NPC MEMORY RECALL EVAL — RESULTS")
    print("=" * 60)
    summary = result.summary()
    print(f"  Total test cases : {summary['total']}")
    print(f"  Hits (recall@K)  : {summary['hits']} ({summary['recall_at_k_pct']}%)")
    print("=" * 60)

    if result.misses:
        print(f"\n{len(result.misses)} missed case(s) — see output above for detail.")

    import json
    out_path = Path(__file__).parent / "memory_recall_results.json"
    out_path.write_text(json.dumps(summary, indent=2))
    print(f"\nSaved summary to {out_path}")


if __name__ == "__main__":
    main()