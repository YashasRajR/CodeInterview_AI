import { useEffect, useRef, useState } from "react";

/** Voice input using the browser's Web Speech API (works in Chrome and Edge). */
export function useSpeech(onText) {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  const supported = Boolean(SpeechRecognition);
  const [listening, setListening] = useState(false);
  const recRef = useRef(null);
  const cbRef = useRef(onText);
  cbRef.current = onText;

  useEffect(() => () => recRef.current?.stop(), []);

  const start = () => {
    if (!supported || listening) return;
    const rec = new SpeechRecognition();
    rec.lang = "en-IN";
    rec.continuous = true;
    rec.interimResults = false;
    rec.onresult = (e) => {
      let text = "";
      for (let i = e.resultIndex; i < e.results.length; i++) {
        if (e.results[i].isFinal) text += e.results[i][0].transcript;
      }
      if (text) cbRef.current(text.trim());
    };
    rec.onend = () => setListening(false);
    rec.onerror = () => setListening(false);
    recRef.current = rec;
    rec.start();
    setListening(true);
  };

  const stop = () => {
    recRef.current?.stop();
    setListening(false);
  };

  return { supported, listening, start, stop };
}
