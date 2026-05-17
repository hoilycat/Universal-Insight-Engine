# app/core/knowledge_loader.py
import os
from llama_index.core import SimpleDirectoryReader, PropertyGraphIndex, StorageContext
from llama_index.graph_stores.neo4j import Neo4jPropertyGraphStore
from llama_index.llms.gemini import Gemini
from dotenv import load_dotenv

load_dotenv()

def load_wisdom_to_graph(directory_path: str):
    """
    지정된 폴더(design_wisdom 등)의 모든 파일을 읽어서 Neo4j 그래프로 만듭니다.
    """
    # 1. 문서 읽기 (txt, pdf 등 싹 다 읽어옴)
    documents = SimpleDirectoryReader(directory_path).load_data()
    print(f"📚 {len(documents)}개의 문서를 읽어왔습니다.")

    # 2. 그래프 저장소 설정
    graph_store = Neo4jPropertyGraphStore(
        username=os.getenv("NEO4J_USERNAME"),
        password=os.getenv("NEO4J_PASSWORD"),
        url=os.getenv("NEO4J_URI"),
    )

    # 3. 지식 그래프 인덱스 생성 (여기서 AI가 엔티티를 추출해서 그래프를 그려!)
    # gemini-1.5-flash를 쓰면 속도도 빠르고 비용도 싸!
    index = PropertyGraphIndex.from_documents(
        documents,
        llm=Gemini(model_name="models/gemini-1.5-flash"),
        property_graph_store=graph_store,
        show_progress=True
    )
    
    print("✅ 지식 그래프 주입 완료!")
    return index