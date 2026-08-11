"use client";

import type { CSSProperties } from "react";
import { getBiomeGradient, getMoodDot, getMoodOverlay } from "@/lib/constants";
import { FONT_CINZEL, FONT_MONO } from "@/lib/fonts";
import type { Location } from "@/lib/types";

export default function SceneHeader({
  location,
  mood,
  sceneImageUrl,
  leftOpen,
  rightOpen,
  onToggleLeft,
  onToggleRight,
  isMuted,
  onToggleMute,
  isMusicMuted,
  onToggleMusic,
}: {
  location: Location;
  mood: string;
  sceneImageUrl: string | null;
  leftOpen: boolean;
  rightOpen: boolean;
  onToggleLeft: () => void;
  onToggleRight: () => void;
  isMuted: boolean;
  onToggleMute: () => void;
  isMusicMuted: boolean;
  onToggleMusic: () => void;
}) {
  return (
    <div
      style={{
        position: "relative",
        height: 236,
        flex: "none",
        overflow: "hidden",
        borderBottom: "1px solid rgba(201,162,39,.18)",
      }}
    >
      {/* Base layer: generated scene image if we have one, else the biome gradient */}
      {sceneImageUrl ? (
        <div
          style={{
            position: "absolute",
            inset: 0,
            backgroundImage: `url(${sceneImageUrl})`,
            backgroundSize: "cover",
            backgroundPosition: "center",
            transition: "opacity .6s ease",
          }}
        />
      ) : (
        <div
          style={{
            position: "absolute",
            inset: 0,
            background: getBiomeGradient(location.biome),
            animation: "dm-drift 26s ease-in-out infinite alternate",
          }}
        />
      )}

      <div
        style={{
          position: "absolute",
          inset: 0,
          background: getMoodOverlay(mood),
          mixBlendMode: "soft-light",
        }}
      />
      <div
        style={{
          position: "absolute",
          inset: 0,
          background:
            "linear-gradient(180deg, rgba(8,7,6,.55) 0%, rgba(8,7,6,0) 35%, rgba(11,10,9,.92) 100%)",
        }}
      />
      <div
        style={{
          position: "absolute",
          inset: 0,
          backgroundImage: "radial-gradient(rgba(232,220,196,.05) 1px, transparent 1px)",
          backgroundSize: "3px 3px",
          mixBlendMode: "overlay",
        }}
      />

      <div
        style={{
          position: "absolute",
          top: 16,
          left: 20,
          right: 20,
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
          gap: 16,
        }}
      >
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <button
            type="button"
            onClick={onToggleLeft}
            className="dm-toolbar-btn"
            style={toolbarBtnStyle(leftOpen)}
          >
            HERO
          </button>
          <button
            type="button"
            onClick={onToggleRight}
            className="dm-toolbar-btn"
            style={toolbarBtnStyle(rightOpen)}
          >
            WORLD
          </button>
          <button
            type="button"
            onClick={onToggleMute}
            className="dm-toolbar-btn"
            style={toolbarBtnStyle(!isMuted)}
            title={isMuted ? "Unmute narration" : "Mute narration"}
          >
            {isMuted ? "VOICE OFF" : "VOICE ON"}
          </button>
          <button
            type="button"
            onClick={onToggleMusic}
            className="dm-toolbar-btn"
            style={toolbarBtnStyle(!isMusicMuted)}
            title={isMusicMuted ? "Unmute music" : "Mute music"}
          >
            {isMusicMuted ? "MUSIC OFF" : "MUSIC ON"}
          </button>
        </div>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 8,
            background: "rgba(14,12,10,.5)",
            backdropFilter: "blur(10px)",
            border: "1px solid rgba(201,162,39,.2)",
            borderRadius: 3,
            padding: "7px 12px",
          }}
        >
          <span
            style={{
              width: 7,
              height: 7,
              borderRadius: "50%",
              background: getMoodDot(mood),
              boxShadow: `0 0 12px ${getMoodDot(mood)}`,
            }}
          />
          <span
            style={{
              fontFamily: FONT_MONO,
              fontSize: 10,
              letterSpacing: ".22em",
              textTransform: "uppercase",
              color: "rgba(232,220,196,.78)",
            }}
          >
            {mood}
          </span>
        </div>
      </div>

      <div style={{ position: "absolute", left: 24, bottom: 18, right: 24 }}>
        <div
          style={{
            fontFamily: FONT_MONO,
            fontSize: 10,
            letterSpacing: ".3em",
            textTransform: "uppercase",
            color: "rgba(201,162,39,.75)",
            marginBottom: 6,
          }}
        >
          {location.biome}
          {location.is_dangerous ? " · dangerous" : ""}
        </div>
        <h2
          style={{
            margin: 0,
            fontFamily: FONT_CINZEL,
            fontWeight: 600,
            fontSize: 30,
            letterSpacing: ".05em",
            color: "#f0e3bd",
            textShadow: "0 4px 30px rgba(0,0,0,.8)",
          }}
        >
          {location.name}
        </h2>
        <p
          style={{
            margin: "6px 0 0",
            maxWidth: 620,
            fontSize: 16,
            lineHeight: 1.5,
            color: "rgba(232,220,196,.6)",
            fontStyle: "italic",
            textWrap: "pretty",
          }}
        >
          {location.description}
        </p>
      </div>
    </div>
  );
}

function toolbarBtnStyle(active: boolean): CSSProperties {
  return {
    cursor: "pointer",
    background: active ? "rgba(201,162,39,.16)" : "rgba(14,12,10,.55)",
    backdropFilter: "blur(10px)",
    border: "1px solid rgba(201,162,39,.24)",
    borderRadius: 3,
    color: "rgba(232,220,196,.8)",
    fontFamily: FONT_MONO,
    fontSize: 10,
    letterSpacing: ".18em",
    padding: "7px 11px",
  };
}