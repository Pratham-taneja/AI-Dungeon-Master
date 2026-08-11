"use client";

import { useEffect, useRef } from "react";
import { QUICK_ACTIONS } from "@/lib/constants";
import { FONT_CINZEL, FONT_MONO, FONT_SERIF } from "@/lib/fonts";
import type { ChronicleEntry } from "@/lib/types";

export default function MainPanel({
  entries,
  showFull,
  onToggleHistory,
  streaming,
  streamText,
  draft,
  onDraftChange,
  onAct,
  playerName,
  actionError,
}: {
  entries: ChronicleEntry[];
  showFull: boolean;
  onToggleHistory: () => void;
  streaming: boolean;
  streamText: string;
  draft: string;
  onDraftChange: (value: string) => void;
  onAct: (text: string) => void;
  playerName: string;
  actionError: string | null;
}) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const visible = showFull ? entries : entries.slice(-3);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [entries.length, streamText]);

  return (
    <main style={{ flex: 1, minWidth: 0, display: "flex", flexDirection: "column" }}>
      <div ref={scrollRef} style={{ flex: 1, minHeight: 0, overflowY: "auto", padding: "26px 34px 10px" }}>
        <div style={{ maxWidth: 760, margin: "0 auto", display: "grid", gap: 20 }}>
          <div style={{ display: "flex", justifyContent: "center" }}>
            <button
              type="button"
              onClick={onToggleHistory}
              className="dm-history-toggle"
              style={{
                cursor: "pointer",
                background: "transparent",
                border: "1px solid rgba(201,162,39,.22)",
                borderRadius: 99,
                padding: "6px 16px",
                fontFamily: FONT_MONO,
                fontSize: 10,
                letterSpacing: ".22em",
                textTransform: "uppercase",
                color: "rgba(232,220,196,.55)",
              }}
            >
              {showFull ? "show recent only" : `show full chronicle (${entries.length})`}
            </button>
          </div>

          {visible.map((e) => (
            <div key={e.id}>
              {e.role === "dm" && (
                <div
                  style={{
                    position: "relative",
                    border: "1px solid rgba(201,162,39,.18)",
                    borderRadius: 3,
                    padding: "22px 26px",
                    background: "linear-gradient(180deg, rgba(38,30,21,.55), rgba(22,18,14,.55))",
                    backdropFilter: "blur(10px)",
                    boxShadow: "inset 0 1px 0 rgba(232,220,196,.05)",
                  }}
                >
                  <div style={{ fontFamily: FONT_MONO, fontSize: 9, letterSpacing: ".3em", textTransform: "uppercase", color: "rgba(201,162,39,.6)", marginBottom: 10 }}>
                    Dungeon Master
                  </div>
                  <p style={{ margin: 0, fontSize: 19, lineHeight: 1.68, color: "#e3d6ba", textWrap: "pretty" }}>{e.text}</p>
                </div>
              )}
              {e.role === "player" && (
                <div style={{ display: "flex", justifyContent: "flex-end" }}>
                  <div style={{ maxWidth: "76%", border: "1px solid rgba(201,162,39,.3)", borderRadius: "14px 14px 3px 14px", padding: "13px 18px", background: "rgba(201,162,39,.1)" }}>
                    <div style={{ fontFamily: FONT_MONO, fontSize: 9, letterSpacing: ".28em", textTransform: "uppercase", color: "rgba(201,162,39,.6)", marginBottom: 5 }}>
                      {playerName}
                    </div>
                    <p style={{ margin: 0, fontSize: 17, lineHeight: 1.5, color: "#efe2c2", fontStyle: "italic" }}>{e.text}</p>
                  </div>
                </div>
              )}
              {e.role === "system" && (
                <div style={{ textAlign: "center", fontFamily: FONT_MONO, fontSize: 10, letterSpacing: ".24em", textTransform: "uppercase", color: "rgba(201,162,39,.55)", padding: "4px 0" }}>
                  — {e.text} —
                </div>
              )}
            </div>
          ))}

          {streaming && (
            <div
              style={{
                border: "1px solid rgba(201,162,39,.28)",
                borderRadius: 3,
                padding: "22px 26px",
                background: "linear-gradient(180deg, rgba(38,30,21,.6), rgba(22,18,14,.6))",
                backdropFilter: "blur(10px)",
              }}
            >
              <div style={{ fontFamily: FONT_MONO, fontSize: 9, letterSpacing: ".3em", textTransform: "uppercase", color: "rgba(201,162,39,.75)", marginBottom: 10 }}>
                Dungeon Master · narrating
              </div>
              <p style={{ margin: 0, fontSize: 19, lineHeight: 1.68, color: "#e3d6ba", textWrap: "pretty" }}>
                {streamText}
                <span
                  style={{
                    display: "inline-block",
                    width: 9,
                    height: 19,
                    marginLeft: 3,
                    verticalAlign: "-3px",
                    background: "#c9a227",
                    animation: "dm-blink 1s step-end infinite",
                  }}
                />
              </p>
            </div>
          )}

          {actionError && (
            <div style={{ textAlign: "center", fontFamily: FONT_MONO, fontSize: 11, letterSpacing: ".08em", color: "#c1452f" }}>{actionError}</div>
          )}
        </div>
      </div>

      <div style={{ flex: "none", borderTop: "1px solid rgba(201,162,39,.16)", background: "rgba(14,12,10,.8)", backdropFilter: "blur(16px)", padding: "16px 34px 20px" }}>
        <div style={{ maxWidth: 760, margin: "0 auto", display: "grid", gap: 12 }}>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8, opacity: streaming ? 0.4 : 1, transition: "opacity .25s ease" }}>
            {QUICK_ACTIONS.map((label) => (
              <button
                key={label}
                type="button"
                disabled={streaming}
                onClick={() => onAct(label)}
                className="dm-quick-action"
                style={{
                  cursor: streaming ? "default" : "pointer",
                  background: "rgba(201,162,39,.06)",
                  border: "1px solid rgba(201,162,39,.24)",
                  borderRadius: 99,
                  padding: "8px 16px",
                  fontFamily: FONT_MONO,
                  fontSize: 10,
                  letterSpacing: ".2em",
                  textTransform: "uppercase",
                  color: "rgba(232,220,196,.78)",
                  transition: "all .2s ease",
                }}
              >
                {label}
              </button>
            ))}
          </div>
          <div style={{ display: "flex", gap: 10, alignItems: "stretch" }}>
            <input
              className="dm-act-input"
              value={draft}
              onChange={(e) => onDraftChange(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") onAct(draft);
              }}
              disabled={streaming}
              placeholder={streaming ? "The Dungeon Master is speaking…" : "What do you do?"}
              style={{
                flex: 1,
                background: "rgba(10,9,7,.85)",
                border: "1px solid rgba(201,162,39,.3)",
                borderRadius: 3,
                padding: "15px 18px",
                color: "#efe2c2",
                fontFamily: FONT_SERIF,
                fontSize: 18,
                outline: "none",
                animation: "dm-glow 4.5s ease-in-out infinite",
              }}
            />
            <button
              type="button"
              disabled={streaming}
              onClick={() => onAct(draft)}
              className="dm-act-btn"
              style={{
                flex: "none",
                cursor: streaming ? "default" : "pointer",
                background: "linear-gradient(180deg, rgba(201,162,39,.28), rgba(201,162,39,.1))",
                border: "1px solid rgba(201,162,39,.5)",
                borderRadius: 3,
                padding: "0 26px",
                fontFamily: FONT_CINZEL,
                fontSize: 13,
                letterSpacing: ".2em",
                textTransform: "uppercase",
                color: "#f0dfae",
              }}
            >
              Act
            </button>
          </div>
        </div>
      </div>
    </main>
  );
}
