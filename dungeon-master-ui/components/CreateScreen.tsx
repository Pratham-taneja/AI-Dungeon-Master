"use client";

import { CLASSES } from "@/lib/constants";
import { FONT_CINZEL, FONT_MONO, FONT_SERIF } from "@/lib/fonts";
import type { GameSession } from "@/hooks/useGameSession";

export default function CreateScreen({ gs }: { gs: GameSession }) {
  return (
    <div
      style={{
        position: "relative",
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "48px 24px",
        overflow: "hidden",
        background:
          "radial-gradient(120% 90% at 50% 0%, #221a12 0%, #120e0b 45%, #080706 100%)",
      }}
    >
      <div
        style={{
          position: "absolute",
          inset: 0,
          background:
            "radial-gradient(60% 45% at 50% 8%, rgba(201,162,39,.16), transparent 70%)",
          pointerEvents: "none",
        }}
      />
      <div
        style={{
          position: "absolute",
          inset: 0,
          backgroundImage:
            "radial-gradient(rgba(232,220,196,.055) 1px, transparent 1px)",
          backgroundSize: "3px 3px",
          mixBlendMode: "overlay",
          pointerEvents: "none",
        }}
      />

      <div
        style={{
          position: "relative",
          width: "100%",
          maxWidth: 880,
          background: "rgba(20,16,13,.62)",
          backdropFilter: "blur(18px)",
          WebkitBackdropFilter: "blur(18px)",
          border: "1px solid rgba(201,162,39,.22)",
          borderRadius: 4,
          boxShadow: "0 40px 120px -30px rgba(0,0,0,.9), inset 0 1px 0 rgba(232,220,196,.06)",
          padding: "44px 44px 36px",
        }}
      >
        <div style={{ textAlign: "center", marginBottom: 34 }}>
          <div
            style={{
              fontFamily: FONT_MONO,
              fontSize: 11,
              letterSpacing: ".42em",
              textTransform: "uppercase",
              color: "rgba(201,162,39,.75)",
              marginBottom: 14,
            }}
          >
            Chronicle the First
          </div>
          <h1
            style={{
              fontFamily: FONT_CINZEL,
              fontWeight: 600,
              fontSize: 44,
              lineHeight: 1.1,
              letterSpacing: ".06em",
              margin: 0,
              color: "#e9d9ae",
              textShadow: "0 0 40px rgba(201,162,39,.25)",
            }}
          >
            AI Dungeon Master
          </h1>
          <div
            style={{
              width: 120,
              height: 1,
              margin: "20px auto 0",
              background: "linear-gradient(90deg,transparent,rgba(201,162,39,.6),transparent)",
            }}
          />
          <p
            style={{
              margin: "18px auto 0",
              maxWidth: 520,
              fontSize: 17,
              lineHeight: 1.6,
              color: "rgba(232,220,196,.62)",
              fontStyle: "italic",
              textWrap: "pretty",
            }}
          >
            The world has not yet been written. Give it a name to bleed for, and the telling begins.
          </p>
        </div>

        <div style={{ display: "grid", gap: 26 }}>
          <div style={{ display: "grid", gap: 9 }}>
            <label
              style={{
                fontFamily: FONT_MONO,
                fontSize: 10,
                letterSpacing: ".28em",
                textTransform: "uppercase",
                color: "rgba(232,220,196,.5)",
              }}
            >
              Name
            </label>
            <input
              className="dm-input"
              value={gs.name}
              onChange={(e) => gs.setName(e.target.value)}
              placeholder="Who walks into the dark?"
              style={{
                width: "100%",
                background: "rgba(12,10,8,.7)",
                border: "1px solid rgba(201,162,39,.22)",
                borderRadius: 3,
                padding: "14px 16px",
                color: "#e8dcc4",
                fontFamily: FONT_SERIF,
                fontSize: 19,
                outline: "none",
              }}
            />
          </div>

          <div style={{ display: "grid", gap: 12 }}>
            <label
              style={{
                fontFamily: FONT_MONO,
                fontSize: 10,
                letterSpacing: ".28em",
                textTransform: "uppercase",
                color: "rgba(232,220,196,.5)",
              }}
            >
              Calling
            </label>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(3,1fr)",
                gap: 10,
              }}
            >
              {CLASSES.map((c) => {
                const active = gs.playerClass === c.id;
                return (
                  <button
                    key={c.id}
                    type="button"
                    onClick={() => gs.setPlayerClass(c.id)}
                    className="dm-class-card"
                    style={{
                      textAlign: "left",
                      cursor: "pointer",
                      background: active ? "rgba(201,162,39,.12)" : "rgba(12,10,8,.5)",
                      border: `1px solid ${active ? "rgba(201,162,39,.6)" : "rgba(232,220,196,.09)"}`,
                      borderRadius: 3,
                      padding: "16px 16px 14px",
                      color: "inherit",
                      fontFamily: "inherit",
                      transition: "all .2s ease",
                    }}
                  >
                    <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 7 }}>
                      <span
                        style={{
                          fontSize: 19,
                          color: active ? "#c9a227" : "rgba(232,220,196,.55)",
                          lineHeight: 1,
                        }}
                      >
                        {c.icon}
                      </span>
                      <span
                        style={{
                          fontFamily: FONT_CINZEL,
                          fontSize: 15,
                          letterSpacing: ".08em",
                          textTransform: "capitalize",
                          color: active ? "#f0e3bd" : "rgba(232,220,196,.8)",
                        }}
                      >
                        {c.id}
                      </span>
                    </div>
                    <div
                      style={{
                        fontSize: 14,
                        lineHeight: 1.45,
                        color: "rgba(232,220,196,.5)",
                        fontStyle: "italic",
                      }}
                    >
                      {c.flavor}
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          <div style={{ display: "grid", gap: 9 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
              <label
                style={{
                  fontFamily: FONT_MONO,
                  fontSize: 10,
                  letterSpacing: ".28em",
                  textTransform: "uppercase",
                  color: "rgba(232,220,196,.5)",
                }}
              >
                Backstory
              </label>
              <span
                style={{
                  fontFamily: FONT_MONO,
                  fontSize: 10,
                  letterSpacing: ".12em",
                  color: "rgba(232,220,196,.32)",
                }}
              >
                optional — the DM will invent one
              </span>
            </div>
            <textarea
              className="dm-input"
              value={gs.backstory}
              onChange={(e) => gs.setBackstory(e.target.value)}
              rows={3}
              placeholder="Left blank, the Dungeon Master will write you a past you may not enjoy."
              style={{
                width: "100%",
                resize: "vertical",
                background: "rgba(12,10,8,.7)",
                border: "1px solid rgba(201,162,39,.22)",
                borderRadius: 3,
                padding: "14px 16px",
                color: "#e8dcc4",
                fontFamily: FONT_SERIF,
                fontSize: 17,
                lineHeight: 1.55,
                outline: "none",
              }}
            />
          </div>

          <button
            type="button"
            onClick={() => void gs.begin()}
            disabled={gs.beginning}
            className="dm-begin-btn"
            style={{
              marginTop: 6,
              width: "100%",
              cursor: gs.beginning ? "default" : "pointer",
              background: "linear-gradient(180deg, rgba(201,162,39,.22), rgba(201,162,39,.08))",
              border: "1px solid rgba(201,162,39,.5)",
              borderRadius: 3,
              padding: 17,
              fontFamily: FONT_CINZEL,
              fontSize: 15,
              letterSpacing: ".24em",
              textTransform: "uppercase",
              color: "#f0dfae",
              opacity: gs.beginning ? 0.6 : 1,
              transition: "all .25s ease",
            }}
          >
            {gs.beginning ? "Weaving the world" : "Begin Adventure"}
          </button>

          {gs.beginning && (
            <div
              style={{
                textAlign: "center",
                fontFamily: FONT_MONO,
                fontSize: 11,
                letterSpacing: ".2em",
                color: "rgba(201,162,39,.7)",
              }}
            >
              drawing the map · seeding the ruins · waking the dead
            </div>
          )}

          {gs.createError && (
            <div
              style={{
                textAlign: "center",
                fontFamily: FONT_MONO,
                fontSize: 12,
                letterSpacing: ".05em",
                color: "#c1452f",
              }}
            >
              {gs.createError}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
