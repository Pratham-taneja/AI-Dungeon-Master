import type { NPCDisposition, PlayerClass, QuestStatus } from "./types";

export const CLASSES: { id: PlayerClass; icon: string; flavor: string }[] = [
  { id: "warrior", icon: "⚔", flavor: "Iron discipline, and a debt paid in blood." },
  { id: "mage", icon: "✦", flavor: "Reads the world as a text half-erased." },
  { id: "rogue", icon: "◆", flavor: "Never at the table; always in the room." },
  { id: "cleric", icon: "✝", flavor: "Prays to a god who stopped answering." },
  { id: "ranger", icon: "➳", flavor: "The wilds kept them. The roads never will." },
  { id: "bard", icon: "♪", flavor: "Every lie improves in the retelling." },
];

export const DISPOSITION_COLOR: Record<NPCDisposition, string> = {
  friendly: "#6fae6a",
  neutral: "#c9a227",
  suspicious: "#c98a2f",
  hostile: "#c1452f",
  fearful: "#8d7fc4",
};

export const QUEST_COLOR: Record<QuestStatus, string> = {
  available: "#c9a227",
  active: "#6fae6a",
  completed: "#5c8fbf",
  failed: "#c1452f",
};

const BIOME_GRADIENT: Record<string, string> = {
  ruins: "radial-gradient(80% 120% at 30% 10%, #3a2f22 0%, #1b1611 55%, #0d0b09 100%)",
  forest: "radial-gradient(80% 120% at 30% 10%, #23301f 0%, #141b12 55%, #0a0c09 100%)",
  swamp: "radial-gradient(80% 120% at 30% 10%, #263024 0%, #141a15 55%, #090b09 100%)",
  village: "radial-gradient(80% 120% at 30% 10%, #3a3120 0%, #1c170f 55%, #0d0a07 100%)",
  city: "radial-gradient(80% 120% at 30% 10%, #33302c 0%, #1a1815 55%, #0b0a09 100%)",
  dungeon: "radial-gradient(80% 120% at 30% 10%, #2a2a2e 0%, #17171a 55%, #09090a 100%)",
  unknown: "radial-gradient(80% 120% at 30% 10%, #2e2a24 0%, #17140f 55%, #0a0908 100%)",
};

export function getBiomeGradient(biome: string): string {
  return BIOME_GRADIENT[biome] ?? BIOME_GRADIENT.unknown;
}

const MOOD_OVERLAY: Record<string, string> = {
  peaceful: "linear-gradient(120deg, rgba(120,160,140,.5), rgba(200,180,120,.3))",
  tense: "linear-gradient(120deg, rgba(150,110,60,.55), rgba(60,50,60,.4))",
  dangerous: "linear-gradient(120deg, rgba(160,50,35,.6), rgba(50,20,20,.45))",
  mysterious: "linear-gradient(120deg, rgba(80,70,150,.55), rgba(30,40,70,.45))",
  dramatic: "linear-gradient(120deg, rgba(190,140,40,.55), rgba(90,25,25,.45))",
  neutral: "linear-gradient(120deg, rgba(90,80,70,.4), rgba(40,36,32,.4))",
};

export function getMoodOverlay(mood: string): string {
  return MOOD_OVERLAY[mood] ?? MOOD_OVERLAY.neutral;
}

const MOOD_DOT: Record<string, string> = {
  peaceful: "#6fae6a",
  tense: "#c98a2f",
  dangerous: "#c1452f",
  mysterious: "#8d7fc4",
  dramatic: "#d9b750",
  neutral: "#9a917f",
};

export function getMoodDot(mood: string): string {
  return MOOD_DOT[mood] ?? MOOD_DOT.neutral;
}

const PORTRAIT_GRADIENTS = [
  "linear-gradient(160deg,#3b3226,#171310)",
  "linear-gradient(160deg,#2b3328,#141711)",
  "linear-gradient(160deg,#33262a,#141011)",
];

export function getPortraitGradient(index: number): string {
  return PORTRAIT_GRADIENTS[index % PORTRAIT_GRADIENTS.length];
}

export const QUICK_ACTIONS = ["Look around", "Attack", "Talk", "Rest"];
