

import os
from llama_index.core import Settings, StorageContext , StorageContext
from llama_index.llms.gemini import Gemini
from llama_index.graph_stores.neo4j import Neo4jPropertyGraphStore
from llama_index.core.query_engine import KnowledgeGraphQueryEngine
from dotenv import load_dotenv

load_dotenv()

# 셋업
Settings.llm = Gemini(model="gemini-2.0-flash", api_key=os.getenv("GEMINI_API_KEY"))
graph_store = Neo4jPropertyGraphStore(
    username=os.getenv("NEO4J_USERNAME", "neo4j"),
    password=os.getenv("NEO4J_PASSWORD"),
    url=os.getenv("NEO4J_URI"),
    database=os.getenv("NEO4J_DATABASE"), 
)


# 3. ★ 핵심: 창고를 상자(StorageContext)에 담기 ★
storage_context = StorageContext.from_defaults(graph_store=graph_store)

query_engine = KnowledgeGraphQueryEngine(
    storage_context=storage_context,  # 👈 graph_store 대신 storage_context를 입력!
    llm=Settings.llm
)
# 스키마 힌트들은 코드 가독성을 위해 생략(상단에 정의되어 있다고 가정)
# ... ( MOODDNA_SCHEMA, COFFEE_SCHEMA 사용) ...

MOODDNA_SCHEMA = """
Neo4j 그래프 스키마 (Mood-DNA 전용):
- 노드: DesignSession (brightness, complexity, saturation, created_at)
- 노드: MoodState (name) ← 예시: "피로", "스트레스", "집중"
- 관계: (DesignSession)-[:REFLECTS_MOOD]->(MoodState)

⚠️ 규칙:
- 반드시 DesignSession 노드만 탐색할 것
- CoffeeSession, 카페인, 건강 데이터는 절대 언급 금지
- 답변은 밝기/복잡도/채도 등 디자인 용어로만 표현
"""

COFFEE_SCHEMA = """
Neo4j 그래프 스키마 (Cof/fee 전용):
- 노드: CoffeeSession (caffeine_mg, drink_type, created_at)
- 노드: BodyReaction (name) ← 예시: "두통", "집중", "불안"
- 관계: (CoffeeSession)-[:CAUSED_REACTION]->(BodyReaction)

⚠️ 규칙:
- 반드시 CoffeeSession 노드만 탐색할 것
- DesignSession, 디자인 데이터는 절대 언급 금지
- 답변은 카페인/신체반응 용어로만 표현
"""

def ask_mooddna(question: str):
    augmented = f"{MOODDNA_SCHEMA}\n질문: {question}"
    return str(query_engine.query(augmented))

def ask_coffee(question: str):
    augmented = f"{COFFEE_SCHEMA}\n질문: {question}"
    return str(query_engine.query(augmented))

def ask_yie(question: str):
    augmented = f"[Rule: 모든 데이터 통합 분석]\n질문: {question}"
    return str(query_engine.query(augmented))