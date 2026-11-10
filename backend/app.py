"""CodeInterview AI - Flask API.

Run:  python app.py   (serves on http://localhost:5000)
"""
import json
import os

from flask import Flask, jsonify, request
from flask_cors import CORS

import db
import interview
import llm

ROLES_DEFAULT = "Software Engineer"
DIFFICULTIES = {"easy", "medium", "hard"}
TIME_LIMITS = {0, 60, 120, 180, 300}
MAX_UPLOAD_MB = 5

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_MB * 1024 * 1024
CORS(app)
db.init()


def error(message, status=400):
    return jsonify({"error": message}), status


@app.errorhandler(llm.LLMError)
def handle_llm_error(e):
    return error(str(e), 503)


@app.errorhandler(413)
def too_large(_):
    return error(f"File is too large (max {MAX_UPLOAD_MB} MB).", 413)


@app.get("/api/health")
def health():
    ok, message = llm.health()
    return jsonify({"ok": ok, "message": message, "model": llm.OLLAMA_MODEL})


@app.post("/api/interviews")
def start_interview():
    file = request.files.get("resume")
    if not file or not file.filename.lower().endswith(".pdf"):
        return error("Please upload your resume as a PDF.")
    role = (request.form.get("role") or ROLES_DEFAULT).strip()[:80]
    difficulty = (request.form.get("difficulty") or "medium").lower()
    if difficulty not in DIFFICULTIES:
        difficulty = "medium"
    try:
        count = max(3, min(10, int(request.form.get("count", 5))))
    except ValueError:
        count = 5
    job_description = (request.form.get("job_description") or "").strip()[:interview.MAX_JD_CHARS]
    try:
        time_limit = int(request.form.get("time_limit", 0))
    except ValueError:
        time_limit = 0
    if time_limit not in TIME_LIMITS:
        time_limit = 0
    try:
        text = interview.extract_resume_text(file.read())
    except ValueError as e:
        return error(str(e))
    except Exception:
        return error("Could not read this PDF.")
    skills, questions = interview.generate_questions(text, role, difficulty, count, job_description)
    return jsonify(db.create_session(role, difficulty, skills, questions, job_description, time_limit)), 201


@app.get("/api/interviews")
def list_interviews():
    return jsonify(db.list_sessions())


@app.get("/api/interviews/<int:sid>")
def get_interview(sid):
    session = db.get_session(sid)
    return jsonify(session) if session else error("Interview not found.", 404)


@app.delete("/api/interviews/<int:sid>")
def delete_interview(sid):
    db.delete_session(sid)
    return "", 204


@app.post("/api/interviews/<int:sid>/questions/<int:qid>/answer")
def answer_question(sid, qid):
    session = db.get_session(sid)
    if not session:
        return error("Interview not found.", 404)
    row = db.get_question(sid, qid)
    if not row:
        return error("Question not found.", 404)
    body = request.get_json(silent=True) or {}
    answer = str(body.get("answer", ""))[:5000]
    try:
        seconds = max(0, min(3600, int(body.get("time_seconds")))) if body.get("time_seconds") is not None else None
    except (TypeError, ValueError):
        seconds = None
    feedback = interview.evaluate_answer(row["question"], answer, session["role"], session["difficulty"])
    db.save_answer(qid, answer, feedback, seconds)
    return jsonify({
        "question_id": qid, "answer": answer, "feedback": feedback, "score": feedback["score"],
        "previous_score": row["score"], "attempts": row["attempts"] + 1,
    })


@app.post("/api/interviews/<int:sid>/questions/<int:qid>/hint")
def hint(sid, qid):
    session = db.get_session(sid)
    row = db.get_question(sid, qid) if session else None
    if not row:
        return error("Question not found.", 404)
    if row["hint"]:
        return jsonify({"hint": row["hint"]})
    text = interview.generate_hint(row["question"], session["role"])
    db.save_hint(qid, text)
    return jsonify({"hint": text})


@app.post("/api/interviews/<int:sid>/questions/<int:qid>/followup")
def followup(sid, qid):
    session = db.get_session(sid)
    row = db.get_question(sid, qid) if session else None
    if not row:
        return error("Question not found.", 404)
    if row["score"] is None:
        return error("Answer this question before asking for a follow-up.")
    if row["parent_id"] is not None or db.has_followup(qid):
        return error("This question already has a follow-up.", 409)
    improvements = json.loads(row["feedback"]).get("improvements", []) if row["feedback"] else []
    q = interview.generate_followup(row["question"], row["answer"], improvements, session["role"], session["difficulty"])
    return jsonify(db.insert_followup(sid, row, q)), 201


@app.post("/api/interviews/<int:sid>/complete")
def complete_interview(sid):
    if not db.get_session(sid):
        return error("Interview not found.", 404)
    return jsonify(db.complete_session(sid))


@app.get("/api/stats")
def get_stats():
    return jsonify(db.stats())


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.getenv("PORT", "5000")), debug=os.getenv("FLASK_DEBUG") == "1")
