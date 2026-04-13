# app/core/nl_query_engine.py
# (클로드의 SCHEMA_HINT 로직을 통합함)

import os
from llama_index.core import Settings, StorageContext , StorageContext
from llama_index.llms.gemini import Gemini
from llama_index.graph_stores.neo4j import Neo4jPropertyGraphStore
from llama_index.core.query_engine import KnowledgeGraphQueryEngine

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

def ask_mooddna(question: str):
    augmented = f"[Rule: 디자인 데이터만 사용]\n{question}"
    return str(query_engine.query(augmented))

def ask_coffee(question: str):
    augmented = f"[Rule: 건강 데이터만 사용]\n{question}"
    return str(query_engine.query(augmented))

def ask_yie(question: str):
    augmented = f"[Rule: 모든 데이터 통합 분석]\n{question}"
    return str(query_engine.query(augmented))