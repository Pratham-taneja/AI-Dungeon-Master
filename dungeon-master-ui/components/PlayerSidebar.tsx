"use client";

import { CLASSES } from "@/lib/constants";
import { FONT_CINZEL, FONT_MONO } from "@/lib/fonts";
import type { Player } from "@/lib/types";

export default function PlayerSidebar({ player, open }: { player: Player; open: boolean }) {
  const stats = player.stats;
  const icon = CLASSES.find((c) => c.id === player.player_class)?.icon ?? "?";
  const healthPct = Math.round((stats.health / stats.max_health) * 100);
  const manaPct = Math.round((stats.mana / stats.max_mana) * 100);

  const attributes = [
    { key: "STR", value: stats.strength },
    { key: "INT", value: stats.intelligence },
    { key: "DEX", value: stats.dexterity },
    { key: "CHA", value: stats.charisma },
  ];

  return (
    <aside
      style={{
        width: open ? 264 : 0,
        flex: "none",
        overflow: "hidden",
        borderRight: "1px solid rgba(201,162,39,.14)",
        background: "rgba(16,13,11,.72)",
        backdropFilter: "blur(14px)",
        transition: "width .28s ease",
      }}
    >
      <div
        style={{
          width: 264,
          height: "100%",
          overflowY: "auto",
          padding: "20px 18px",
          display: "grid",
          gap: 22,
          alignContent: "start",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div
            style={{
              width: 44,
              height: 44,
              flex: "none",
              display: "grid",
              placeItems: "center",
              border: "1px solid rgba(201,162,39,.35)",
              borderRadius: 3,
              background: "rgba(201,162,39,.08)",
              fontSize: 20,
              color: "#d9b750",
            }}
          >
            {icon}
          </div>
          <div>
            <div style={{ fontFamily: FONT_CINZEL, fontSize: 17, letterSpacing: ".05em", color: "#eddcb0" }}>
              {player.name}
            </div>
            <div
              style={{
                fontFamily: FONT_MONO,
                fontSize: 10,
                letterSpacing: ".18em",
                textTransform: "uppercase",
                color: "rgba(232,220,196,.45)",
              }}
            >
              Level {stats.level} · {player.player_class}
            </div>
          </div>
        </div>

        <div style={{ display: "grid", gap: 12 }}>
          <StatBar label="HEALTH" valueLabel={`${stats.health} / ${stats.max_health}`} pct={healthPct} gradient="linear-gradient(90deg,#7e1f1f,#c1452f)" glow="rgba(193,69,47,.8)" />
          <StatBar label="MANA" valueLabel={`${stats.mana} / ${stats.max_mana}`} pct={manaPct} gradient="linear-gradient(90deg,#1f3f6e,#4a86c4)" glow="rgba(74,134,196,.8)" />

          <div style={{ display: "flex", gap: 8 }}>
            <div style={{ flex: 1, border: "1px solid rgba(201,162,39,.16)", borderRadius: 3, padding: "9px 10px", background: "rgba(12,10,8,.5)" }}>
              <div style={{ fontFamily: FONT_MONO, fontSize: 9, letterSpacing: ".2em", color: "rgba(232,220,196,.4)" }}>GOLD</div>
              <div style={{ fontFamily: FONT_CINZEL, fontSize: 18, color: "#d9b750" }}>{player.gold}</div>
            </div>
            <div style={{ flex: 1, border: "1px solid rgba(201,162,39,.16)", borderRadius: 3, padding: "9px 10px", background: "rgba(12,10,8,.5)" }}>
              <div style={{ fontFamily: FONT_MONO, fontSize: 9, letterSpacing: ".2em", color: "rgba(232,220,196,.4)" }}>XP</div>
              <div style={{ fontFamily: FONT_CINZEL, fontSize: 18, color: "#e8dcc4" }}>{stats.experience}</div>
            </div>
          </div>
        </div>

        <div style={{ display: "grid", gap: 8 }}>
          <div style={{ fontFamily: FONT_MONO, fontSize: 10, letterSpacing: ".26em", textTransform: "uppercase", color: "rgba(201,162,39,.65)" }}>
            Attributes
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 6 }}>
            {attributes.map((a) => (
              <div
                key={a.key}
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  border: "1px solid rgba(232,220,196,.08)",
                  borderRadius: 3,
                  padding: "7px 9px",
                  fontFamily: FONT_MONO,
                  fontSize: 10,
                  letterSpacing: ".12em",
                  color: "rgba(232,220,196,.55)",
                }}
              >
                <span>{a.key}</span>
                <span style={{ color: "#e8dcc4" }}>{a.value}</span>
              </div>
            ))}
          </div>
        </div>

        <div style={{ display: "grid", gap: 8 }}>
          <div style={{ fontFamily: FONT_MONO, fontSize: 10, letterSpacing: ".26em", textTransform: "uppercase", color: "rgba(201,162,39,.65)" }}>
            Inventory
          </div>
          <div style={{ display: "grid", gap: 4 }}>
            {player.inventory.length === 0 && (
              <div style={{ fontSize: 14, color: "rgba(232,220,196,.35)", fontStyle: "italic" }}>Empty-handed, for now.</div>
            )}
            {player.inventory.map((item, i) => (
              <div
                key={`${item}-${i}`}
                className="dm-inventory-item"
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 9,
                  padding: "8px 10px",
                  border: "1px solid rgba(232,220,196,.07)",
                  borderRadius: 3,
                  background: "rgba(12,10,8,.4)",
                  fontSize: 15,
                  color: "rgba(232,220,196,.82)",
                }}
              >
                <span style={{ width: 4, height: 4, borderRadius: "50%", background: "rgba(201,162,39,.6)", flex: "none" }} />
                {item}
              </div>
            ))}
          </div>
        </div>
      </div>
    </aside>
  );
}

function StatBar({
  label,
  valueLabel,
  pct,
  gradient,
  glow,
}: {
  label: string;
  valueLabel: string;
  pct: number;
  gradient: string;
  glow: string;
}) {
  return (
    <div style={{ display: "grid", gap: 5 }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          fontFamily: FONT_MONO,
          fontSize: 10,
          letterSpacing: ".16em",
          color: "rgba(232,220,196,.5)",
        }}
      >
        <span>{label}</span>
        <span>{valueLabel}</span>
      </div>
      <div style={{ height: 6, borderRadius: 6, background: "rgba(232,220,196,.08)", overflow: "hidden" }}>
        <div
          style={{
            height: "100%",
            borderRadius: 6,
            background: gradient,
            boxShadow: `0 0 14px -2px ${glow}`,
            transition: "width .5s ease",
            width: `${pct}%`,
          }}
        />
      </div>
    </div>
  );
}
