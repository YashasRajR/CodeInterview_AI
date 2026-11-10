import { useRef, useState } from "react";
import { api } from "../api.js";

const ROLES = ["Software Engineer", "ML Engineer", "Data Scientist", "Frontend Developer", "Backend Developer", "Full Stack Developer"];

export default function Setup({ onStarted }) {
  const [file, setFile] = useState(null);
  const [role, setRole] = useState("Software Engineer");
  const [difficulty, setDifficulty] = useState("medium");
  const [count, setCount] = useState(5);
  const [timeLimit, setTimeLimit] = useState(0);
  const [jobDescription, setJobDescription] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [drag, setDrag] = useState(false);
  const inputRef = useRef(null);

  const pick = (f) => {
    setError("");
    if (f && f.type !== "application/pdf" && !f.name.toLowerCase().endsWith(".pdf")) {
      setError("Please choose a PDF file.");
      return;
    }
    setFile(f || null);
  };

  const submit = async (e) => {
    e.preventDefault();
    if (!file) return setError("Add your resume PDF to start.");
    const fd = new FormData();
    fd.append("resume", file);
    fd.append("role", role);
    fd.append("difficulty", difficulty);
    fd.append("count", count);
    fd.append("time_limit", timeLimit);
    fd.append("job_description", jobDescription);
    setLoading(true);
    setError("");
    try {
      onStarted(await api.startInterview(fd));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
    <div className="intro">
      <h1>Walk into the interview already warmed up.</h1>
      <p className="muted">Give it your resume. It asks the questions an interviewer would ask about your projects, then grades each answer and shows you what to fix.</p>
    </div>
    <section className="card narrow">
      <form onSubmit={submit}>
        <div
          className={`dropzone ${drag ? "drag" : ""} ${file ? "has-file" : ""}`}
          onClick={() => inputRef.current.click()}
          onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
          onDragLeave={() => setDrag(false)}
          onDrop={(e) => { e.preventDefault(); setDrag(false); pick(e.dataTransfer.files[0]); }}
        >
          <input ref={inputRef} type="file" accept="application/pdf" hidden onChange={(e) => pick(e.target.files[0])} />
          {file ? <><strong>{file.name}</strong><span className="muted">Click to choose a different file</span></>
                : <><strong>Drop your resume here</strong><span className="muted">PDF, up to 5 MB, or click to browse</span></>}
        </div>

        <div className="grid3">
          <label>Target role
            <select value={role} onChange={(e) => setRole(e.target.value)}>
              {ROLES.map((r) => <option key={r}>{r}</option>)}
            </select>
          </label>
          <label>Difficulty
            <select value={difficulty} onChange={(e) => setDifficulty(e.target.value)}>
              <option value="easy">Easy</option>
              <option value="medium">Medium</option>
              <option value="hard">Hard</option>
            </select>
          </label>
          <label>How many
            <select value={count} onChange={(e) => setCount(Number(e.target.value))}>
              {[3, 5, 7, 10].map((n) => <option key={n}>{n}</option>)}
            </select>
          </label>
        </div>

        <div className="grid2">
          <label>Timer per question
            <select value={timeLimit} onChange={(e) => setTimeLimit(Number(e.target.value))}>
              <option value={0}>No timer</option>
              <option value={60}>1 minute</option>
              <option value={120}>2 minutes</option>
              <option value={180}>3 minutes</option>
              <option value={300}>5 minutes</option>
            </select>
          </label>
        </div>

        <details className="jd" open={Boolean(jobDescription)}>
          <summary>Practising for a specific job? Paste the job description</summary>
          <textarea
            className="plain"
            value={jobDescription}
            onChange={(e) => setJobDescription(e.target.value)}
            rows={6}
            maxLength={3000}
            placeholder="Paste the job posting here. Questions will focus on the skills it asks for."
          />
          <span className="muted small">{jobDescription.length} of 3000 characters</span>
        </details>

        {error && <div className="banner error">{error}</div>}
        <button className="primary big" disabled={loading}>
          {loading ? <><span className="spinner" /> Reading your resume</> : "Start interview"}
        </button>
        {loading && <p className="muted small center">Writing questions on your computer. This takes 20 to 60 seconds.</p>}
      </form>
    </section>
    </>
  );
}
