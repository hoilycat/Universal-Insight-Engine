import os
import json
import argparse
from pathlib import Path
from dotenv import load_dotenv
from neo4j import GraphDatabase

ROOT_DIR = Path(r"C:\Users\iopuh\Universal-Insight-Engine")
load_dotenv(ROOT_DIR / ".env")

URI = os.getenv("NEO4J_URI", "neo4j://127.0.0.1:7687").strip()
USERNAME = os.getenv("NEO4J_USERNAME", "neo4j").strip()
PASSWORD = os.getenv("NEO4J_PASSWORD", "yongyong1234").strip()
DATABASE = os.getenv("NEO4J_DATABASE", "neo4j").strip()

DESIGN_FILE = ROOT_DIR / "Yongyong-Agentic-Core" / "data" / "chunks" / "design_chunks.jsonl"
HEALTH_FILE = ROOT_DIR / "Yongyong-Agentic-Core" / "data" / "chunks" / "health_chunks.jsonl"

def get_chunks():
    chunks = []
    for f in [DESIGN_FILE, HEALTH_FILE]:
        with open(f, "r", encoding="utf-8-sig") as file:
            for line in file:
                if line.strip():
                    chunks.append(json.loads(line))
    return chunks

def create_constraints(tx):
    # 1. Create constraints for performance and uniqueness
    tx.run("CREATE CONSTRAINT document_name_unique IF NOT EXISTS FOR (d:Document) REQUIRE d.name IS UNIQUE")
    tx.run("CREATE CONSTRAINT chunk_id_unique IF NOT EXISTS FOR (c:Chunk) REQUIRE c.id IS UNIQUE")
    tx.run("CREATE CONSTRAINT tag_name_unique IF NOT EXISTS FOR (t:Tag) REQUIRE t.name IS UNIQUE")

def ingest_to_neo4j(tx, chunks):
    docs_created = 0
    chunks_created = 0
    tags_created = 0
    
    # 2. Ingest
    for chunk in chunks:
        meta = chunk.get("metadata", {})
        doc_name = meta.get("file_name", "Unknown")
        chunk_id = chunk.get("id")
        text = chunk.get("text", "")
        en_insight = meta.get("core_insight_en", "")
        ko_insight = meta.get("core_insight_ko", "")
        tags = meta.get("hub_tags", [])
        
        # Merge Document
        tx.run("""
            MERGE (d:Document {name: $doc_name})
        """, doc_name=doc_name)
        
        # Merge Chunk and link to Document
        tx.run("""
            MATCH (d:Document {name: $doc_name})
            MERGE (c:Chunk {id: $chunk_id})
            SET c.text = $text,
                c.core_insight_en = $en_insight,
                c.core_insight_ko = $ko_insight
            MERGE (d)-[:CONTAINS]->(c)
        """, doc_name=doc_name, chunk_id=chunk_id, text=text, en_insight=en_insight, ko_insight=ko_insight)
        chunks_created += 1
        
        # Merge Tags and link to Chunk
        for tag in tags:
            tx.run("""
                MATCH (c:Chunk {id: $chunk_id})
                MERGE (t:Tag {name: $tag_name})
                MERGE (c)-[:HAS_TAG]->(t)
            """, chunk_id=chunk_id, tag_name=tag)

def main():
    parser = argparse.ArgumentParser(description="Ingest Knowledge Base chunks into Neo4j")
    parser.add_argument("--reset", action="store_true", help="CAUTION: Delete all existing nodes and relationships before ingestion")
    parser.add_argument("--dry-run", action="store_true", help="Print expected nodes and relationships, then exit without modifying the database")
    args = parser.parse_args()

    print("Loading data for dry-run...")
    chunks = get_chunks()
    
    docs = set(c['metadata']['file_name'] for c in chunks)
    tags = set(t for c in chunks for t in c['metadata'].get('hub_tags', []))
    tag_rels = sum(len(c['metadata'].get('hub_tags', [])) for c in chunks)
    
    print("\n--- [ DRY RUN EXPECTATION ] ---")
    print(f"Expected New Nodes: Documents={len(docs)}, Chunks={len(chunks)}, Tags={len(tags)}")
    print(f"Expected New Relationships: CONTAINS={len(chunks)}, HAS_TAG={tag_rels}")
    print("-------------------------------\n")
    
    if args.dry_run:
        print("Dry-run mode active. Exiting before database connection.")
        return
    
    print(f"Connecting to Neo4j at {URI} (Database: {DATABASE})...")
    driver = GraphDatabase.driver(URI, auth=(USERNAME, PASSWORD))
    
    with driver.session(database=DATABASE) as session:
        if args.reset:
            print("WARNING: --reset flag detected. Clearing existing graph...")
            session.run("MATCH (n) DETACH DELETE n")
            print("Graph cleared.")
        else:
            print("Upsert-only mode (default). Existing nodes will be merged, not deleted.")
            
        print("Creating constraints (if not exist)...")
        session.execute_write(create_constraints)
            
        print("Ingesting data to Neo4j...")
        session.execute_write(ingest_to_neo4j, chunks)
        
        # Verification Queries
        print("\n--- [ INGESTION VERIFICATION ] ---")
        doc_count = session.run("MATCH (d:Document) RETURN count(d) as cnt").single()["cnt"]
        chunk_count = session.run("MATCH (c:Chunk) RETURN count(c) as cnt").single()["cnt"]
        tag_count = session.run("MATCH (t:Tag) RETURN count(t) as cnt").single()["cnt"]
        rel_contains = session.run("MATCH ()-[r:CONTAINS]->() RETURN count(r) as cnt").single()["cnt"]
        rel_has_tag = session.run("MATCH ()-[r:HAS_TAG]->() RETURN count(r) as cnt").single()["cnt"]
        
        print(f"Actual Nodes in DB: Documents={doc_count}, Chunks={chunk_count}, Tags={tag_count}")
        print(f"Actual Relationships in DB: CONTAINS={rel_contains}, HAS_TAG={rel_has_tag}")
        print("----------------------------------\n")
        
    driver.close()
    print("Neo4j Ingestion Complete!")

if __name__ == "__main__":
    main()
