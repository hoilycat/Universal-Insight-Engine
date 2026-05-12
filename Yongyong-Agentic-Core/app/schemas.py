from pydantic import BaseModel
from typing import Optional

class DesignInput(BaseModel):
    brightness: float
    complexity: float
    description: str  # AI 비평 결과 JSON 문자열

class QuestionRequest(BaseModel):
    question: str

class CoffeeInput(BaseModel):
    caffeine_mg: int
    drink_type: str
    body_reaction: str

class KnowledgeChunk(BaseModel):
    id: str
    document: str
    text: str
    insight_en: Optional[str]
    insight_ko: Optional[str]
    tags: list[str]
    score: int

class KnowledgeSearchResponse(BaseModel):
    query: str
    results: list[KnowledgeChunk]