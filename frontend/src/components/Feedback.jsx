export function scoreClass(score) {
  if (score === null || score === undefined) return "none";
  if (score >= 7.5) return "good";
  if (score >= 5) return "ok";
  return "bad";
}

/** A score written in marker and circled, the way an interviewer grades on a whiteboard. */
export function ScoreMark({ score }) {
  return (
    <div className={`mark ${scoreClass(score)}`} aria-label={score == null ? "Not scored" : `Score ${score} out of 10`}>
      <svg viewBox="0 0 140 96" aria-hidden="true">
        <path d="M78 8 C118 6 136 30 130 54 C123 82 46 92 18 70 C-2 54 6 20 44 10 C60 6 74 7 88 11"
          fill="none" stroke="currentColor" strokeWidth="3.5" strokeLinecap="round" />
      </svg>
      <span>{score ?? "?"}<small>/10</small></span>
    </div>
  );
}

export default function Feedback({ feedback, answer }) {
  if (!feedback) return null;
  return (
    <div className="feedback">
      <div className="scores">
        <ScoreMark score={feedback.score} />
        {["accuracy", "depth", "clarity"].map((k) => (
          <div key={k} className="bar-row">
            <span>{k}</span>
            <div className="bar"><div className={scoreClass(feedback[k])} style={{ width: `${feedback[k] * 10}%` }} /></div>
            <b>{feedback[k]}</b>
          </div>
        ))}
      </div>
      <div className="notes">
        <div className="pos">
          <p className="note-head good">Good</p>
          {feedback.strengths.length
            ? <ul>{feedback.strengths.map((s, i) => <li key={i}>{s}</li>)}</ul>
            : <p className="muted">Nothing stood out yet.</p>}
        </div>
        <div className="neg">
          <p className="note-head bad">Work on this</p>
          <ul>{feedback.improvements.map((s, i) => <li key={i}>{s}</li>)}</ul>
        </div>
      </div>
      {answer !== undefined && (
        <details>
          <summary>Your answer</summary>
          <p className="answer-text">{answer || <em>Skipped</em>}</p>
        </details>
      )}
      {feedback.model_answer && (
        <details open>
          <summary>What a strong answer covers</summary>
          <p className="answer-text model">{feedback.model_answer}</p>
        </details>
      )}
    </div>
  );
}
