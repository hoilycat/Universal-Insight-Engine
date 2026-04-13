from neo4j import GraphDatabase
import os

driver = GraphDatabase.driver(
    os.getenv("NEO4J_URI"),
    auth=(os.getenv("NEO4J_USERNAME"), os.getenv("NEO4J_PASSWORD"))
)

def query_cross_domain_brightness_by_mood(mood: str) -> dict:
    """
    "피로할 때 만든 디자인의 평균 밝기는?"
    [CoffeeSession] -CAUSED_REACTION-> [MoodState] <-REFLECTS_MOOD- [DesignSession]
    """
    cypher = """
    MATCH (c:CoffeeSession)-[:CAUSED_REACTION]->(m:MoodState {name: $mood})
          <-[:REFLECTS_MOOD]-(d:DesignSession)
    RETURN 
        m.name AS mood,
        COUNT(d) AS design_count,
        AVG(d.brightness) AS avg_brightness,
        AVG(d.complexity) AS avg_complexity
    """
    with driver.session() as session:
        result = session.run(cypher, mood=mood)
        record = result.single()
        if not record:
            return {"message": f"'{mood}' 관련 크로스 데이터 없음"}
        return {
            "mood": record["mood"],
            "design_count": record["design_count"],
            "avg_brightness": round(record["avg_brightness"], 2),
            "avg_complexity": round(record["avg_complexity"], 2),
        }
    
    # Mood-DNA 전용 스키마 (디자인만)
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

# Cof/fee 전용 스키마 (건강만)
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