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
    
   