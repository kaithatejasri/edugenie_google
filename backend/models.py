"""Request and response schemas shared across EduGenie API routes."""

from typing import List, Optional
from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, description="The student's question")
    subject: Optional[str] = Field(None, description="Optional subject hint, e.g. 'Geography'")


class AskResponse(BaseModel):
    answer: str
    context: str
    related_topics: List[str]


class QuizRequest(BaseModel):
    topic: str = Field(..., min_length=1)
    difficulty: str = Field("medium", pattern="^(easy|medium|hard)$")
    num_questions: int = Field(5, ge=1, le=15)


class QuizQuestion(BaseModel):
    question: str
    options: List[str]
    correct_answer: str
    explanation: str


class QuizResponse(BaseModel):
    topic: str
    difficulty: str
    questions: List[QuizQuestion]


class SummarizeRequest(BaseModel):
    text: str = Field(..., min_length=20)
    length: str = Field("medium", pattern="^(short|medium|long)$")


class SummarizeResponse(BaseModel):
    summary: str
    key_points: List[str]
    word_count_original: int
    word_count_summary: int


class LearningPathRequest(BaseModel):
    topic: str = Field(..., min_length=1)
    current_level: str = Field("beginner", pattern="^(beginner|intermediate|advanced)$")
    goal: Optional[str] = Field(None, description="Optional learning goal, e.g. 'pass an interview'")


class LearningStage(BaseModel):
    stage: str
    title: str
    duration_estimate: str
    topics: List[str]
    resources: List[str]


class LearningPathResponse(BaseModel):
    topic: str
    stages: List[LearningStage]
