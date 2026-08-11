"use client";

import type { ReactNode } from "react";
import { DISPOSITION_COLOR, QUEST_COLOR, getPortraitGradient } from "@/lib/constants";
import { FONT_CINZEL, FONT_MONO } from "@/lib/fonts";
import { timeAgo } from "@/lib/format";
import type { WorldEventEntry } from "@/hooks/useWorldEvents";
import type { NPC, Quest } from "@/lib/types";

export default function WorldSidebar({
  npcs,
  quests,
  worldEvents,
  connected,
  open,
  onOpenNpc,
}: {
  npcs: NPC[];
  quests: Quest[];
  worldEvents: WorldEventEntry[];
  connected: boolean;
  open: boolean;
  onOpenNpc: (npc: NPC) => void;
}) {
  return (
    <aside
      style={{
        width: open ? 308 : 0,
        flex: "none",
        overflow: "hidden",
        borderLeft: "1px solid rgba(201,162,39,.14)",
        background: "rgba(16,13,11,.72)",
        backdropFilter: "blur(14px)",
        transition: "width .28s ease",
      }}
    >
      <div
        style={{
          width: 308,
          height: "100%",
          overflowY: "auto",
          padding: "20px 18px",
          display: "grid",
          gap: 24,
          alignContent: "start",
        }}
      >
        <div style={{ display: "grid", gap: 10 }}>
          <SectionLabel>Present</SectionLabel>
          {npcs.length === 0 && <EmptyNote>No one else is here.</EmptyNote>}
          {npcs.map((n, i) => {
            const dispColor = DISPOSITION_COLOR[n.disposition_toward_player];
            return (
              <button
                key={n.id}
                type="button"
                onClick={() => onOpenNpc(n)}
                className="dm-npc-card"
                style={{
                  cursor: "pointer",
                  textAlign: "left",
                  display: "flex",
                  gap: 12,
                  alignItems: "center",
                  width: "100%",
                  padding: 11,
                  border: "1px solid rgba(232,220,196,.08)",
                  borderRadius: 3,
                  background: "rgba(12,10,8,.5)",
                  color: "inherit",
                  fontFamily: "inherit",
                  transition: "all .2s ease",
                }}
              >
                <div
                    style={{
                    width: 42,
                    height: 42,
                    flex: "none",
                    borderRadius: 2,
                    border: "1px solid rgba(201,162,39,.28)",
                    background: n.portrait_url ? undefined : getPortraitGradient(i),
                    backgroundImage: n.portrait_url ? `url(${n.portrait_url})` : undefined,
                    backgroundSize: "cover",
                    backgroundPosition: "center",
                    display: "grid",
                    placeItems: "center",
                    fontFamily: FONT_CINZEL,
                    fontSize: 16,
                    color: "rgba(240,227,189,.9)",
            }}
            >
                    {!n.portrait_url && n.name.charAt(0)}
                </div>
                
                <div style={{ minWidth: 0, flex: 1 }}>
                  <div
                    style={{
                      fontFamily: FONT_CINZEL,
                      fontSize: 15,
                      letterSpacing: ".03em",
                      color: "#ecdcb4",
                      whiteSpace: "nowrap",
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                    }}
                  >
                    {n.name}
                  </div>
                  <div
                    style={{
                      fontSize: 14,
                      color: "rgba(232,220,196,.5)",
                      fontStyle: "italic",
                      whiteSpace: "nowrap",
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                    }}
                  >
                    {n.role}
                  </div>
                </div>
                <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 4, flex: "none" }}>
                  <span style={{ width: 7, height: 7, borderRadius: "50%", background: dispColor, boxShadow: `0 0 10px ${dispColor}` }} />
                  <span
                    style={{
                      fontFamily: FONT_MONO,
                      fontSize: 8,
                      letterSpacing: ".14em",
                      textTransform: "uppercase",
                      color: dispColor,
                    }}
                  >
                    {n.disposition_toward_player}
                  </span>
                </div>
              </button>
            );
          })}
        </div>

        <div style={{ display: "grid", gap: 10 }}>
          <SectionLabel>Quests</SectionLabel>
          {quests.length === 0 && <EmptyNote>No quests taken up — yet.</EmptyNote>}
          {quests.map((q) => (
            <QuestCard key={q.id} quest={q} />
          ))}
        </div>

        <div style={{ display: "grid", gap: 10 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <SectionLabel>World</SectionLabel>
            <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
              <span
                style={{
                  width: 6,
                  height: 6,
                  borderRadius: "50%",
                  background: connected ? "#6fae6a" : "#c1452f",
                  animation: "dm-pulse 2.2s ease-in-out infinite",
                }}
              />
              <span
                style={{
                  fontFamily: FONT_MONO,
                  fontSize: 9,
                  letterSpacing: ".16em",
                  textTransform: "uppercase",
                  color: "rgba(232,220,196,.45)",
                }}
              >
                {connected ? "live" : "reconnecting"}
              </span>
            </div>
          </div>
          <div style={{ display: "grid", gap: 6, maxHeight: 240, overflowY: "auto", paddingRight: 4 }}>
            {worldEvents.length === 0 && <EmptyNote>The world is quiet, so far.</EmptyNote>}
            {worldEvents.map((ev) => (
              <div
                key={ev.id}
                style={{
                  border: "1px solid rgba(232,220,196,.06)",
                  borderRadius: 3,
                  padding: "10px 11px",
                  background: "rgba(12,10,8,.4)",
                }}
              >
                <div style={{ fontSize: 14, lineHeight: 1.45, color: "rgba(232,220,196,.66)", fontStyle: "italic", textWrap: "pretty" }}>
                  {ev.text}
                </div>
                <div style={{ marginTop: 5, fontFamily: FONT_MONO, fontSize: 9, letterSpacing: ".14em", color: "rgba(232,220,196,.32)" }}>
                  {timeAgo(ev.timestamp)}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </aside>
  );
}

function SectionLabel({ children }: { children: ReactNode }) {
  return (
    <div
      style={{
        fontFamily: FONT_MONO,
        fontSize: 10,
        letterSpacing: ".26em",
        textTransform: "uppercase",
        color: "rgba(201,162,39,.65)",
      }}
    >
      {children}
    </div>
  );
}

function EmptyNote({ children }: { children: ReactNode }) {
  return <div style={{ fontSize: 13, color: "rgba(232,220,196,.32)", fontStyle: "italic" }}>{children}</div>;
}

function QuestCard({ quest }: { quest: Quest }) {
  const statusColor = QUEST_COLOR[quest.status];
  const rewardParts: string[] = [];
  if (quest.reward_gold > 0) rewardParts.push(`${quest.reward_gold}g`);
  if (quest.reward_items.length > 0) rewardParts.push(quest.reward_items.join(", "));

  return (
    <div
      style={{
        border: "1px solid rgba(232,220,196,.08)",
        borderLeft: `2px solid ${statusColor}`,
        borderRadius: 3,
        padding: 12,
        background: "rgba(12,10,8,.45)",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", gap: 8 }}>
        <div style={{ fontFamily: FONT_CINZEL, fontSize: 14, color: "#ecdcb4" }}>{quest.title}</div>
        <div
          style={{
            fontFamily: FONT_MONO,
            fontSize: 8,
            letterSpacing: ".16em",
            textTransform: "uppercase",
            color: statusColor,
            flex: "none",
          }}
        >
          {quest.status}
        </div>
      </div>
      {quest.objectives.length > 0 && (
        <div style={{ marginTop: 6, display: "grid", gap: 3 }}>
          {quest.objectives.map((o, i) => (
            <div key={i} style={{ fontSize: 14, lineHeight: 1.4, color: "rgba(232,220,196,.55)" }}>
              · {o}
            </div>
          ))}
        </div>
      )}
      {rewardParts.length > 0 && (
        <div style={{ marginTop: 8, fontFamily: FONT_MONO, fontSize: 9, letterSpacing: ".14em", color: "rgba(201,162,39,.65)" }}>
          {rewardParts.join(" · ")}
        </div>
      )}
    </div>
  );
}
