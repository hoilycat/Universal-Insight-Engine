from pydantic import BaseModel
from typing import Optional, Literal

# ── 기존 스키마 (하위 호환 유지) ──────────────────────────────────────
class DesignInput(BaseModel):
    brightness: float
    complexity: float
    description: str

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
    insight_en: Optional[str] = None
    insight_ko: Optional[str] = None
    tags: list[str]
    score: int

class KnowledgeSearchResponse(BaseModel):
    query: str
    results: list[KnowledgeChunk]

# ── /rag/* 공통 스키마 ────────────────────────────────────────────────
class RagRequest(BaseModel):
    domain: Literal["coffee", "design", "travel", "integrated"]
    task: str
    question: str
    context: Optional[dict] = None   # 앱별 추가 컨텍스트 (logs, metrics 등)

class EvidenceItem(BaseModel):
    document: str
    chunk_id: str
    tags: list[str]
    insight_ko: Optional[str] = None
    score: int

class RagSections(BaseModel):
    summary: Optional[str] = None
    evidence: Optional[str] = None
    recommendation: Optional[str] = None
    warning: Optional[str] = None

class RagResponse(BaseModel):
    domain: str
    task: str
    answer: str
    sections: RagSections
    evidence: list[EvidenceItem]
    cross_domain_used: bool = False  # UI에서는 숨기고 내부 플래그로만 사용

class EvidenceOnlyResponse(BaseModel):
    domain: str
    question: str
    results: list[EvidenceItem]

class EvidenceDebugInfo(BaseModel):
    intent: str
    boost_terms: list[str]
    penalty_terms: list[str]
    total_raw: int
    total_after_dedup: int
    total_after_min_score: int
    total_curated: int
    score_min: float
    score_max: float
    score_avg: float
    per_document_counts: dict

class EvidenceDetailResponse(BaseModel):
    domain: str
    question: str
    raw_results: list[EvidenceItem]
    curated_results: list[EvidenceItem]
    debug: EvidenceDebugInfo
