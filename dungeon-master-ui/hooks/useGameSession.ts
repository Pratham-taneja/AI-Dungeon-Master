"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  getWorldState,
  startGame,
  streamNpcTalk,
  streamPlayerAction,
  generateAllAssets,
  generateSceneImage,
} from "@/lib/api";
import type {
  ChronicleEntry,
  Location,
  ModalLine,
  NPC,
  Player,
  PlayerClass,
  Quest,
} from "@/lib/types";

type Screen = "create" | "game";

function makeId(prefix: string): string {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

export function useGameSession() {
  // Screen / character creation
  const [screen, setScreen] = useState<Screen>("create");
  const [name, setName] = useState("");
  const [playerClass, setPlayerClass] = useState<PlayerClass>("ranger");
  const [backstory, setBackstory] = useState("");
  const [beginning, setBeginning] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  // Session
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [player, setPlayer] = useState<Player | null>(null);
  const [location, setLocation] = useState<Location | null>(null);
  const [npcs, setNpcs] = useState<NPC[]>([]);
  const [quests, setQuests] = useState<Quest[]>([]);
  const [mood, setMood] = useState("neutral");
  const [sceneImageUrl, setSceneImageUrl] = useState<string | null>(null);
  const lastScenePromptRef = useRef<string | null>(null);

  // Chronicle
  const [entries, setEntries] = useState<ChronicleEntry[]>([]);
  const [showFull, setShowFull] = useState(false);
  const [streaming, setStreaming] = useState(false);
  const [streamText, setStreamText] = useState("");
  const [draft, setDraft] = useState("");
  const [actionError, setActionError] = useState<string | null>(null);
  const streamTextRef = useRef("");

  // Layout
  const [leftOpen, setLeftOpen] = useState(true);
  const [rightOpen, setRightOpen] = useState(true);

  // NPC modal
  const [modalNpcId, setModalNpcId] = useState<string | null>(null);
  const [modalLines, setModalLines] = useState<ModalLine[]>([]);
  const [modalStreaming, setModalStreaming] = useState(false);
  const [modalStreamText, setModalStreamText] = useState("");
  const [npcDraft, setNpcDraft] = useState("");
  const [modalError, setModalError] = useState<string | null>(null);
  const modalStreamTextRef = useRef("");

  const actionAbortRef = useRef<AbortController | null>(null);
  const npcAbortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    return () => {
      actionAbortRef.current?.abort();
      npcAbortRef.current?.abort();
    };
  }, []);

  const refreshWorldState = useCallback(async (sid: string) => {
    try {
      const state = await getWorldState(sid);
      setPlayer(state.player);
      setLocation(state.current_location);
      setNpcs(state.npcs_present);
      setQuests(state.active_quests);
    } catch {
      // Non-fatal: keep whatever state we already have.
    }
  }, []);

  const begin = useCallback(async () => {
    if (beginning) return;
    setBeginning(true);
    setCreateError(null);

    try {
      const trimmedBackstory = backstory.trim();
      const res = await startGame({
        player: {
          name: name.trim() || "Wanderer",
          player_class: playerClass,
          ...(trimmedBackstory ? { backstory: trimmedBackstory } : {}),
        },
      });

      setSessionId(res.session_id);
      setPlayer(res.player);
      setLocation(res.current_location);
      setEntries([
        {
          id: makeId("sys"),
          role: "system",
          text: `${res.current_location.name} · ${res.current_location.biome}`,
          timestamp: Date.now(),
        },
        {
          id: makeId("dm"),
          role: "dm",
          text: res.opening_narrative,
          timestamp: Date.now(),
        },
      ]);
      setScreen("game");
      
      generateAllAssets(res.session_id)
      .then(() => refreshWorldState(res.session_id))
      .catch(() => {
            // Non-critical — the game is still fully playable without generated art.
      });

      
      await refreshWorldState(res.session_id);
    } catch (exc) {
      setCreateError(
        exc instanceof Error ? exc.message : "The world would not take shape. Try again."
      );
    } finally {
      setBeginning(false);
    }
  }, [beginning, backstory, name, playerClass, refreshWorldState]);

  const act = useCallback(
    (rawText: string) => {
      const text = rawText.trim();
      if (!text || streaming || !sessionId) return;

      setEntries((prev) => [
        ...prev,
        { id: makeId("p"), role: "player", text, timestamp: Date.now() },
      ]);
      setDraft("");
      setActionError(null);
      setStreaming(true);
      setStreamText("");
      streamTextRef.current = "";

      const controller = new AbortController();
      actionAbortRef.current?.abort();
      actionAbortRef.current = controller;

      streamPlayerAction(
        sessionId,
        text,
        {
          onNarrative: (chunk) => {
            streamTextRef.current += chunk;
            setStreamText(streamTextRef.current);
          },
          onWorldUpdate: (payload) => {
            setMood(payload.scene_mood || "neutral");
          
            if (payload.scene_image_prompt && payload.scene_image_prompt !== lastScenePromptRef.current) {
              lastScenePromptRef.current = payload.scene_image_prompt;
              generateSceneImage(sessionId, payload.scene_image_prompt)
              .then((res) => setSceneImageUrl(res.scene_url))
              .catch(() => {
              // Non-critical — falls back to the mood-gradient background.
              });
              
            }

          },
          onDone: () => {
            const finalText = streamTextRef.current;
            setStreaming(false);
            setStreamText("");
            if (finalText) {
              setEntries((prev) => [
                ...prev,
                { id: makeId("dm"), role: "dm", text: finalText, timestamp: Date.now() },
              ]);
            }
            void refreshWorldState(sessionId);
          },
          onError: (message) => {
            setStreaming(false);
            setStreamText("");
            setActionError(message);
          },
        },
        controller.signal
      );
    },
    [sessionId, streaming, refreshWorldState]
  );

  const openNpc = useCallback((npc: NPC) => {
    setModalNpcId(npc.id);
    setModalLines([]);
    setModalStreamText("");
    modalStreamTextRef.current = "";
    setNpcDraft("");
    setModalError(null);
  }, []);

  const closeModal = useCallback(() => {
    npcAbortRef.current?.abort();
    setModalNpcId(null);
    setModalLines([]);
    setModalStreamText("");
    setModalStreaming(false);
    setModalError(null);
  }, []);

  const npcSpeak = useCallback(
    (rawText: string) => {
      const text = rawText.trim();
      if (!text || modalStreaming || !sessionId || !modalNpcId) return;

      setModalLines((prev) => [...prev, { id: makeId("pl"), role: "player", text }]);
      setNpcDraft("");
      setModalError(null);
      setModalStreaming(true);
      setModalStreamText("");
      modalStreamTextRef.current = "";

      const controller = new AbortController();
      npcAbortRef.current?.abort();
      npcAbortRef.current = controller;

      streamNpcTalk(
        sessionId,
        modalNpcId,
        text,
        {
          onNarrative: (chunk) => {
            modalStreamTextRef.current += chunk;
            setModalStreamText(modalStreamTextRef.current);
          },
          onReaction: (payload) => {
            setNpcs((prev) =>
              prev.map((n) =>
                n.id === payload.npc_id
                  ? { ...n, trust_level: payload.trust_level, disposition_toward_player: payload.disposition }
                  : n
              )
            );
          },
          onDone: () => {
            const finalText = modalStreamTextRef.current;
            setModalStreaming(false);
            setModalStreamText("");
            if (finalText) {
              setModalLines((prev) => [
                ...prev,
                { id: makeId("nl"), role: "npc", text: finalText },
              ]);
            }
          },
          onError: (message) => {
            setModalStreaming(false);
            setModalStreamText("");
            setModalError(message);
          },
        },
        controller.signal
      );
    },
    [sessionId, modalNpcId, modalStreaming]
  );

  return {
    screen,
    name,
    setName,
    playerClass,
    setPlayerClass,
    backstory,
    setBackstory,
    beginning,
    createError,
    begin,

    sessionId,
    player,
    location,
    npcs,
    quests,
    mood,
    sceneImageUrl,

    entries,
    showFull,
    toggleHistory: () => setShowFull((v) => !v),
    streaming,
    streamText,
    draft,
    setDraft,
    actionError,
    act,

    leftOpen,
    rightOpen,
    toggleLeft: () => setLeftOpen((v) => !v),
    toggleRight: () => setRightOpen((v) => !v),

    modalNpcId,
    modalLines,
    modalStreaming,
    modalStreamText,
    npcDraft,
    setNpcDraft,
    modalError,
    openNpc,
    closeModal,
    npcSpeak,
  };
}

export type GameSession = ReturnType<typeof useGameSession>;
