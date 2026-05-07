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