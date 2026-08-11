/**
 * Minimal Server-Sent Events frame parser for POST-initiated streams.
 *
 * The browser's native EventSource only supports GET requests, but the
 * backend's action/npc-talk endpoints are POST (they take a JSON body), so
 * those streams are read by hand off the fetch Response body instead.
 */
export async function* readSSEFrames(
  body: ReadableStream<Uint8Array>
): AsyncGenerator<string> {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      let boundary: number;
      while ((boundary = buffer.indexOf("\n\n")) !== -1) {
        const rawEvent = buffer.slice(0, boundary);
        buffer = buffer.slice(boundary + 2);

        const dataLines = rawEvent
          .split("\n")
          .filter((line) => line.startsWith("data:"))
          .map((line) => line.slice(5).trimStart());

        if (dataLines.length > 0) {
          yield dataLines.join("\n");
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}
