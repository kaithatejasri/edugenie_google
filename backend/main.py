"""
EduGenie backend -- FastAPI service powering:
  - Intelligent Question Answering
  - AI-Powered Quiz Generation
  - Educational Text Summarization
  - Personalized Learning Path Recommendations
  - User accounts + history

Run with:
    uvicorn main:app --reload --port 8000
"""

import json
from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import os

from models import (
    AskRequest, AskResponse,
    QuizRequest, QuizResponse,
    SummarizeRequest, SummarizeResponse,
    LearningPathRequest, LearningPathResponse,
)
import gemini_service as ai
import auth

app = FastAPI(
    title="EduGenie API",
    description="Lightweight AI-powered educational assistant",
    version="1.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

auth.init_db()


# --- auth helpers ------------------------------------------------------
def get_current_user(authorization: str = Header(None)):
    """Returns user dict if a valid Bearer token is provided, else None (guest)."""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization.removeprefix("Bearer ").strip()
    return auth.get_user_from_token(token)


def save_history(user, feature: str, request_summary: str, response: dict):
    if user:
        auth.add_history(user["id"], feature, request_summary, json.dumps(response))


# --- auth models ---------------------------------------------------------
class AuthRequest(BaseModel):
    username: str
    password: str


@app.post("/api/register")
def register(req: AuthRequest):
    if len(req.username.strip()) < 3 or len(req.password) < 4:
        raise HTTPException(400, "Username must be 3+ chars, password 4+ chars.")
    try:
        user_id = auth.create_user(req.username.strip(), req.password)
    except Exception:
        raise HTTPException(400, "That username is already taken.")
    token = auth.create_session(user_id)
    return {"token": token, "username": req.username.strip()}


@app.post("/api/login")
def login(req: AuthRequest):
    user_id = auth.verify_user(req.username.strip(), req.password)
    if not user_id:
        raise HTTPException(401, "Incorrect username or password.")
    token = auth.create_session(user_id)
    return {"token": token, "username": req.username.strip()}


@app.post("/api/logout")
def logout(authorization: str = Header(None)):
    if authorization and authorization.startswith("Bearer "):
        auth.delete_session(authorization.removeprefix("Bearer ").strip())
    return {"status": "logged out"}


@app.get("/api/me")
def me(user=None, authorization: str = Header(None)):
    current = get_current_user(authorization)
    if not current:
        raise HTTPException(401, "Not logged in.")
    return current


@app.get("/api/history")
def history(authorization: str = Header(None)):
    current = get_current_user(authorization)
    if not current:
        raise HTTPException(401, "Log in to view history.")
    return auth.get_history(current["id"])


# --- health ---------------------------------------------------------------
@app.get("/api/health")
def health():
    return {"status": "ok", "demo_mode": ai.is_demo_mode()}


# --- feature routes ---------------------------------------------------------
@app.post("/api/ask", response_model=AskResponse)
def ask_question(req: AskRequest, authorization: str = Header(None)):
    user = get_current_user(authorization)
    demo_fallback = {
        "answer": (
            "The Pacific Ocean is the largest and deepest ocean on Earth, covering "
            "about 63 million square miles -- more than all of Earth's land area combined."
        ),
        "context": (
            "It stretches from the Arctic in the north to the Southern Ocean near "
            "Antarctica, and separates Asia and Australia from the Americas."
        ),
        "related_topics": ["Atlantic Ocean", "Ocean currents", "Marine ecosystems", "Plate tectonics"],
    }
    result = ai.generate_json(
        system_prompt=(
            "You are EduGenie, a friendly and accurate educational tutor. "
            "Answer the student's question clearly, then give brief extra context "
            "that helps them understand the bigger picture, then list 3-4 related topics "
            "they might want to explore next."
        ),
        user_prompt=(
            f"Question: {req.question}\n"
            f"Subject hint: {req.subject or 'general'}\n\n"
            'Return JSON: {"answer": str, "context": str, "related_topics": [str, ...]}'
        ),
        demo_fallback=demo_fallback,
    )
    clean = {k: v for k, v in result.items() if k in AskResponse.model_fields}
    save_history(user, "ask", req.question, clean)
    return AskResponse(**clean)


@app.post("/api/quiz", response_model=QuizResponse)
def generate_quiz(req: QuizRequest, authorization: str = Header(None)):
    user = get_current_user(authorization)
    demo_fallback = {
        "topic": req.topic,
        "difficulty": req.difficulty,
        "questions": [
            {
                "question": "In a right triangle, if the two legs are 3 and 4, what is the hypotenuse?",
                "options": ["5", "6", "7", "8"],
                "correct_answer": "5",
                "explanation": "By the Pythagoras theorem, c = sqrt(3^2 + 4^2) = sqrt(25) = 5.",
            },
        ][: req.num_questions] or [],
    }
    result = ai.generate_json(
        system_prompt=(
            "You are EduGenie, an assistant that writes self-assessment quizzes for students. "
            "Write clear, unambiguous multiple-choice questions with exactly 4 options each, "
            "one correct answer, and a short explanation of why it's correct."
        ),
        user_prompt=(
            f"Topic: {req.topic}\n"
            f"Difficulty: {req.difficulty}\n"
            f"Number of questions: {req.num_questions}\n\n"
            'Return JSON: {"topic": str, "difficulty": str, "questions": '
            '[{"question": str, "options": [str x4], "correct_answer": str, "explanation": str}, ...]}'
        ),
        demo_fallback=demo_fallback,
    )
    clean = {k: v for k, v in result.items() if k in QuizResponse.model_fields}
    save_history(user, "quiz", req.topic, clean)
    return QuizResponse(**clean)


@app.post("/api/summarize", response_model=SummarizeResponse)
def summarize_text(req: SummarizeRequest, authorization: str = Header(None)):
    user = get_current_user(authorization)
    word_count = len(req.text.split())
    demo_fallback = {
        "summary": (
            "This passage explains a core concept in clear terms, covering its definition, "
            "why it matters, and how it connects to related ideas in the subject."
        ),
        "key_points": ["Defines the main concept", "Explains its significance", "Connects it to related topics"],
        "word_count_original": word_count,
        "word_count_summary": 24,
    }
    result = ai.generate_json(
        system_prompt=(
            "You are EduGenie, an assistant that summarizes educational material for students. "
            "Produce a summary at the requested length and extract the key points as a bullet list."
        ),
        user_prompt=(
            f"Length preference: {req.length} (short=~40 words, medium=~100 words, long=~200 words)\n\n"
            f"Text to summarize:\n{req.text}\n\n"
            'Return JSON: {"summary": str, "key_points": [str, ...], '
            f'"word_count_original": {word_count}, "word_count_summary": int}}'
        ),
        demo_fallback=demo_fallback,
    )
    result["word_count_original"] = word_count
    clean = {k: v for k, v in result.items() if k in SummarizeResponse.model_fields}
    save_history(user, "summarize", req.text[:80], clean)
    return SummarizeResponse(**clean)


@app.post("/api/learning-path", response_model=LearningPathResponse)
def learning_path(req: LearningPathRequest, authorization: str = Header(None)):
    user = get_current_user(authorization)
    demo_fallback = {
        "topic": req.topic,
        "stages": [
            {
                "stage": "beginner",
                "title": f"{req.topic} Fundamentals",
                "duration_estimate": "2 weeks",
                "topics": ["Core syntax and concepts", "Basic queries and operations", "Common terminology"],
                "resources": ["Official documentation", "Interactive beginner tutorial"],
            },
            {
                "stage": "intermediate",
                "title": f"Applying {req.topic}",
                "duration_estimate": "3 weeks",
                "topics": ["Joins and relationships", "Aggregation and filtering", "Indexing basics"],
                "resources": ["Hands-on practice platform", "Case-study exercises"],
            },
            {
                "stage": "advanced",
                "title": f"Mastering {req.topic}",
                "duration_estimate": "4 weeks",
                "topics": ["Performance optimization", "Advanced query patterns", "Real-world project"],
                "resources": ["Open-source project contribution", "Advanced certification course"],
            },
        ],
    }
    result = ai.generate_json(
        system_prompt=(
            "You are EduGenie, an assistant that builds personalized learning roadmaps. "
            "Design a progression of stages (beginner, intermediate, advanced) starting from "
            "the learner's current level, each with topics to cover, resource suggestions, "
            "and a rough duration estimate."
        ),
        user_prompt=(
            f"Topic: {req.topic}\n"
            f"Current level: {req.current_level}\n"
            f"Goal: {req.goal or 'general proficiency'}\n\n"
            'Return JSON: {"topic": str, "stages": [{"stage": str, "title": str, '
            '"duration_estimate": str, "topics": [str, ...], "resources": [str, ...]}, ...]}'
        ),
        demo_fallback=demo_fallback,
    )
    clean = {k: v for k, v in result.items() if k in LearningPathResponse.model_fields}
    save_history(user, "learning-path", req.topic, clean)
    return LearningPathResponse(**clean)


# --- serve the frontend -----------------------------------------------------
_FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")

if os.path.isdir(_FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=_FRONTEND_DIR), name="static")

    @app.get("/")
    def serve_frontend():
        return FileResponse(os.path.join(_FRONTEND_DIR, "index.html"))