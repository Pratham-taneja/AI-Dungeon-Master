"""
NPC persistent memory system backed by ChromaDB.

Each NPC gets its own ChromaDB collection.
Memories are stored as embeddings and retrieved via semantic similarity search,
enabling NPCs to "remember" past interactions without stuffing full history
into every prompt.

"""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime
from typing import Any

import chromadb
from chromadb.config import Settings as ChromaSettings
from langchain_huggingface import HuggingFaceEmbeddings

from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class NPCMemoryStore:
    """
    Manages the vector memory for a single NPC.

    Usage:
        store = NPCMemoryStore(npc_id="npc_innkeeper", session_id="abc123")
        await store.add_memory("Player paid double for a room, seemed wealthy")
        memories = await store.retrieve_relevant_memories("player asks for a discount")
    """

    def __init__(self, npc_id: str, session_id: str) -> None:
        self.npc_id = npc_id
        self.session_id = session_id
        # Collection name must be unique per NPC per session
        self.collection_name = (
            f"{settings.chroma_collection_prefix}{session_id[:8]}_{npc_id[:20]}"
        )
        self._client: chromadb.ClientAPI | None = None
        self._collection: chromadb.Collection | None = None
        self._embeddings: HuggingFaceEmbeddings | None = None

    def _get_client(self) -> chromadb.ClientAPI:
        if self._client is None:
            self._client = chromadb.PersistentClient(
                path=settings.chroma_persist_path,
                settings=ChromaSettings(anonymized_telemetry=False),
            )
        return self._client

    def _get_embeddings(self) -> HuggingFaceEmbeddings:
        if self._embeddings is None:
            self._embeddings = HuggingFaceEmbeddings(
                model_name="all-MiniLM-L6-v2",
            )
        return self._embeddings

    def _get_collection(self) -> chromadb.Collection:
        if self._collection is None:
            client = self._get_client()
            self._collection = client.get_or_create_collection(
                name=self.collection_name,
                metadata={"npc_id": self.npc_id, "session_id": self.session_id},
            )
        return self._collection

    def _make_memory_id(self, text: str) -> str:
        """Deterministic ID so duplicate memories are naturally deduped."""
        return hashlib.md5(f"{self.npc_id}:{text}".encode()).hexdigest()

    async def add_memory(
        self,
        memory_text: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """
        Embed and store a memory string for this NPC.

        Args:
            memory_text: A concise factual sentence describing what happened.
            metadata: Optional extra metadata (e.g. turn number, timestamp).
        """
        try:
            embeddings_model = self._get_embeddings()
            collection = self._get_collection()

            # Generate embedding synchronously (chromadb is sync)
            embedding = embeddings_model.embed_query(memory_text)

            meta = {
                "npc_id": self.npc_id,
                "session_id": self.session_id,
                "timestamp": datetime.utcnow().isoformat(),
                **(metadata or {}),
            }

            memory_id = self._make_memory_id(memory_text)

            # Upsert so re-adding the same fact doesn't create duplicates
            collection.upsert(
                ids=[memory_id],
                embeddings=[embedding],
                documents=[memory_text],
                metadatas=[meta],
            )
            logger.debug("Memory stored for NPC %s: %s", self.npc_id, memory_text[:60])

        except Exception as exc:
            logger.error("Failed to store memory for NPC %s: %s", self.npc_id, exc)

    async def retrieve_relevant_memories(
        self,
        query: str,
        top_k: int | None = None,
    ) -> list[str]:
        """
        Retrieve the most semantically relevant memories for a given query.

        Args:
            query: The current player action / context to match against.
            top_k: Number of memories to retrieve (defaults to settings value).

        Returns:
            List of memory strings, most relevant first.
        """
        k = top_k or settings.npc_memory_top_k
        try:
            collection = self._get_collection()

            # If collection is empty return early
            if collection.count() == 0:
                return []

            embeddings_model = self._get_embeddings()
            query_embedding = embeddings_model.embed_query(query)

            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=min(k, collection.count()),
                include=["documents", "distances"],
            )

            memories: list[str] = results["documents"][0] if results["documents"] else []
            logger.debug(
                "Retrieved %d memories for NPC %s (query: %s)",
                len(memories),
                self.npc_id,
                query[:40],
            )
            return memories

        except Exception as exc:
            logger.error(
                "Failed to retrieve memories for NPC %s: %s", self.npc_id, exc
            )
            return []

    async def clear_memories(self) -> None:
        """Wipe all memories for this NPC (used in testing / session reset)."""
        try:
            client = self._get_client()
            client.delete_collection(self.collection_name)
            self._collection = None
            logger.info("Cleared memories for NPC %s", self.npc_id)
        except Exception as exc:
            logger.error("Failed to clear memories for NPC %s: %s", self.npc_id, exc)

    def memory_count(self) -> int:
        """Return how many memories this NPC has stored."""
        try:
            return self._get_collection().count()
        except Exception:
            return 0



# Session-level memory registry

class SessionMemoryRegistry:
    """
    Holds all NPCMemoryStore instances for a single game session.
    Acts as a simple factory + cache so we never create duplicate stores.

    Usage:
        registry = SessionMemoryRegistry(session_id="abc123")
        store = registry.get_store("npc_innkeeper")
    """

    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        self._stores: dict[str, NPCMemoryStore] = {}

    def get_store(self, npc_id: str) -> NPCMemoryStore:
        if npc_id not in self._stores:
            self._stores[npc_id] = NPCMemoryStore(
                npc_id=npc_id,
                session_id=self.session_id,
            )
        return self._stores[npc_id]

    async def bulk_clear(self) -> None:
        """Clear all NPC memories in this session."""
        for store in self._stores.values():
            await store.clear_memories()
        self._stores.clear()

    def all_npc_ids(self) -> list[str]:
        return list(self._stores.keys())
