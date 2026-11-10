"""Interview logic: resume parsing, question generation and answer evaluation."""
import io
import re

from pypdf import PdfReader

import llm

MAX_RESUME_CHARS = 6000
MAX_JD_CHARS = 3000


def extract_resume_text(file_bytes):
    reader = PdfReader(io.BytesIO(file_bytes))
    text = "\n".join((page.extract_text() or "") for page in reader.pages)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if len(text) < 50:
        raise ValueError("Could not read text from this PDF. Is it a scanned image?")
    return text[:MAX_RESUME_CHARS]


QUESTION_SYSTEM = """You are a senior technical interviewer.
Read the candidate's resume and write technical interview questions that are
specific to the projects, skills and experience it mentions.
If a job description is given, focus on the skills that job needs and
connect them to what the candidate has actually done.
Mix question types: concepts, project deep-dives, problem solving and trade-offs.
Return ONLY JSON in this exact shape:
{"skills": ["skill", ...],
 "questions": [{"question": "...", "topic": "short topic name", "type": "concept|project|problem-solving|behavioral"}]}"""


def generate_questions(resume_text, role, difficulty, count, job_description=""):
    user = (
        f"Target role: {role}\nDifficulty: {difficulty}\n"
        f"Number of questions: {count}\n\nRESUME:\n{resume_text}"
    )
    if job_description.strip():
        user += f"\n\nJOB DESCRIPTION:\n{job_description.strip()[:MAX_JD_CHARS]}"
    data = llm.chat_json(QUESTION_SYSTEM, user, temperature=0.7)
    questions = []
    for q in data.get("questions", []):
        if isinstance(q, str):
            q = {"question": q}
        text = str(q.get("question", "")).strip()
        if text:
            questions.append({
                "question": text,
                "topic": str(q.get("topic") or "General").strip()[:60],
                "type": str(q.get("type") or "concept").strip()[:30],
            })
    if not questions:
        raise llm.LLMError("The model did not return any questions. Try again.")
    skills = [str(s).strip() for s in data.get("skills", []) if str(s).strip()][:20]
    return skills, questions[:count]


EVAL_SYSTEM = """You are a fair but strict technical interviewer grading one answer.
Score from 0 to 10 for: technical accuracy, depth, and clarity.
Be specific and constructive. If the answer is empty or off-topic, score low.
Return ONLY JSON in this exact shape:
{"score": 0-10, "accuracy": 0-10, "depth": 0-10, "clarity": 0-10,
 "strengths": ["..."], "improvements": ["..."], "model_answer": "a concise strong answer"}"""


def _clamp(value):
    try:
        return max(0.0, min(10.0, float(value)))
    except (TypeError, ValueError):
        return 0.0


def _as_list(value):
    if isinstance(value, str):
        return [value] if value.strip() else []
    return [str(v) for v in (value or []) if str(v).strip()]


def evaluate_answer(question, answer, role, difficulty):
    if not answer.strip():
        return {
            "score": 0, "accuracy": 0, "depth": 0, "clarity": 0,
            "strengths": [], "improvements": ["No answer was given."],
            "model_answer": "",
        }
    user = (
        f"Role: {role}\nDifficulty: {difficulty}\n"
        f"QUESTION: {question}\n\nCANDIDATE ANSWER: {answer}"
    )
    data = llm.chat_json(EVAL_SYSTEM, user, temperature=0.2)
    return {
        "score": round(_clamp(data.get("score")), 1),
        "accuracy": round(_clamp(data.get("accuracy")), 1),
        "depth": round(_clamp(data.get("depth")), 1),
        "clarity": round(_clamp(data.get("clarity")), 1),
        "strengths": _as_list(data.get("strengths"))[:5],
        "improvements": _as_list(data.get("improvements"))[:5],
        "model_answer": str(data.get("model_answer") or "").strip(),
    }


HINT_SYSTEM = """You are a supportive technical interviewer.
The candidate is stuck on a question. Give ONE short hint (one or two sentences)
that points them in the right direction WITHOUT giving the answer away.
Return ONLY JSON: {"hint": "..."}"""


def generate_hint(question, role):
    data = llm.chat_json(HINT_SYSTEM, f"Role: {role}\nQUESTION: {question}", temperature=0.5)
    hint = str(data.get("hint") or "").strip()
    if not hint:
        raise llm.LLMError("The model did not return a hint. Try again.")
    return hint


FOLLOWUP_SYSTEM = """You are a technical interviewer. Based on the candidate's answer,
ask ONE natural follow-up question that digs into the weakest or most interesting
part of what they said, the way a real interviewer would.
Return ONLY JSON: {"question": "...", "topic": "short topic name"}"""


def generate_followup(question, answer, improvements, role, difficulty):
    user = (
        f"Role: {role}\nDifficulty: {difficulty}\n"
        f"ORIGINAL QUESTION: {question}\nCANDIDATE ANSWER: {answer or '(skipped)'}\n"
        f"WEAK POINTS: {'; '.join(improvements) or 'none noted'}"
    )
    data = llm.chat_json(FOLLOWUP_SYSTEM, user, temperature=0.6)
    text = str(data.get("question") or "").strip()
    if not text:
        raise llm.LLMError("The model did not return a follow-up question. Try again.")
    return {"question": text, "topic": str(data.get("topic") or "Follow-up").strip()[:60], "type": "follow-up"}
