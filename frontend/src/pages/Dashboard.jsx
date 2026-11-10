import { useEffect, useState } from "react";
import {
  Bar, BarChart, CartesianGrid, Line, LineChart, PolarAngleAxis, PolarGrid,
  Radar, RadarChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { api } from "../api.js";
import { scoreClass } from "../components/Feedback.jsx";

const ACCENT = "#2457c5";
const INK = "#1b2a4a";

export default function Dashboard({ onOpen, onNew }) {
  const [stats, setStats] = useState(null);
  const [sessions, setSessions] = useState([]);
  const [error, setError] = useState("");

  const load = () =>
    Promise.all([api.stats(), api.listInterviews()])
      .then(([st, ss]) => { setStats(st); setSessions(ss); })
      .catch((e) => setError(e.message));

  useEffect(() => { load(); }, []);

  const remove = async (e, id) => {
    e.stopPropagation();
    if (!window.confirm("Delete this interview?")) return;
    await api.deleteInterview(id);
    load();
  };

  if (error) return <div className="banner error">{error}</div>;
  if (!stats) return <div className="center"><span className="spinner" /></div>;

  if (stats.total_sessions === 0) {
    return (
      <section className="card narrow center">
        <h1>No interviews yet</h1>
        <p className="muted">Your scores and progress will appear here after your first interview.</p>
        <button className="primary" onClick={onNew}>Start an interview</button>
      </section>
    );
  }

  const dims = stats.dimensions
    ? Object.entries(stats.dimensions).map(([k, v]) => ({ dim: k[0].toUpperCase() + k.slice(1), score: v }))
    : [];

  return (
    <>
      <div className="kpis">
        <div className="kpi"><span>Interviews</span><b>{stats.total_sessions}</b></div>
        <div className="kpi"><span>Answers graded</span><b>{stats.questions_answered}</b></div>
        <div className="kpi"><span>Better on a retry</span><b>{stats.improved_on_retry}</b></div>
        <div className="kpi"><span>Average score</span><b className={scoreClass(stats.overall_average)}>{stats.overall_average ?? "–"}</b></div>
      </div>

      <div className="charts">
        <section className="card">
          <h3>Score over time</h3>
          {stats.progress.length > 1 ? (
            <ResponsiveContainer width="100%" height={220}>
              <LineChart data={stats.progress}>
                <CartesianGrid stroke="#eee" />
                <XAxis dataKey="session" tickFormatter={(v) => `#${v}`} />
                <YAxis domain={[0, 10]} />
                <Tooltip labelFormatter={(v) => `Interview #${v}`} />
                <Line isAnimationActive={false} type="monotone" dataKey="score" stroke={ACCENT} strokeWidth={2} dot />
              </LineChart>
            </ResponsiveContainer>
          ) : <p className="muted">Complete one more interview to see a trend.</p>}
        </section>

        <section className="card">
          <h3>Where your answers are strong</h3>
          {dims.length ? (
            <ResponsiveContainer width="100%" height={220}>
              <RadarChart data={dims}>
                <PolarGrid />
                <PolarAngleAxis dataKey="dim" />
                <Radar isAnimationActive={false} dataKey="score" stroke={ACCENT} fill={ACCENT} fillOpacity={0.35} />
                <Tooltip />
              </RadarChart>
            </ResponsiveContainer>
          ) : <p className="muted">No answers yet.</p>}
        </section>
      </div>

      {stats.topics.length > 0 && (
        <section className="card">
          <h3>Score by topic</h3>
          <ResponsiveContainer width="100%" height={Math.max(160, stats.topics.length * 34)}>
            <BarChart data={stats.topics} layout="vertical" margin={{ left: 40 }}>
              <CartesianGrid stroke="#eee" horizontal={false} />
              <XAxis type="number" domain={[0, 10]} />
              <YAxis type="category" dataKey="topic" width={150} />
              <Tooltip />
              <Bar isAnimationActive={false} dataKey="score" fill={INK} radius={[0, 2, 2, 0]} barSize={18} />
            </BarChart>
          </ResponsiveContainer>
        </section>
      )}

      <section className="card">
        <h3>All interviews</h3>
        <table className="table">
          <thead><tr><th>#</th><th>Date</th><th>Role</th><th>Difficulty</th><th>Answered</th><th>Score</th><th /></tr></thead>
          <tbody>
            {sessions.map((s) => (
              <tr key={s.id} onClick={() => onOpen(s)}>
                <td>{s.id}</td>
                <td>{new Date(s.created_at).toLocaleDateString()}</td>
                <td>{s.role}</td>
                <td className="cap">{s.difficulty}</td>
                <td>{s.answered} of {s.total}{s.status !== "completed" && <span className="tag alt" style={{ marginLeft: 8 }}>unfinished</span>}</td>
                <td><span className={`pill ${scoreClass(s.average_score)}`}>{s.average_score ?? "?"}</span></td>
                <td><button className="link danger-text" onClick={(e) => remove(e, s.id)}>Delete</button></td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </>
  );
}
