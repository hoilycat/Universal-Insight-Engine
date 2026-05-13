# app/main.py
from fastapi import FastAPI, Depends, BackgroundTasks, File, UploadFile, Form
from sqlalchemy.orm import Session
from app.database import get_db, DesignHistory, CoffeeLog
from app.core.search import search_agent
from app.core.auto_ingest import register_auto_ingest
from app.services.design.design_analyzer import calculate_brightness, calculate_complexity

# 기존 함수들 (하위 호환 유지)
from app.core.mooddna import ask_mooddna
from app.core.coffee_insight import ask_coffee
from app.core.yie import ask_yie
from app.core.neo4j_kb import search_knowledge_base

# 공통 GraphRAG 엔진
from app.core import rag_engine
from app.core.response_formatter import normalize_evidence

from app.schemas import (
    DesignInput, QuestionRequest, KnowledgeSearchResponse,
    RagRequest, RagResponse, RagSections, EvidenceItem, EvidenceOnlyResponse,
    EvidenceDetailResponse, EvidenceDebugInfo,
)
from fastapi.middleware.cors import CORSMiddleware

import json

app = FastAPI(
    title="Yongyong Agentic Core — Universal Insight Engine",
    description="공통 GraphRAG 엔진. Mood-DNA, Cof/fee, Packy가 공유하는 Agentic Brain.",
    version="2.0.0",
)

# CORS 설정 (프론트엔드 연결 대비)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 기본 루트
@app.get("/")
def read_root():
    return {"message": "Welcome to Yongyong Agentic Core!"}

@app.get("/test-search")
async def test_search(q: str):
    """
    타빌리 검색 테스트: 브라우저에서 ?q=검색어 로 확인 가능
    """
    result = await search_agent(q)
    return {
        "query": q,
        "search_result": result
    }


# 추가 API 엔드포인트
@app.post("/design/analyze")
async def analyze_design(
    file: UploadFile = File(...), # 실제 이미지 파일 받기
    brand_context: str = Form(...), # JSON 형태의 브랜드 설명
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db)
):
    # 1. 이미지 읽기 및 OpenCV 분석
    image_bytes = await file.read()
    brightness = calculate_brightness(image_bytes)
    complexity = calculate_complexity(image_bytes)
    # TODO: 필요한 다른 지표들(OCR 등)도 여기서 호출 가능

    # 2. AI 컨설턴트 호출 (에이전틱 비평 생성)
    # 현재 코드의 design_consultant.py에 있는 consult_design 호출
    # (매개변수가 많으니 필요한 것 위주로 전달하게 수정 필요)
    
    # 3. SQLite 저장 (기록용)
    record = DesignHistory(
        brightness=brightness,
        complexity=complexity,
        description=brand_context # 비평 결과 JSON을 담는 것이 좋음
    )
    db.add(record)
    
    # 4. Neo4j 자동 주입 (클로드가 짜준 자동화 로직!)
    register_auto_ingest(db, background_tasks)
    
    db.commit()
    db.refresh(record)

    return {
        "id": record.id, 
        "metrics": {"brightness": brightness, "complexity": complexity},
        "status": "Neo4j Syncing..."
    }


@app.post("/mooddna/ask")   # 디자인 챗봇
async def ask_mooddna_endpoint(req: QuestionRequest):
    return {"answer": ask_mooddna(req.question)}

@app.post("/coffee/ask")    # 건강 챗봇
async def ask_coffee_endpoint(req: QuestionRequest):
    return {"answer": ask_coffee(req.question)}

# 통합 인사이트는 내부 분석용으로만 (UI 노출 X)
@app.post("/insight/ask")   
async def ask_insight_endpoint(req: QuestionRequest):
    return {"answer": ask_yie(req.question)}

@app.get("/knowledge/search", response_model=KnowledgeSearchResponse)
async def search_knowledge_endpoint(q: str, limit: int = 8):
    return {
        "query": q,
        "results": search_knowledge_base(q, limit=min(max(limit, 1), 20)),
    }


# ═══════════════════════════════════════════════════════════════════════
# /rag/* — 공통 GraphRAG 엔드포인트 (v2)
# ═══════════════════════════════════════════════════════════════════════

@app.post("/rag/query", response_model=RagResponse)
async def rag_query(req: RagRequest):
    """
    공통 GraphRAG 질의 엔드포인트.
    domain: coffee | design | travel | integrated
    """
    raw = rag_engine.query(
        domain=req.domain,
        task=req.task,
        question=req.question,
        context=req.context,
    )
    # sections dict → RagSections 변환
    raw["sections"] = RagSections(**raw["sections"])
    # evidence list → EvidenceItem 변환
    raw["evidence"] = [EvidenceItem(**e) for e in raw["evidence"]]
    return RagResponse(**raw)


@app.post("/rag/evidence", response_model=EvidenceDetailResponse)
async def rag_evidence(req: RagRequest):
    """
    raw_results (30개) + curated_results (5-6개) + debug 반환.
    LLM 호출 없음. 프론트 카드 / 디버깅용.
    """
    raw, curated, debug = rag_engine.search_only(
        domain=req.domain,
        question=req.question,
        task=req.task if req.task else None,
    )
    return EvidenceDetailResponse(
        domain=req.domain,
        question=req.question,
        raw_results=[EvidenceItem(**e) for e in normalize_evidence(raw)],
        curated_results=[EvidenceItem(**e) for e in normalize_evidence(curated)],
        debug=EvidenceDebugInfo(
            intent=debug.intent,
            boost_terms=debug.boost_terms,
            penalty_terms=debug.penalty_terms,
            total_raw=debug.total_raw,
            total_after_dedup=debug.total_after_dedup,
            total_after_min_score=debug.total_after_min_score,
            total_curated=debug.total_curated,
            score_min=debug.score_min,
            score_max=debug.score_max,
            score_avg=debug.score_avg,
            per_document_counts=debug.per_document_counts,
        ),
    )


@app.post("/rag/report", response_model=RagResponse)
async def rag_report(req: RagRequest):
    """
    상세 리포트용: 그래프 확장을 2-hop으로 허용하지 않고
    base chunk 수를 10개로 늘려 더 풍부한 컨텍스트 사용.
    (내부 리서치/디버깅용)
    """
    raw = rag_engine.query(
        domain=req.domain,
        task=req.task,
        question=req.question,
        context=req.context,
        expand_graph=True,
    )
    raw["sections"] = RagSections(**raw["sections"])
    raw["evidence"] = [EvidenceItem(**e) for e in raw["evidence"]]
    return RagResponse(**raw)
