/**
 * TypeScript mirrors of backend/models/schemas.py.
 * Keep in sync with the FastAPI Pydantic models — these are the wire types.
 */

export type PlayerClass =
  | "warrior"
  | "mage"
  | "rogue"
  | "cleric"
  | "ranger"
  | "bard";

export type QuestStatus = "available" | "active" | "completed" | "failed";

export type NPCDisposition =
  | "friendly"
  | "neutral"
  | "suspicious"
  | "hostile"
  | "fearful";

export type GameEventType =
  | "narrative"
  | "world_update"
  | "npc_reaction"
  | "quest_update"
  | "item_gained"
  | "combat_start"
  | "error"
  | "done";

export interface PlayerStats {
  health: number;
  max_health: number;
  mana: number;
  max_mana: number;
  strength: number;
  intelligence: number;
  dexterity: number;
  charisma: number;
  level: number;
  experience: number;
}

export interface PlayerCreate {
  name: string;
  player_class: PlayerClass;
  backstory?: string;
}

export interface Player {
  id: string;
  name: string;
  player_class: PlayerClass;
  backstory: string;
  stats: PlayerStats;
  inventory: string[];
  gold: number;
  current_location_id: string;
  created_at: string;
}

export interface Location {
  id: string;
  name: string;
  description: string;
  biome: string;
  connected_locations: string[];
  npc_ids: string[];
  items_present: string[];
  is_dangerous: boolean;
  map_image_url: string | null;
  discovered_at: string;
}

export interface NPCPersonality {
  traits: string[];
  speech_style: string;
  motivation: string;
  secret: string;
  disposition_toward_strangers: NPCDisposition;
}

export interface NPC {
  id: string;
  name: string;
  role: string;
  appearance: string;
  location_id: string;
  personality: NPCPersonality;
  backstory: string;
  disposition_toward_player: NPCDisposition;
  trust_level: number;
  portrait_url: string | null;
  created_at: string;
  last_interaction: string | null;
}

export interface Quest {
  id: string;
  title: string;
  description: string;
  giver_npc_id: string | null;
  status: QuestStatus;
  objectives: string[];
  reward_gold: number;
  reward_items: string[];
  created_at: string;
}

export interface StartGameRequest {
  player: PlayerCreate;
  world_seed?: string | null;
}

export interface StartGameResponse {
  session_id: string;
  player: Player;
  opening_narrative: string;
  current_location: Location;
}

export interface PlayerActionRequest {
  session_id: string;
  action: string;
  target_npc_id?: string | null;
}

export interface WorldStateResponse {
  session_id: string;
  player: Player;
  current_location: Location;
  npcs_present: NPC[];
  active_quests: Quest[];
  turn_count: number;
}

export interface StreamEvent<T = unknown> {
  event_type: GameEventType;
  data: T;
  session_id: string;
  turn: number;
}

export interface NarrativeChunk {
  text: string;
  is_final: boolean;
}

export interface WorldUpdatePayload {
  location_changed: boolean;
  new_location: Location | null;
  npc_disposition_changes: Record<string, NPCDisposition>;
  items_gained: string[];
  quest_updates: Record<string, unknown>[];
  player_stats_delta: Record<string, number>;
  scene_mood: string | null;
  scene_image_prompt: string | null;
}

export interface NpcReactionPayload {
  npc_id: string;
  npc_name: string;
  trust_level: number;
  disposition: NPCDisposition;
  interaction_result: unknown;
}

export interface ErrorPayload {
  message: string;
}

/** Message shape published on the `/events/world/{session_id}` SSE channel. */
export interface WorldEventMessage {
  type: "connected" | "world_event" | "error";
  session_id?: string;
  text?: string;
  message?: string;
}

/** A line in the chronicle / dialogue feed, as rendered by the UI. */
export interface ChronicleEntry {
  id: string;
  role: "dm" | "player" | "system";
  text: string;
  timestamp: number;
}

export interface ModalLine {
  id: string;
  role: "npc" | "player";
  text: string;
}
