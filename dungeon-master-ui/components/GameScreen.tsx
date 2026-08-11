"use client";

import { useEffect, useRef } from "react";
import { useWorldEvents } from "@/hooks/useWorldEvents";
import { useTTS } from "@/hooks/useTTS";
import { useAmbientMusic } from "@/hooks/useAmbientMusic";
import type { GameSession } from "@/hooks/useGameSession";
import SceneHeader from "./SceneHeader";
import PlayerSidebar from "./PlayerSidebar";
import WorldSidebar from "./WorldSidebar";
import MainPanel from "./MainPanel";

export default function GameScreen({ gs }: { gs: GameSession }) {
  const { events, connected } = useWorldEvents(gs.sessionId);
  const tts = useTTS();
  const music = useAmbientMusic();

  const lastSpokenEntryId = useRef<string | null>(null);

  // Speak the latest DM narrative entry as soon as it lands.
  useEffect(() => {
    const lastDmEntry = [...gs.entries].reverse().find((e) => e.role === "dm");
    if (lastDmEntry && lastDmEntry.id !== lastSpokenEntryId.current) {
      lastSpokenEntryId.current = lastDmEntry.id;
      tts.speak(lastDmEntry.text);
    }
  }, [gs.entries, tts]);

  // Keep ambient music synced to the current scene mood.
  useEffect(() => {
    music.setMood(gs.mood);
  }, [gs.mood, music]);

  if (!gs.player || !gs.location) return null;

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100vh", overflow: "hidden", background: "#0b0a09" }}>
      <SceneHeader
        location={gs.location}
        mood={gs.mood}
        sceneImageUrl={gs.sceneImageUrl}
        leftOpen={gs.leftOpen}
        rightOpen={gs.rightOpen}
        onToggleLeft={gs.toggleLeft}
        onToggleRight={gs.toggleRight}
        isMuted={tts.isMuted}
        onToggleMute={tts.toggleMute}
        isMusicMuted={music.isMusicMuted}
        onToggleMusic={music.toggleMusic}
      />

      <div style={{ flex: 1, display: "flex", minHeight: 0 }}>
        <PlayerSidebar player={gs.player} open={gs.leftOpen} />

        <MainPanel
          entries={gs.entries}
          showFull={gs.showFull}
          onToggleHistory={gs.toggleHistory}
          streaming={gs.streaming}
          streamText={gs.streamText}
          draft={gs.draft}
          onDraftChange={gs.setDraft}
          onAct={gs.act}
          playerName={gs.player.name}
          actionError={gs.actionError}
        />

        <WorldSidebar
          npcs={gs.npcs}
          quests={gs.quests}
          worldEvents={events}
          connected={connected}
          open={gs.rightOpen}
          onOpenNpc={gs.openNpc}
        />
      </div>
    </div>
  );
}