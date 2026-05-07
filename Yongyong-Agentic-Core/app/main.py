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
# app/main.py 수정본
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

