# app/core/search.py
import os
from tavily import TavilyClient
from dotenv import load_dotenv

# .env 파일에서 API 키 로드
load_dotenv()

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

# 타빌리 클라이언트 초기화
if not TAVILY_API_KEY:
    print("[ERROR] TAVILY_API_KEY가 .env 파일에 없습니다!")
else:
    tavily = TavilyClient(api_key=TAVILY_API_KEY)

async def search_agent(query: str):
    """
    외부 실시간 지식이 필요할 때 호출하는 검색 함수
    """
    try:
        # 크레딧 절약을 위해 꼭 필요한 설정만!
        # max_results=3: 딱 중요한 거 3개만 가져와
        # search_depth="basic": 기본 검색으로 크레딧 아끼기
        response = tavily.search(
            query=query,
            search_depth="basic",
            max_results=3,
            include_answer=True  # 타빌리가 스스로 요약한 답변 포함
        )
        
        # 타빌리가 똑똑하게 요약해준 답변이 있다면 그것만 반환
        if response.get('answer'):
            return response['answer']
        
        # 요약 답변이 없으면 검색 결과들을 합치기
        context = ""
        for result in response.get('results', []):
            context += f"\n- {result['title']}: {result['content']}\n"
            
        return context if context else "검색 결과가 없습니다."

    except Exception as e:
        print(f"[Search Agent Error] {e}")
        return f"검색 중 오류가 발생했습니다: {str(e)}"