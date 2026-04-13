# app/main.py
from fastapi import FastAPI
from app.core.search import search_agent
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Yongyong Agentic Core")

# CORS 설정 (프론트엔드 연결 대비)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

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