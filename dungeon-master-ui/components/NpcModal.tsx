"use client";

import { useEffect, useRef } from "react";
import { DISPOSITION_COLOR, getMoodOverlay } from "@/lib/constants";
import { FONT_CINZEL, FONT_MONO, FONT_SERIF } from "@/lib/fonts";
import type { GameSession } from "@/hooks/useGameSession";

export default function NpcModal({ gs }: { gs: GameSession }) {
  const npc = gs.npcs.find((n) => n.id === gs.modalNpcId) ?? null;
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [gs.modalLines.length, gs.modalStreamText]);

  if (!npc) return null;

  const trust = npc.trust_level;
  const trustLabel = trust > 0 ? `+${trust}` : String(trust);
  const trustPct = Math.round((trust + 100) / 2);
  const trustColor = trust > 25 ? "#6fae6a" : trust > -25 ? "#c9a227" : "#c1452f";
  const dispColor = DISPOSITION_COLOR[npc.disposition_toward_player];

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 60,
        display: "flex",
        alignItems: "flex-end",
        justifyContent: "center",
        background: "rgba(6,5,4,.82)",
        backdropFilter: "blur(10px)",
      }}
    >
      <div
        style={{ position: "absolute", inset: 0, background: getMoodOverlay(gs.mood), opacity: 0.5 }}
        onClick={gs.closeModal}
      />
      <div
        style={{
          position: "relative",
          width: "100%",
          maxWidth: 1080,
          margin: "0 24px",
          background: "rgba(18,15,12,.9)",
          border: "1px solid rgba(201,162,39,.3)",
          borderBottom: "none",
          borderRadius: "5px 5px 0 0",
          boxShadow: "0 -30px 120px -20px rgba(0,0,0,.95)",
          padding: "28px 32px 26px",
          display: "flex",
          gap: 26,
        }}
      >
        <div style={{ width: 190, flex: "none", display: "grid", gap: 12, alignContent: "start" }}>
          <div
            style={{
              width: 190,
              height: 230,
              border: "1px solid rgba(201,162,39,.3)",
              borderRadius: 3,
              background: npc.portrait_url ? undefined : "linear-gradient(160deg,#3b3226,#171310)",
              backgroundImage: npc.portrait_url ? `url(${npc.portrait_url})` : undefined,
              backgroundSize: "cover",
              backgroundPosition: "center",
              display: "grid",
              placeItems: "center",
              position: "relative",
              overflow: "hidden",
            }}
          >
          {!npc.portrait_url && (
            <span style={{ fontFamily: FONT_CINZEL, fontSize: 56, color: "rgba(240,227,189,.85)", textShadow: "0 4px 24px rgba(0,0,0,.6)" }}>
              {npc.name.charAt(0)}
            </span>
            )}

          </div>
          
          <div style={{ display: "grid", gap: 5 }}>
            <div style={{ display: "flex", justifyContent: "space-between", fontFamily: FONT_MONO, fontSize: 9, letterSpacing: ".16em", color: "rgba(232,220,196,.5)" }}>
              <span>TRUST</span>
              <span style={{ color: trustColor }}>{trustLabel}</span>
            </div>
            <div style={{ height: 5, borderRadius: 5, background: "rgba(232,220,196,.08)", overflow: "hidden" }}>
              <div style={{ height: "100%", borderRadius: 5, background: trustColor, transition: "width .6s ease", width: `${trustPct}%` }} />
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 6, marginTop: 2 }}>
              <span style={{ width: 6, height: 6, borderRadius: "50%", background: dispColor, boxShadow: `0 0 10px ${dispColor}` }} />
              <span style={{ fontFamily: FONT_MONO, fontSize: 9, letterSpacing: ".16em", textTransform: "uppercase", color: dispColor }}>
                {npc.disposition_toward_player}
              </span>
            </div>
          </div>
        </div>

        <div style={{ flex: 1, minWidth: 0, display: "flex", flexDirection: "column", gap: 16 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 16 }}>
            <div>
              <h3 style={{ margin: 0, fontFamily: FONT_CINZEL, fontSize: 26, letterSpacing: ".05em", color: "#f0e3bd" }}>{npc.name}</h3>
              <div style={{ marginTop: 4, fontSize: 16, fontStyle: "italic", color: "rgba(232,220,196,.55)" }}>
                {npc.role} · {npc.personality.speech_style}
              </div>
            </div>
            <button
              type="button"
              onClick={gs.closeModal}
              className="dm-modal-close"
              style={{
                cursor: "pointer",
                flex: "none",
                background: "transparent",
                border: "1px solid rgba(201,162,39,.28)",
                borderRadius: 3,
                color: "rgba(232,220,196,.7)",
                fontFamily: FONT_MONO,
                fontSize: 10,
                letterSpacing: ".2em",
                padding: "8px 13px",
              }}
            >
              LEAVE
            </button>
          </div>

          <div ref={scrollRef} style={{ flex: 1, minHeight: 170, maxHeight: 280, overflowY: "auto", display: "grid", gap: 12, alignContent: "start", paddingRight: 6 }}>
            {gs.modalLines.length === 0 && !gs.modalStreaming && (
              <p style={{ margin: 0, fontSize: 16, fontStyle: "italic", color: "rgba(232,220,196,.4)" }}>
                {npc.name.split(" ")[0]} waits for you to speak first.
              </p>
            )}
            {gs.modalLines.map((l) => (
              <div key={l.id}>
                {l.role === "npc" && (
                  <p style={{ margin: 0, fontSize: 20, lineHeight: 1.6, color: "#e6d9bd", textWrap: "pretty" }}>“{l.text}”</p>
                )}
                {l.role === "player" && (
                  <p style={{ margin: 0, fontSize: 17, lineHeight: 1.5, fontStyle: "italic", color: "rgba(201,162,39,.8)", textAlign: "right" }}>
                    {l.text}
                  </p>
                )}
              </div>
            ))}
            {gs.modalStreaming && (
              <p style={{ margin: 0, fontSize: 20, lineHeight: 1.6, color: "#e6d9bd", textWrap: "pretty" }}>
                “{gs.modalStreamText}
                <span
                  style={{
                    display: "inline-block",
                    width: 9,
                    height: 19,
                    marginLeft: 2,
                    verticalAlign: "-3px",
                    background: "#c9a227",
                    animation: "dm-blink 1s step-end infinite",
                  }}
                />
              </p>
            )}
            {gs.modalError && (
              <p style={{ margin: 0, fontSize: 13, color: "#c1452f", fontFamily: FONT_MONO }}>{gs.modalError}</p>
            )}
          </div>

          <div style={{ display: "flex", gap: 10 }}>
            <input
              className="dm-modal-input"
              value={gs.npcDraft}
              onChange={(e) => gs.setNpcDraft(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") gs.npcSpeak(gs.npcDraft);
              }}
              disabled={gs.modalStreaming}
              placeholder={`Say something to ${npc.name.split(" ")[0]}…`}
              style={{
                flex: 1,
                background: "rgba(10,9,7,.85)",
                border: "1px solid rgba(201,162,39,.3)",
                borderRadius: 3,
                padding: "14px 16px",
                color: "#efe2c2",
                fontFamily: FONT_SERIF,
                fontSize: 18,
                outline: "none",
              }}
            />
            <button
              type="button"
              disabled={gs.modalStreaming}
              onClick={() => gs.npcSpeak(gs.npcDraft)}
              style={{
                cursor: gs.modalStreaming ? "default" : "pointer",
                flex: "none",
                background: "linear-gradient(180deg, rgba(201,162,39,.28), rgba(201,162,39,.1))",
                border: "1px solid rgba(201,162,39,.5)",
                borderRadius: 3,
                padding: "0 24px",
                fontFamily: FONT_CINZEL,
                fontSize: 13,
                letterSpacing: ".2em",
                textTransform: "uppercase",
                color: "#f0dfae",
              }}
            >
              Speak
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
