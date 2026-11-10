"""SQLite storage for interview sessions, questions and answers."""
import json
import os
import sqlite3
from datetime import datetime, timezone

DB_PATH = os.getenv("DB_PATH", os.path.join(os.path.dirname(__file__), "codeinterview.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    role TEXT NOT NULL,
    difficulty TEXT NOT NULL,
    skills TEXT NOT NULL DEFAULT '[]',
    status TEXT NOT NULL DEFAULT 'in_progress'
);
CREATE TABLE IF NOT EXISTS questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    position INTEGER NOT NULL,
    question TEXT NOT NULL,
    topic TEXT NOT NULL,
    type TEXT NOT NULL,
    answer TEXT,
    feedback TEXT,
    score REAL
);
"""

# Columns added after the first version. init() adds any that are missing,
# so an existing database keeps working after an update.
MIGRATIONS = {
    "sessions": {
        "job_description": "TEXT NOT NULL DEFAULT ''",
        "time_limit": "INTEGER NOT NULL DEFAULT 0",
    },
    "questions": {
        "time_seconds": "INTEGER",
        "attempts": "INTEGER NOT NULL DEFAULT 0",
        "previous_score": "REAL",
        "hint": "TEXT",
        "parent_id": "INTEGER",
    },
}


def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init():
    with connect() as conn:
        conn.executescript(SCHEMA)
        for table, cols in MIGRATIONS.items():
            existing = {r["name"] for r in conn.execute(f"PRAGMA table_info({table})")}
            for name, ddl in cols.items():
                if name not in existing:
                    conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}")


def create_session(role, difficulty, skills, questions, job_description="", time_limit=0):
    with connect() as conn:
        cur = conn.execute(
            "INSERT INTO sessions (created_at, role, difficulty, skills, job_description, time_limit) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (datetime.now(timezone.utc).isoformat(), role, difficulty, json.dumps(skills),
             job_description, time_limit),
        )
        sid = cur.lastrowid
        conn.executemany(
            "INSERT INTO questions (session_id, position, question, topic, type) VALUES (?, ?, ?, ?, ?)",
            [(sid, i, q["question"], q["topic"], q["type"]) for i, q in enumerate(questions)],
        )
    return get_session(sid)


def _question_row(r):
    return {
        "id": r["id"], "position": r["position"], "question": r["question"],
        "topic": r["topic"], "type": r["type"], "answer": r["answer"],
        "score": r["score"], "previous_score": r["previous_score"],
        "attempts": r["attempts"], "time_seconds": r["time_seconds"],
        "hint": r["hint"], "parent_id": r["parent_id"],
        "feedback": json.loads(r["feedback"]) if r["feedback"] else None,
    }


def get_session(sid):
    with connect() as conn:
        s = conn.execute("SELECT * FROM sessions WHERE id = ?", (sid,)).fetchone()
        if not s:
            return None
        qs = conn.execute(
            "SELECT * FROM questions WHERE session_id = ? ORDER BY position", (sid,)
        ).fetchall()
    questions = [_question_row(q) for q in qs]
    for q in questions:
        q["has_followup"] = any(x["parent_id"] == q["id"] for x in questions)
    scored = [q["score"] for q in questions if q["score"] is not None]
    times = [q["time_seconds"] for q in questions if q["time_seconds"]]
    return {
        "id": s["id"], "created_at": s["created_at"], "role": s["role"],
        "difficulty": s["difficulty"], "skills": json.loads(s["skills"]),
        "status": s["status"], "time_limit": s["time_limit"],
        "targeted": bool(s["job_description"]), "questions": questions,
        "average_score": round(sum(scored) / len(scored), 1) if scored else None,
        "average_time": round(sum(times) / len(times)) if times else None,
    }


def get_question(sid, qid):
    with connect() as conn:
        return conn.execute(
            "SELECT * FROM questions WHERE id = ? AND session_id = ?", (qid, sid)
        ).fetchone()


def save_answer(qid, answer, feedback, time_seconds=None):
    """Store an answer. On a retry, the previous score is kept for comparison."""
    with connect() as conn:
        conn.execute(
            """UPDATE questions SET previous_score = score, answer = ?, feedback = ?, score = ?,
                      time_seconds = ?, attempts = attempts + 1 WHERE id = ?""",
            (answer, json.dumps(feedback), feedback["score"], time_seconds, qid),
        )


def save_hint(qid, hint):
    with connect() as conn:
        conn.execute("UPDATE questions SET hint = ? WHERE id = ?", (hint, qid))


def has_followup(qid):
    with connect() as conn:
        return conn.execute("SELECT 1 FROM questions WHERE parent_id = ?", (qid,)).fetchone() is not None


def insert_followup(sid, parent, q):
    """Insert a follow-up question directly after its parent question."""
    with connect() as conn:
        conn.execute(
            "UPDATE questions SET position = position + 1 WHERE session_id = ? AND position > ?",
            (sid, parent["position"]),
        )
        conn.execute(
            "INSERT INTO questions (session_id, position, question, topic, type, parent_id) VALUES (?, ?, ?, ?, ?, ?)",
            (sid, parent["position"] + 1, q["question"], q["topic"], q["type"], parent["id"]),
        )
        conn.execute("UPDATE sessions SET status = 'in_progress' WHERE id = ?", (sid,))
    return get_session(sid)


def complete_session(sid):
    with connect() as conn:
        conn.execute("UPDATE sessions SET status = 'completed' WHERE id = ?", (sid,))
    return get_session(sid)


def delete_session(sid):
    with connect() as conn:
        conn.execute("DELETE FROM sessions WHERE id = ?", (sid,))


def list_sessions():
    with connect() as conn:
        rows = conn.execute(
            """SELECT s.*, AVG(q.score) AS avg_score,
                      COUNT(q.id) AS total, COUNT(q.score) AS answered
               FROM sessions s LEFT JOIN questions q ON q.session_id = s.id
               GROUP BY s.id ORDER BY s.id DESC"""
        ).fetchall()
    return [{
        "id": r["id"], "created_at": r["created_at"], "role": r["role"],
        "difficulty": r["difficulty"], "status": r["status"],
        "targeted": bool(r["job_description"]),
        "average_score": round(r["avg_score"], 1) if r["avg_score"] is not None else None,
        "answered": r["answered"], "total": r["total"],
    } for r in rows]


def stats():
    with connect() as conn:
        topics = conn.execute(
            """SELECT topic, AVG(score) AS avg, COUNT(*) AS n FROM questions
               WHERE score IS NOT NULL GROUP BY topic ORDER BY n DESC LIMIT 12"""
        ).fetchall()
        types = conn.execute(
            """SELECT type, AVG(score) AS avg, COUNT(*) AS n FROM questions
               WHERE score IS NOT NULL GROUP BY type"""
        ).fetchall()
        dims = conn.execute(
            "SELECT feedback FROM questions WHERE feedback IS NOT NULL"
        ).fetchall()
        improved = conn.execute(
            """SELECT COUNT(*) AS n FROM questions
               WHERE previous_score IS NOT NULL AND score > previous_score"""
        ).fetchone()["n"]
        avg_time = conn.execute(
            "SELECT AVG(time_seconds) AS t FROM questions WHERE time_seconds IS NOT NULL"
        ).fetchone()["t"]
    sums = {"accuracy": 0.0, "depth": 0.0, "clarity": 0.0}
    for row in dims:
        fb = json.loads(row["feedback"])
        for k in sums:
            sums[k] += float(fb.get(k, 0))
    n = len(dims)
    all_sessions = list_sessions()
    sessions = [s for s in reversed(all_sessions) if s["average_score"] is not None]
    return {
        "total_sessions": len(all_sessions),
        "questions_answered": n,
        "improved_on_retry": improved,
        "average_time": round(avg_time) if avg_time else None,
        "overall_average": round(sum(s["average_score"] for s in sessions) / len(sessions), 1) if sessions else None,
        "dimensions": {k: round(v / n, 1) for k, v in sums.items()} if n else None,
        "progress": [{"session": s["id"], "date": s["created_at"][:10], "score": s["average_score"]} for s in sessions],
        "topics": [{"topic": t["topic"], "score": round(t["avg"], 1), "count": t["n"]} for t in topics],
        "types": [{"type": t["type"], "score": round(t["avg"], 1), "count": t["n"]} for t in types],
    }
