# app/core/graph.py
import os
from llama_index.core import StorageContext, PropertyGraphIndex
from llama_index.graph_stores.neo4j import Neo4jPropertyGraphStore
from llama_index.vector_stores.chroma import ChromaVectorStore
import chromadb

def get_hybrid_index():
    # 1. 그래프 창고 연결 (Cloud Neo4j)
    graph_store = Neo4jPropertyGraphStore(
        username=os.getenv("NEO4J_USERNAME"),
        password=os.getenv("NEO4J_PASSWORD"),
        url=os.getenv("NEO4J_URI"),
        database=os.getenv("NEO4J_DATABASE", "neo4j"),
    )

    # 2. 벡터 창고 연결 (Local ChromaDB)
    # 별도 설치 없이 프로젝트 폴더 내 './chroma_db'에 자동 저장됨!
    db = chromadb.PersistentClient(path="./chroma_db")
    chroma_collection = db.get_or_create_collection("y_insight_vectors")
    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)

    # 3. 하이브리드 합체! (Storage Context)
    storage_context = StorageContext.from_defaults(
        graph_store=graph_store,
        vector_store=vector_store
    )
    
    return storage_context

# 이 함수를 나중에 인덱스 생성할 때 부르면 끝!