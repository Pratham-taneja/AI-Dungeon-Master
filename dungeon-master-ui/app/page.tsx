"use client";

import { useGameSession } from "@/hooks/useGameSession";
import CreateScreen from "@/components/CreateScreen";
import GameScreen from "@/components/GameScreen";
import NpcModal from "@/components/NpcModal";

export default function Home() {
  const gs = useGameSession();

  return (
    <div style={{ minHeight: "100vh", fontFamily: "var(--font-eb-garamond), Georgia, serif", color: "#e8dcc4" }}>
      {gs.screen === "create" && <CreateScreen gs={gs} />}
      {gs.screen === "game" && <GameScreen gs={gs} />}
      {gs.modalNpcId && <NpcModal gs={gs} />}
    </div>
  );
}
