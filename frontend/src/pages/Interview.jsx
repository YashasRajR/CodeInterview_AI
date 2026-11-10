import { useEffect, useRef, useState } from "react";
import { api } from "../api.js";
import { useSpeech } from "../useSpeech.js";
import Feedback from "../components/Feedback.jsx";

function formatTime(total) {
  const t = Math.abs(total);
  return `${total < 0 ? "-" : ""}${Math.floor(t / 60)}:${String(t % 60).padStart(2, "0")}`;
}

/** Counts up from the moment a question is shown. Returns elapsed seconds and a reset function. */
function useStopwatch(running) {
  const [elapsed, setElapsed] = useState(0);
  const startRef = useRef(Date.now());
  useEffect(() => {
    if (!running) return;
    const id = setInterval(() => setElapsed(Math.floor((Date.now() - startRef.current) / 1000)), 500);
    return () => clearInterval(id);
  }, [running]);
  const reset = () => { startRef.current = Date.now(); setElapsed(0); };
  return { elapsed, reset };
}

export default function Interview({ id, onFinished }) {
  const [session, setSession] = useState(null);
  const [index, setIndex] = useState(0);
  const [answer, setAnswer] = useState("");
  const [result, setResult] = useState(null);
  const [hint, setHint] = useState("");
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const speech = useSpeech((text) => setAnswer((a) => (a ? a + " " : "") + text));
  const clock = useStopwatch(Boolean(session) && !result);

  useEffect(() => {
    api.getInterview(id).then((s) => {
      setSession(s);
      const next = s.questions.findIndex((q) => q.score === null);
      setIndex(next === -1 ? s.questions.length - 1 : next);
      clock.reset();
    }).catch((e) => setError(e.message));
  }, [id]);

  if (error && !session) return <div className="banner error">{error}</div>;
  if (!session) return <div className="center"><span className="spinner" /></div>;

  const q = session.questions[index];
  const total = session.questions.length;
  const isLast = index === total - 1;
  const limit = session.time_limit;
  const remaining = limit ? limit - clock.elapsed : null;
  const canFollowUp = result && q.type !== "follow-up" && !q.has_followup;

  const run = async (label, fn) => {
    setBusy(label);
    setError("");
    try { await fn(); } catch (e) { setError(e.message); } finally { setBusy(""); }
  };

  const submit = (text = answer) => run("grade", async () => {
    speech.stop();
    const r = await api.submitAnswer(id, q.id, text, clock.elapsed);
    setResult({ ...r.feedback, previous: r.previous_score });
    setSession((s) => ({
      ...s,
      questions: s.questions.map((x) => (x.id === q.id
        ? { ...x, answer: text, score: r.score, feedback: r.feedback, attempts: r.attempts } : x)),
    }));
  });

  const getHint = () => run("hint", async () => setHint((await api.hint(id, q.id)).hint));

  const goTo = (i) => {
    setIndex(i);
    setAnswer("");
    setResult(null);
    setHint("");
    clock.reset();
  };

  const retry = () => { setAnswer(""); setResult(null); clock.reset(); };

  const followUp = () => run("follow", async () => {
    const s = await api.followup(id, q.id);
    setSession(s);
    goTo(index + 1);
  });

  const next = () => run("next", async () => {
    if (isLast) {
      await api.complete(id);
      onFinished(id);
    } else {
      goTo(index + 1);
    }
  });

  return (
    <section className="card">
      <div className="progress-head">
        <span className="counter">Question {index + 1} of {total}</span>
        <span className="tags">
          {q.type === "follow-up" && <span className="tag followup">Follow-up</span>}
          <span className="tag">{q.topic}</span>
          {q.type !== "follow-up" && <span className="tag alt">{q.type}</span>}
        </span>
      </div>
      <div className="progress" aria-hidden="true">
        {session.questions.map((x) => <span key={x.id} className={x.score !== null ? "done" : ""} />)}
      </div>

      <h2 className="question">{q.question}</h2>

      {!result ? (
        <>
          {hint && <p className="hint"><span className="hint-label">Hint</span>{hint}</p>}
          <div className="answer-head">
            <span className="muted small">{q.attempts > 0 ? `Attempt ${q.attempts + 1}. Your last score was ${q.score}.` : "Your answer"}</span>
            <span className={`timer ${remaining !== null && remaining < 0 ? "over" : remaining !== null && remaining <= 15 ? "low" : ""}`}
              aria-label={remaining !== null ? "Time remaining" : "Time spent"}>
              {remaining !== null ? formatTime(remaining) : formatTime(clock.elapsed)}
            </span>
          </div>
          <textarea
            value={answer}
            onChange={(e) => setAnswer(e.target.value)}
            placeholder="Explain it the way you would to the interviewer."
            rows={8}
            disabled={Boolean(busy)}
          />
          {remaining !== null && remaining < 0 && (
            <p className="muted small">Time is up. In a real interview, wrap up your point and move on.</p>
          )}
          <div className="row">
            {speech.supported ? (
              <button className={speech.listening ? "danger" : "ghost"} onClick={speech.listening ? speech.stop : speech.start} disabled={Boolean(busy)}>
                {speech.listening ? "Stop recording" : "Answer by voice"}
              </button>
            ) : (
              <span className="muted small">Voice answers need Chrome or Edge.</span>
            )}
            {!hint && (
              <button className="ghost" onClick={getHint} disabled={Boolean(busy)}>
                {busy === "hint" ? <><span className="spinner" /> Thinking</> : "Get a hint"}
              </button>
            )}
            <span className="spacer" />
            <button className="ghost" onClick={() => { setAnswer(""); submit(""); }} disabled={Boolean(busy)}>Skip</button>
            <button className="primary" onClick={() => submit()} disabled={Boolean(busy) || !answer.trim()}>
              {busy === "grade" ? <><span className="spinner" /> Grading</> : "Submit answer"}
            </button>
          </div>
          {speech.listening && <p className="recording">Listening. Speak your answer.</p>}
        </>
      ) : (
        <>
          {result.previous !== null && result.previous !== undefined && (
            <p className={`delta ${result.score > result.previous ? "good" : result.score < result.previous ? "bad" : ""}`}>
              {result.score > result.previous ? `Up from ${result.previous}. Nice work.`
                : result.score < result.previous ? `Down from ${result.previous}. Your earlier answer was stronger.`
                : `Same score as before (${result.previous}).`}
            </p>
          )}
          <Feedback feedback={result} answer={answer} />
          <div className="row">
            <button className="ghost" onClick={retry} disabled={Boolean(busy)}>Try again</button>
            {canFollowUp && (
              <button className="ghost" onClick={followUp} disabled={Boolean(busy)}>
                {busy === "follow" ? <><span className="spinner" /> Writing a follow-up</> : "Ask me a follow-up"}
              </button>
            )}
            <span className="spacer" />
            <button className="primary" onClick={next} disabled={Boolean(busy)}>{isLast ? "See my report" : "Next question"}</button>
          </div>
        </>
      )}
      {error && <div className="banner error">{error}</div>}
    </section>
  );
}
