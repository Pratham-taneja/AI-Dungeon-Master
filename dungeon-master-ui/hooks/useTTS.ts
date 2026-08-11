"use client";

/**
 * hooks/useTTS.ts
 * Text-to-Speech narration using the Web Speech API.
 * Speaks DM narrative with a deep, dramatic voice.
 */

import { useCallback, useEffect, useRef, useState } from "react";

export function useTTS() {
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const utteranceRef = useRef<SpeechSynthesisUtterance | null>(null);

  // Pick the best available voice (prefer deep English voice)
  const getVoice = useCallback((): SpeechSynthesisVoice | null => {
    if (typeof window === "undefined") return null;
    const voices = window.speechSynthesis.getVoices();
    const preferred = [
      "Daniel",
      "Google UK English Male",
      "Google US English",
      "Microsoft David",
      "Alex",
    ];
    for (const name of preferred) {
      const found = voices.find((v) => v.name.includes(name));
      if (found) return found;
    }
    return voices.find((v) => v.lang.startsWith("en")) || voices[0] || null;
  }, []);

  const speak = useCallback(
    (text: string) => {
      if (typeof window === "undefined" || isMuted) return;
      window.speechSynthesis.cancel();

      // Strip markdown, code blocks, and any stray JSON before speaking
      const clean = text
        .replace(/```[\s\S]*?```/g, "")
        .replace(/[*_#`]/g, "")
        .replace(/\{[\s\S]*?\}/g, "")
        .trim();

      if (!clean) return;

      const utterance = new SpeechSynthesisUtterance(clean);
      const voice = getVoice();
      if (voice) utterance.voice = voice;
      utterance.rate = 0.95;
      utterance.pitch = 0.85;
      utterance.volume = 1;

      utterance.onstart = () => setIsSpeaking(true);
      utterance.onend = () => setIsSpeaking(false);
      utterance.onerror = () => setIsSpeaking(false);

      utteranceRef.current = utterance;
      window.speechSynthesis.speak(utterance);
    },
    [isMuted, getVoice]
  );

  const stop = useCallback(() => {
    if (typeof window === "undefined") return;
    window.speechSynthesis.cancel();
    setIsSpeaking(false);
  }, []);

  const toggleMute = useCallback(() => {
    setIsMuted((prev) => {
      if (!prev) {
        window.speechSynthesis?.cancel();
        setIsSpeaking(false);
      }
      return !prev;
    });
  }, []);

  // Preload voices (Chrome needs this — voice list loads async)
  useEffect(() => {
    if (typeof window === "undefined") return;
    window.speechSynthesis.getVoices();
    window.speechSynthesis.onvoiceschanged = () => {
      window.speechSynthesis.getVoices();
    };
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      window.speechSynthesis?.cancel();
    };
  }, []);

  return { speak, stop, isSpeaking, isMuted, toggleMute };
}