# app/core/ingestion_coffee.py
import os
from llama_index.graph_stores.neo4j import Neo4jPropertyGraphStore
from llama_index.core.graph_stores.types import EntityNode, Relation
from .ingestion import get_shared_mood_node, extract_mood

graph_store = Neo4jPropertyGraphStore(
    username=os.getenv("NEO4J_USERNAME", "neo4j"),
    password=os.getenv("NEO4J_PASSWORD"),
    url=os.getenv("NEO4J_URI"),
    database=os.getenv("NEO4J_DATABASE"), 
)

def ingest_coffee_from_dict(data: dict):
    """
    [커피 도메인] -> Neo4j 주입 및 무드 연결
    """
    # 1. 신체 반응에서 무드 키워드 추출
    mood_keyword = extract_mood(data["body_reaction"])
    if not mood_keyword:
        return

    # 2. 노드 생성 (커피 로그)
    coffee_node = EntityNode(
        name=f"coffee_{data['id']}",
        label="CoffeeSession",
        properties={
            "caffeine_mg": data["caffeine_mg"],
            "drink_type": data["drink_type"],
            "created_at": data["created_at"]
        }
    )
    
    # 공통 무드 노드 (ingestion.py에 있는 함수 재사용!)
    mood_node = get_shared_mood_node(mood_keyword, "coffee")

    # 3. 관계 생성 (커피가 무드를 유발함)
    relation = Relation(
        source_id=coffee_node.id,
        target_id=mood_node.id,
        label="CAUSED_REACTION"
    )

    graph_store.upsert_nodes([coffee_node, mood_node])
    graph_store.upsert_relations([relation])
    print(f"✅ [Coffee] Neo4j 저장 완료: coffee_{data['id']} → {mood_keyword}")