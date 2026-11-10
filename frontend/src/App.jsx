import { useEffect, useState } from "react";
import { api } from "./api.js";
import Setup from "./pages/Setup.jsx";
import Interview from "./pages/Interview.jsx";
import Report from "./pages/Report.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import Logo from "./components/Logo.jsx";

export default function App() {
  // view: { name: "setup" | "interview" | "report" | "dashboard", id? }
  const [view, setView] = useState({ name: "setup" });
  const [health, setHealth] = useState(null);

  useEffect(() => {
    api.health().then(setHealth).catch(() =>
      setHealth({ ok: false, message: "Backend is not running. Start it with `python app.py`." })
    );
  }, []);

  return (
    <div className="app">
      <header className="topbar">
        <button className="brand" onClick={() => setView({ name: "setup" })} aria-label="CodeInterview AI home">
          <Logo />
          <span>CodeInterview<span className="logo">.ai</span></span>
        </button>
        <nav>
          <button className={view.name === "setup" ? "active" : ""} onClick={() => setView({ name: "setup" })}>
            New interview
          </button>
          <button className={view.name === "dashboard" ? "active" : ""} onClick={() => setView({ name: "dashboard" })}>
            Dashboard
          </button>
        </nav>
      </header>

      {health && !health.ok && <div className="banner warn" role="status">{health.message}</div>}

      <main>
        {view.name === "setup" && <Setup onStarted={(s) => setView({ name: "interview", id: s.id })} />}
        {view.name === "interview" && (
          <Interview id={view.id} onFinished={(id) => setView({ name: "report", id })} />
        )}
        {view.name === "report" && <Report id={view.id} onBack={() => setView({ name: "dashboard" })} />}
        {view.name === "dashboard" && (
          <Dashboard
            onOpen={(s) => setView({ name: s.status === "completed" ? "report" : "interview", id: s.id })}
            onNew={() => setView({ name: "setup" })}
          />
        )}
      </main>
      <footer>Runs on your computer with Ollama. Your resume is never uploaded anywhere.</footer>
    </div>
  );
}
