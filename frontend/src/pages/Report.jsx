import { useEffect, useState } from "react";

const fmt = (t) => `${Math.floor(t / 60)}:${String(t % 60).padStart(2, "0")}`;
import { api } from "../api.js";
import Feedback, { ScoreMark, scoreClass } from "../components/Feedback.jsx";

export default function Report({ id, onBack }) {
  const [s, setS] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => { api.getInterview(id).then(setS).catch((e) => setError(e.message)); }, [id]);

  // Open every answer before printing so the PDF includes all feedback.
  useEffect(() => {
    const open = () => document.querySelectorAll("details").forEach((d) => { d.dataset.wasOpen = d.open; d.open = true; });
    const restore = () => document.querySelectorAll("details").forEach((d) => { d.open = d.dataset.wasOpen === "true"; });
    window.addEventListener("beforeprint", open);
    window.addEventListener("afterprint", restore);
    return () => { window.removeEventListener("beforeprint", open); window.removeEventListener("afterprint", restore); };
  }, []);

  if (error) return <div className="banner error">{error}</div>;
  if (!s) return <div className="center"><span className="spinner" /></div>;

  const answered = s.questions.filter((q) => q.feedback);
  const weakest = [...new Set([...answered].sort((a, b) => a.score - b.score).map((q) => q.topic))].slice(0, 2);

  return (
    <section className="card">
      <div className="row no-print" style={{ marginTop: 0 }}>
        <button className="link" onClick={onBack}>Back to dashboard</button>
        <span className="spacer" />
        <button className="ghost" onClick={() => window.print()}>Save as PDF</button>
      </div>
      <div className="report-head">
        <div>
          <h1>Your interview report</h1>
          <p className="muted">{s.role}, <span className="cap">{s.difficulty}</span> difficulty, {new Date(s.created_at).toLocaleDateString()}</p>
          {(s.targeted || s.average_time) && (
            <p className="muted small">
              {s.targeted && "Targeted at a job description. "}
              {s.average_time && `Average time per answer: ${fmt(s.average_time)}.`}
            </p>
          )}
          {s.skills.length > 0 && (
            <div className="tags wrap">{s.skills.map((k) => <span key={k} className="tag">{k}</span>)}</div>
          )}
        </div>
        <ScoreMark score={s.average_score} />
      </div>

      {weakest.length > 0 && (
        <div className="banner info">
          Practise these next: <b>{weakest.join(" and ")}</b>
        </div>
      )}

      {s.questions.map((q, i) => (
        <details key={q.id} className="qa" open={i === 0}>
          <summary>
            <span className={`pill ${scoreClass(q.score)}`}>{q.score ?? "?"}</span>
            <span>
              <b>{q.type === "follow-up" ? "Follow-up." : `Question ${i + 1}.`}</b> {q.question}
              {(q.time_seconds || q.attempts > 1) && (
                <span className="qa-meta">
                  {q.time_seconds ? ` Answered in ${fmt(q.time_seconds)}.` : ""}
                  {q.attempts > 1 ? ` ${q.attempts} attempts, previous score ${q.previous_score}.` : ""}
                </span>
              )}
            </span>
          </summary>
          {q.feedback ? <Feedback feedback={q.feedback} answer={q.answer} /> : <p className="muted">You skipped this question.</p>}
        </details>
      ))}
    </section>
  );
}
