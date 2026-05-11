import os
import json
from llama_index.graph_stores.neo4j import Neo4jPropertyGraphStore
from llama_index.core.graph_stores.types import EntityNode, Relation
from dotenv import load_dotenv

load_dotenv()

# Setup Neo4j Store
graph_store = Neo4jPropertyGraphStore(
    username=os.getenv("NEO4J_USERNAME", "neo4j"),
    password=os.getenv("NEO4J_PASSWORD"),
    url=os.getenv("NEO4J_URI"),
    database=os.getenv("NEO4J_DATABASE"),
)

def ingest_kb_chunks(file_path):
    print(f"[*] Ingesting KB Chunks from {file_path} into Neo4j...")
    
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            data = json.loads(line)
            chunk_id = data["id"]
            text = data["text"]
            meta = data["metadata"]
            
            # 1. Create Paper Node (Unique by name)
            paper_name = meta.get("file_name", "Unknown Paper")
            paper_node = EntityNode(
                label="Paper",
                name=paper_name,
                properties={
                    "category": meta.get("category"),
                    "project": meta.get("project")
                }
            )
            
            # 2. Create Chunk Node (Unique by chunk_id)
            chunk_node = EntityNode(
                label="Chunk",
                name=f"chunk_{chunk_id[:8]}",
                properties={
                    "text": text,
                    "chunk_id": chunk_id
                }
            )
            
            # 3. Create Insight Node (Unique by chunk_id)
            insight_node = EntityNode(
                label="Insight",
                name=f"insight_{chunk_id[:8]}",
                properties={
                    "en": meta.get("core_insight_en"),
                    "ko": meta.get("core_insight_ko")
                }
            )
            
            # Relationships using proper IDs
            rels = [
                Relation(source_id=paper_node.id, target_id=chunk_node.id, label="HAS_CHUNK"),
                Relation(source_id=chunk_node.id, target_id=insight_node.id, label="PROVIDES_INSIGHT")
            ]
            
            # 4. Create HubTag Nodes & Relations (Unique by name)
            hub_tags = meta.get("hub_tags", [])
            tag_nodes = []
            for tag_name in hub_tags:
                tag_node = EntityNode(label="HubTag", name=tag_name)
                tag_nodes.append(tag_node)
                rels.append(Relation(source_id=chunk_node.id, target_id=tag_node.id, label="DESCRIBES_TAG"))
            
            # Batch Upsert (LlamaIndex handles MERGE if IDs are consistent)
            graph_store.upsert_nodes([paper_node, chunk_node, insight_node] + tag_nodes)
            graph_store.upsert_relations(rels)
            
    print(f"✅ Ingestion complete for {file_path}")

if __name__ == "__main__":
    # This will be called after refinement is verified
    # ingest_kb_chunks("data/chunks/design_chunks.jsonl")
    # ingest_kb_chunks("data/chunks/health_chunks.jsonl")
    pass
