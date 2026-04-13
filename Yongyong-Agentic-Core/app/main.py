# app/main.py
from fastapi import FastAPI, Depends, BackgroundTasks, File, UploadFile, Form
from sqlalchemy.orm import Session
from app.database import get_db, DesignHistory, CoffeeLog
from app.core.search import search_agent
from app.core.auto_ingest import register_auto_ingest
from app.services.design.design_analyzer import calculate_brightness, calculate_complexity
# 함수들
from app.core.query_engine import query_cross_domain_brightness_by_mood
from app.core.mooddna import ask_mooddna
from app.core.coffee_insight import ask_coffee
from app.core.yie import ask_yie
from app.schemas import DesignInput, QuestionRequest
from fastapi.middleware.cors import CORSMiddleware

import json

app = FastAPI(title="Yongyong Agentic Core")

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


#추가 API 엔드포인트
@app.post("/design/analyze")
async def analyze_design(
    data: DesignInput,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    # 1. SQLite에 저장
    record = DesignHistory(**data.dict())
    db.add(record)

    # 2. 이벤트 리스너 등록 (커밋 전에!)
    register_auto_ingest(db, background_tasks)

    # 3. 커밋 → 리스너 발동 → 백그라운드 ingestion 자동 실행
    db.commit()

    return {"status": "ok", "message": "분석 저장 완료, Neo4j ingestion 진행 중"}


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