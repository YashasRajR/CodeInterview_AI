"""API tests. The LLM is mocked, so Ollama does not need to be running."""
import io
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["DB_PATH"] = os.path.join(tempfile.mkdtemp(), "test.db")

import app as app_module  # noqa: E402
import llm  # noqa: E402


def make_pdf(text):
    """Build a tiny one-page PDF containing `text`."""
    content = f"BT /F1 12 Tf 50 750 Td ({text}) Tj ET".encode()
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
        b"/Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length %d >>\nstream\n" % len(content) + content + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out, offsets = io.BytesIO(), []
    out.write(b"%PDF-1.4\n")
    for i, o in enumerate(objs, 1):
        offsets.append(out.tell())
        out.write(b"%d 0 obj\n" % i + o + b"\nendobj\n")
    xref = out.tell()
    out.write(b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1))
    for off in offsets:
        out.write(b"%010d 00000 n \n" % off)
    out.write(b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF" % (len(objs) + 1, xref))
    return out.getvalue()


RESUME = make_pdf("Yashas Raj R - Python, PyTorch, Flask, React. Built DisenRec music recommender with adversarial training.")


def fake_chat_json(system, user, **_):
    if "grading" in system:
        return {"score": 7.5, "accuracy": 8, "depth": 7, "clarity": 8,
                "strengths": ["Clear"], "improvements": ["Add an example"], "model_answer": "..."}
    return {"skills": ["Python", "PyTorch"], "questions": [
        {"question": "Explain gradient reversal.", "topic": "Deep Learning", "type": "concept"},
        {"question": "How did you evaluate DisenRec?", "topic": "Recommender Systems", "type": "project"},
        {"question": "Design a REST API for uploads.", "topic": "Flask", "type": "problem-solving"},
    ]}


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(llm, "chat_json", fake_chat_json)
    return app_module.app.test_client()


def start(client):
    return client.post("/api/interviews", data={
        "resume": (io.BytesIO(RESUME), "resume.pdf"), "role": "ML Engineer",
        "difficulty": "medium", "count": "3",
    }, content_type="multipart/form-data")


def test_full_interview_flow(client):
    r = start(client)
    assert r.status_code == 201
    s = r.get_json()
    assert len(s["questions"]) == 3 and s["skills"] == ["Python", "PyTorch"]

    q = s["questions"][0]
    r = client.post(f"/api/interviews/{s['id']}/questions/{q['id']}/answer",
                    json={"answer": "It flips the gradient sign during backprop."})
    assert r.status_code == 200 and r.get_json()["score"] == 7.5

    r = client.post(f"/api/interviews/{s['id']}/complete")
    assert r.get_json()["status"] == "completed"
    assert r.get_json()["average_score"] == 7.5

    stats = client.get("/api/stats").get_json()
    assert stats["questions_answered"] >= 1
    assert stats["dimensions"]["accuracy"] == 8.0
    assert any(t["topic"] == "Deep Learning" for t in stats["topics"])


def test_empty_answer_scores_zero(client):
    s = start(client).get_json()
    q = s["questions"][1]
    r = client.post(f"/api/interviews/{s['id']}/questions/{q['id']}/answer", json={"answer": "  "})
    assert r.get_json()["score"] == 0


def test_rejects_non_pdf(client):
    r = client.post("/api/interviews", data={"resume": (io.BytesIO(b"hi"), "cv.txt")},
                    content_type="multipart/form-data")
    assert r.status_code == 400


def test_llm_down_returns_503(monkeypatch):
    def boom(*a, **k):
        raise llm.LLMError("Could not reach Ollama")
    monkeypatch.setattr(llm, "chat_json", boom)
    c = app_module.app.test_client()
    assert start(c).status_code == 503


def test_score_is_clamped(monkeypatch):
    import interview
    monkeypatch.setattr(llm, "chat_json", lambda *a, **k: {"score": 42, "strengths": "Good"})
    fb = interview.evaluate_answer("q", "a", "role", "easy")
    assert fb["score"] == 10 and fb["strengths"] == ["Good"]


def test_extract_json_tolerates_fences():
    assert llm._extract_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert llm._extract_json('Sure! {"a": 2} hope this helps') == {"a": 2}


def fake_chat_json_v2(system, user, **_):
    if "stuck" in system:
        return {"hint": "Think about what happens to the sign of the gradient."}
    if "follow-up" in system:
        return {"question": "How would you choose lambda?", "topic": "Deep Learning"}
    return fake_chat_json(system, user)


@pytest.fixture
def client2(monkeypatch):
    monkeypatch.setattr(llm, "chat_json", fake_chat_json_v2)
    return app_module.app.test_client()


def test_job_description_and_timer_saved(client2, monkeypatch):
    seen = {}
    real = fake_chat_json_v2
    def spy(system, user, **k):
        seen["user"] = user
        return real(system, user, **k)
    monkeypatch.setattr(llm, "chat_json", spy)
    r = client2.post("/api/interviews", data={
        "resume": (io.BytesIO(RESUME), "resume.pdf"), "count": "3",
        "job_description": "We need PyTorch and AWS experience.", "time_limit": "120",
    }, content_type="multipart/form-data")
    s = r.get_json()
    assert "JOB DESCRIPTION" in seen["user"] and s["targeted"] and s["time_limit"] == 120


def test_hint_is_cached(client2):
    s = start(client2).get_json()
    q = s["questions"][0]
    h1 = client2.post(f"/api/interviews/{s['id']}/questions/{q['id']}/hint").get_json()["hint"]
    h2 = client2.post(f"/api/interviews/{s['id']}/questions/{q['id']}/hint").get_json()["hint"]
    assert h1 == h2 and "gradient" in h1


def test_retry_keeps_previous_score_and_time(client2, monkeypatch):
    s = start(client2).get_json()
    q = s["questions"][0]
    url = f"/api/interviews/{s['id']}/questions/{q['id']}/answer"
    client2.post(url, json={"answer": "first", "time_seconds": 40})
    monkeypatch.setattr(llm, "chat_json", lambda *a, **k: {"score": 9, "accuracy": 9, "depth": 9, "clarity": 9})
    r = client2.post(url, json={"answer": "better", "time_seconds": 55}).get_json()
    assert r["previous_score"] == 7.5 and r["score"] == 9 and r["attempts"] == 2
    q2 = client2.get(f"/api/interviews/{s['id']}").get_json()["questions"][0]
    assert q2["previous_score"] == 7.5 and q2["time_seconds"] == 55
    assert client2.get("/api/stats").get_json()["improved_on_retry"] >= 1


def test_followup_inserted_after_parent_once(client2):
    s = start(client2).get_json()
    q = s["questions"][0]
    base = f"/api/interviews/{s['id']}/questions/{q['id']}"
    assert client2.post(base + "/followup").status_code == 400
    client2.post(base + "/answer", json={"answer": "x"})
    r = client2.post(base + "/followup")
    assert r.status_code == 201
    qs = r.get_json()["questions"]
    assert len(qs) == 4 and qs[1]["type"] == "follow-up" and qs[1]["parent_id"] == q["id"]
    assert qs[0]["has_followup"] and [x["position"] for x in qs] == [0, 1, 2, 3]
    assert client2.post(base + "/followup").status_code == 409


def test_migration_adds_columns_to_old_db(tmp_path, monkeypatch):
    import sqlite3, db
    path = tmp_path / "old.db"
    conn = sqlite3.connect(path)
    conn.executescript(db.SCHEMA)
    conn.close()
    monkeypatch.setattr(db, "DB_PATH", str(path))
    db.init()
    cols = {r[1] for r in sqlite3.connect(path).execute("PRAGMA table_info(questions)")}
    assert {"hint", "parent_id", "time_seconds"} <= cols
