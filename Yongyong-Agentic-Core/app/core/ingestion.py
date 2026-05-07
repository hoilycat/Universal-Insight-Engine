import os
import json
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from llama_index.graph_stores.neo4j import Neo4jPropertyGraphStore
from llama_index.core.graph_stores.types import EntityNode, Relation

load_dotenv()

# 클라우드 Neo4j 연결
graph_store = Neo4jPropertyGraphStore(
    username=os.getenv("NEO4J_USERNAME", "neo4j"),
    password=os.getenv("NEO4J_PASSWORD"),
    url=os.getenv("NEO4J_URI"),
    database=os.getenv("NEO4J_DATABASE"),
)

MOOD_KEYWORDS = ["피로", "집중", "창의", "스트레스", "활기", "신뢰", "미니멀"]

def extract_mood(description_text: str) -> str:
    if not description_text: return None
    try:
        data = json.loads(description_text)
        text = str(data)
    except:
        text = description_text
    
    for kw in MOOD_KEYWORDS:
        if kw in text: return kw
    return None

def get_shared_mood_node(mood_label: str, domain: str) -> EntityNode:
    return EntityNode(
        name=mood_label,
        label="MoodState",
        properties={"detected_in_domain": domain} 
    )

def ingest_design_from_dict(data: dict):
    """
    [디자인 도메인] -> Neo4j 주입 최종본
    """
    # 1. 무드 추출
    mood_keyword = extract_mood(data.get("description", ""))
    if not mood_keyword: return 
        
    # 2. 노드 생성
    design_node = EntityNode(
        name=f"design_{data['id']}",
        label="DesignSession",
        properties={
            "brightness": data["brightness"],
            "complexity": data["complexity"],
            "created_at": data.get("created_at", "N/A")
        }
    )
    
    
    mood_node = get_shared_mood_node(mood_keyword, "design")
    
    # 3. 관계 생성
    relation = Relation(
        source_id=design_node.id,
        target_id=mood_node.id,
        label="REFLECTS_MOOD"
    )
    
    # 4. Neo4j 저장
    graph_store.upsert_nodes([design_node, mood_node])
    graph_store.upsert_relations([relation])
    print(f"✅ [Design Sync] design_{data['id']} → {mood_keyword} (VIP 라운지 입장)")   