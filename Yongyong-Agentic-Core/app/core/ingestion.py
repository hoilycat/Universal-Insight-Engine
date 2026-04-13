import os
import json
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from llama_index.graph_stores.neo4j import Neo4jPropertyGraphStore
from llama_index.core.graph_stores.types import EntityNode, Relation

from app.database import DesignHistory

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
    """
    JSON 텍스트나 일반 텍스트에서 감정 키워드를 추출 (클로드 로직)
    """
    if not description_text:
        return None
        
    try:
        data = json.loads(description_text)
        text = str(data)
    except:
        text = description_text
    
    for kw in MOOD_KEYWORDS:
        if kw in text:
            return kw
    return None

def ingest_design_from_dict(data: dict):
    """
    [디자인 도메인] -> Neo4j 주입 (딕셔너리 버전)
    auto_ingest.py에서 백그라운드 태스크로 호출함
    """
    # 1. 무드 추출
    mood_keyword = extract_mood(data.get("description", ""))
    if not mood_keyword:
        return 
        
    # 2. 노드 생성
    design_node = EntityNode(
        name=f"design_{data['id']}",
        label="DesignSession",
        properties={
            "brightness": data["brightness"],
            "complexity": data["complexity"],
        }
    )
    
    # 공통 무드 노드 가져오기
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
    print(f"✅ [Design] Neo4j 저장 완료: design_{data['id']} → {mood_keyword}")


def get_shared_mood_node(mood_label: str, domain: str) -> EntityNode:
    """
    ★ 핵심 로직 ★
    이름(name)이 같으면 Neo4j가 스스로 하나로 합쳐줌 (허브 역할)
    """
    return EntityNode(
        name=mood_label,
        label="MoodState",
        properties={"detected_in_domain": domain} 
    )

def ingest_design_record(record: DesignHistory):
    """
    [디자인 도메인] -> Neo4j 주입
    """
    # 1. 무드 추출 시도
    mood_keyword = extract_mood(getattr(record, 'description', ""))
    if not mood_keyword:
        return # 키워드 없으면 버림 (VIP 라운지 입장 불가)
        
    if record.id is None:
        return  # 안전장치: ID 없으면 진행 불가 (커밋 후에 ID 할당됨)

    
    # 2. 노드 생성
    design_node = EntityNode(
        name=f"design_{record.id}",
        label="DesignSession",
        properties={
            "brightness": record.brightness,
            "complexity": record.complexity,
        }
    )
    
    # 공통 무드 노드 가져오기
    mood_node = get_shared_mood_node(mood_keyword, "design")
    
    # 3. 관계(엣지) 생성
    relation = Relation(
        source_id=design_node.id,
        target_id=mood_node.id,
        label="REFLECTS_MOOD"
    )
    
    # 4. DB에 저장 (Upsert)
    graph_store.upsert_nodes([design_node, mood_node])
    graph_store.upsert_relations([relation])
    print(f"✅ [Design] Neo4j 저장 완료: design_{record.id} → {mood_keyword}")

    