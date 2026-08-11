import { readSSEFrames } from "./sse";
import type {
  ErrorPayload,
  NarrativeChunk,
  NpcReactionPayload,
  StartGameRequest,
  StartGameResponse,
  StreamEvent,
  WorldEventMessage,
  WorldStateResponse,
  WorldUpdatePayload,
} from "./types";

export const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

class ApiError extends Error {}

async function extractErrorMessage(res: Response): Promise<string> {
  try {
    const body = await res.json();
    if (typeof body?.detail === "string") return body.detail;
  } catch {
    // response wasn't JSON — fall through to status text
  }
  return `${res.status} ${res.statusText}`;
}

export async function startGame(
  request: StartGameRequest
): Promise<StartGameResponse> {
  const res = await fetch(`${API_BASE}/game/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  if (!res.ok) throw new ApiError(await extractErrorMessage(res));
  return res.json();
}

export async function getWorldState(
  sessionId: string
): Promise<WorldStateResponse> {
  const res = await fetch(`${API_BASE}/game/state/${sessionId}`);
  if (!res.ok) throw new ApiError(await extractErrorMessage(res));
  return res.json();
}

export async function deleteSession(sessionId: string): Promise<void> {
  await fetch(`${API_BASE}/game/${sessionId}`, { method: "DELETE" });
}

export interface AssetStatusResponse {
  session_id: string;
  locations: Record<string, string | null>;
  npcs: Record<string, string | null>;
}

export async function generateAllAssets(
  sessionId: string
): Promise<{ session_id: string; assets_generated: number; assets: Record<string, string> }> {
  const res = await fetch(`${API_BASE}/assets/generate-all/${sessionId}`, {
    method: "POST",
  });
  if (!res.ok) throw new ApiError(await extractErrorMessage(res));
  return res.json();
}

export async function generateMap(
  sessionId: string,
  locationId: string
): Promise<{ location_id: string; map_url: string }> {
  const res = await fetch(`${API_BASE}/assets/map/${sessionId}/${locationId}`, {
    method: "POST",
  });
  if (!res.ok) throw new ApiError(await extractErrorMessage(res));
  return res.json();
}

export async function generatePortrait(
  sessionId: string,
  npcId: string
): Promise<{ npc_id: string; portrait_url: string }> {
  const res = await fetch(`${API_BASE}/assets/portrait/${sessionId}/${npcId}`, {
    method: "POST",
  });
  if (!res.ok) throw new ApiError(await extractErrorMessage(res));
  return res.json();
}

export async function getAssetStatus(sessionId: string): Promise<AssetStatusResponse> {
  const res = await fetch(`${API_BASE}/assets/status/${sessionId}`);
  if (!res.ok) throw new ApiError(await extractErrorMessage(res));
  return res.json();
}

export async function generateSceneImage(
  sessionId: string,
  prompt: string
): Promise<{ session_id: string; scene_url: string }> {
  const res = await fetch(
    `${API_BASE}/assets/scene/${sessionId}?prompt=${encodeURIComponent(prompt)}`,
    { method: "POST" }
  );
  if (!res.ok) throw new ApiError(await extractErrorMessage(res));
  return res.json();
}

export interface ActionStreamHandlers {
  onNarrative: (text: string) => void;
  onWorldUpdate: (payload: WorldUpdatePayload) => void;
  onDone: () => void;
  onError: (message: string) => void;
}

export async function streamPlayerAction(
  sessionId: string,
  action: string,
  handlers: ActionStreamHandlers,
  signal?: AbortSignal
): Promise<void> {
  await runActionStream(
    `${API_BASE}/game/action/stream`,
    { session_id: sessionId, action },
    {
      narrative: (data) => handlers.onNarrative((data as NarrativeChunk).text),
      world_update: (data) => handlers.onWorldUpdate(data as WorldUpdatePayload),
      done: () => handlers.onDone(),
      error: (data) => handlers.onError((data as ErrorPayload)?.message ?? "Something went wrong."),
    },
    signal
  );
}

export interface NpcTalkHandlers {
  onNarrative: (text: string) => void;
  onReaction: (payload: NpcReactionPayload) => void;
  onDone: () => void;
  onError: (message: string) => void;
}

export async function streamNpcTalk(
  sessionId: string,
  targetNpcId: string,
  action: string,
  handlers: NpcTalkHandlers,
  signal?: AbortSignal
): Promise<void> {
  await runActionStream(
    `${API_BASE}/game/npc/talk`,
    { session_id: sessionId, action, target_npc_id: targetNpcId },
    {
      narrative: (data) => handlers.onNarrative((data as NarrativeChunk).text),
      npc_reaction: (data) => handlers.onReaction(data as NpcReactionPayload),
      done: () => handlers.onDone(),
      error: (data) => handlers.onError((data as ErrorPayload)?.message ?? "Something went wrong."),
    },
    signal
  );
}

async function runActionStream(
  url: string,
  body: Record<string, unknown>,
  onEvent: Partial<Record<StreamEvent["event_type"], (data: unknown) => void>>,
  signal?: AbortSignal
): Promise<void> {
  let res: Response;
  try {
    res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal,
    });
  } catch {
    onEvent.error?.({ message: "Could not reach the Dungeon Master. Is the backend running?" });
    return;
  }

  if (!res.ok || !res.body) {
    onEvent.error?.({ message: await extractErrorMessage(res) });
    return;
  }

  for await (const raw of readSSEFrames(res.body)) {
    let evt: StreamEvent;
    try {
      evt = JSON.parse(raw);
    } catch {
      continue;
    }
    onEvent[evt.event_type]?.(evt.data);
  }
}

export function subscribeWorldEvents(
  sessionId: string,
  handlers: {
    onMessage: (message: WorldEventMessage) => void;
    onOpen?: () => void;
    onError?: () => void;
  }
): EventSource {
  const source = new EventSource(`${API_BASE}/events/world/${sessionId}`);

  source.onopen = () => handlers.onOpen?.();
  source.onerror = () => handlers.onError?.();
  source.onmessage = (evt) => {
    try {
      handlers.onMessage(JSON.parse(evt.data));
    } catch {
      // ignore malformed frames (e.g. heartbeat comments never reach onmessage)
    }
  };

  return source;
}
