"use client";

/**
 * hooks/useAmbientMusic.ts
 * Dynamic ambient soundscape using the Web Audio API.
 * Generates mood-appropriate ambient drones that shift with scene mood.
 * No external audio files — pure synthesis.
 */

import { useCallback, useEffect, useRef, useState } from "react";

type Mood = "peaceful" | "tense" | "dangerous" | "mysterious" | "dramatic" | "neutral";

interface MoodConfig {
  baseFreq: number;
  secondFreq: number;
  thirdFreq: number;
  lfoRate: number;
  filterFreq: number;
  gain: number;
  waveform: OscillatorType;
}

const MOOD_CONFIGS: Record<Mood, MoodConfig> = {
  peaceful: { baseFreq: 110, secondFreq: 165, thirdFreq: 220, lfoRate: 0.15, filterFreq: 800, gain: 0.3, waveform: "sine" },
  tense: { baseFreq: 92.5, secondFreq: 123.47, thirdFreq: 185, lfoRate: 0.5, filterFreq: 600, gain: 0.4, waveform: "triangle" },
  dangerous: { baseFreq: 82.41, secondFreq: 103.83, thirdFreq: 130.81, lfoRate: 1.2, filterFreq: 400, gain: 0.5, waveform: "sawtooth" },
  mysterious: { baseFreq: 130.81, secondFreq: 196, thirdFreq: 261.63, lfoRate: 0.25, filterFreq: 1200, gain: 0.28, waveform: "sine" },
  dramatic: { baseFreq: 98, secondFreq: 146.83, thirdFreq: 196, lfoRate: 0.8, filterFreq: 700, gain: 0.45, waveform: "triangle" },
  neutral: { baseFreq: 110, secondFreq: 146.83, thirdFreq: 220, lfoRate: 0.2, filterFreq: 600, gain: 0.25, waveform: "sine" },
};

export function useAmbientMusic() {
  const [isMusicMuted, setIsMusicMuted] = useState(false);
  const [currentMood, setCurrentMood] = useState<Mood>("neutral");

  const ctxRef = useRef<AudioContext | null>(null);
  const masterGainRef = useRef<GainNode | null>(null);
  const oscsRef = useRef<OscillatorNode[]>([]);
  const oscGainsRef = useRef<GainNode[]>([]);
  const lfoRef = useRef<OscillatorNode | null>(null);
  const filterRef = useRef<BiquadFilterNode | null>(null);
  const isInitRef = useRef(false);
  const hasUserInteracted = useRef(false);
  const currentMoodRef = useRef<Mood>("neutral");

  const initAudio = useCallback((mood: Mood = "neutral") => {
    if (isInitRef.current || typeof window === "undefined") return;

    try {
      const ctx = new (window.AudioContext || (window as any).webkitAudioContext)();
      ctxRef.current = ctx;

      const masterGain = ctx.createGain();
      masterGain.gain.value = 0;
      masterGain.connect(ctx.destination);
      masterGainRef.current = masterGain;

      const filter = ctx.createBiquadFilter();
      filter.type = "lowpass";
      filter.frequency.value = MOOD_CONFIGS[mood].filterFreq;
      filter.Q.value = 0.7;
      filter.connect(masterGain);
      filterRef.current = filter;

      const config = MOOD_CONFIGS[mood];
      const freqs = [config.baseFreq, config.secondFreq, config.thirdFreq];
      const gains = [1.0, 0.6, 0.3];

      const oscGains: GainNode[] = [];
      oscsRef.current = freqs.map((freq, i) => {
        const osc = ctx.createOscillator();
        const oscGain = ctx.createGain();
        osc.type = config.waveform;
        osc.frequency.value = freq;
        oscGain.gain.value = config.gain * gains[i];
        osc.connect(oscGain);
        oscGain.connect(filter);
        osc.start();
        oscGains.push(oscGain);
        return osc;
      });
      oscGainsRef.current = oscGains;

      const lfo = ctx.createOscillator();
      const lfoGain = ctx.createGain();
      lfo.frequency.value = config.lfoRate;
      lfo.type = "sine";
      lfoGain.gain.value = 0.02;
      lfo.connect(lfoGain);
      lfoGain.connect(masterGain.gain);
      lfo.start();
      lfoRef.current = lfo;

      isInitRef.current = true;

      ctx.resume().then(() => {
        masterGain.gain.linearRampToValueAtTime(config.gain, ctx.currentTime + 2);
      });
    } catch (err) {
      console.error("[AmbientMusic] Failed to initialize:", err);
    }
  }, []);

  const changeMood = useCallback((mood: Mood) => {
    const ctx = ctxRef.current;
    if (!ctx || !isInitRef.current) return;

    const config = MOOD_CONFIGS[mood];
    const now = ctx.currentTime;
    const fadeTime = 3;

    const freqs = [config.baseFreq, config.secondFreq, config.thirdFreq];
    const gains = [1.0, 0.6, 0.3];
    oscsRef.current.forEach((osc, i) => {
      if (freqs[i]) {
        osc.frequency.linearRampToValueAtTime(freqs[i], now + fadeTime);
        osc.type = config.waveform;
      }
    });
    oscGainsRef.current.forEach((g, i) => {
      g.gain.linearRampToValueAtTime(config.gain * gains[i], now + fadeTime);
    });

    if (filterRef.current) {
      filterRef.current.frequency.linearRampToValueAtTime(config.filterFreq, now + fadeTime);
    }
    if (lfoRef.current) {
      lfoRef.current.frequency.linearRampToValueAtTime(config.lfoRate, now + fadeTime);
    }
    if (masterGainRef.current) {
      masterGainRef.current.gain.linearRampToValueAtTime(config.gain, now + fadeTime);
    }
  }, []);

  const toggleMusic = useCallback(() => {
    setIsMusicMuted((prev) => {
      const willBeMuted = !prev;
      if (willBeMuted) {
        const ctx = ctxRef.current;
        if (ctx && masterGainRef.current) {
          masterGainRef.current.gain.linearRampToValueAtTime(0, ctx.currentTime + 0.5);
        }
      } else {
        if (!isInitRef.current) {
          initAudio(currentMoodRef.current);
        } else {
          ctxRef.current?.resume();
          const ctx = ctxRef.current;
          const config = MOOD_CONFIGS[currentMoodRef.current];
          if (ctx && masterGainRef.current) {
            masterGainRef.current.gain.linearRampToValueAtTime(config.gain, ctx.currentTime + 1);
          }
        }
      }
      return willBeMuted;
    });
  }, [initAudio]);

  useEffect(() => {
    currentMoodRef.current = currentMood;
  }, [currentMood]);

  // Init on first user interaction (browser autoplay policy)
  useEffect(() => {
    const handler = () => {
      if (!hasUserInteracted.current) {
        hasUserInteracted.current = true;
        if (!isMusicMuted && !isInitRef.current) {
          initAudio(currentMoodRef.current);
        } else if (isInitRef.current) {
          ctxRef.current?.resume();
        }
      }
      window.removeEventListener("click", handler);
      window.removeEventListener("keydown", handler);
    };
    window.addEventListener("click", handler);
    window.addEventListener("keydown", handler);
    return () => {
      window.removeEventListener("click", handler);
      window.removeEventListener("keydown", handler);
    };
  }, [isMusicMuted, initAudio]);

  // React to mood changes
  useEffect(() => {
    if (isMusicMuted) return;
    if (isInitRef.current) changeMood(currentMood);
  }, [currentMood, isMusicMuted, changeMood]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      oscsRef.current.forEach((osc) => {
        try {
          osc.stop();
        } catch {}
      });
      try {
        lfoRef.current?.stop();
      } catch {}
      try {
        ctxRef.current?.close();
      } catch {}
    };
  }, []);

  return {
    isMusicMuted,
    toggleMusic,
    setMood: (mood: string) => {
      const validMood = (mood in MOOD_CONFIGS ? mood : "neutral") as Mood;
      setCurrentMood(validMood);
    },
    currentMood,
  };
}