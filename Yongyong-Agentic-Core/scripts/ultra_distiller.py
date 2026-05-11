import os
import json
import re
import sys
import time
from pypdf import PdfReader
from groq import Groq
from dotenv import load_dotenv
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core import Document

if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

BASE_DIR = r"c:\Users\iopuh\Universal-Insight-Engine"
OUTPUT_DIR = os.path.join(BASE_DIR, "Yongyong-Agentic-Core", "data", "chunks")
TARGET_FOLDERS = [
    os.path.join(BASE_DIR, "data", "selected_wisdom"),
    os.path.join(BASE_DIR, "Yongyong-Agentic-Core", "data", "design_wisdom"),
    os.path.join(BASE_DIR, "Yongyong-Agentic-Core", "data", "health_wisdom")
]

HUB_NODES = ["Attention", "Arousal", "Fatigue", "Processing Fluency", "Recognition", "Preference", "Performance"]

def get_insight_from_groq(filename, text_sample):
    prompt = f"""
    Analyze this academic text from '{filename}'.
    Extract core quantitative metrics and design/health insights.
    Provide:
    1. English Summary
    2. Korean Summary
    3. Tags from this list: {HUB_NODES}
    
    Text: {text_sample[:4000]}
    
    Response format (JSON ONLY):
    {{
        "insight_en": "...",
        "insight_ko": "...",
        "tags": ["Tag1", "Tag2"]
    }}
    """
    try:
        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.1-8b-instant", # 할당량이 넉넉한 8b 모델로 변경
            response_format={"type": "json_object"}
        )
        return json.loads(chat_completion.choices[0].message.content)
    except Exception as e:
        print(f"      [Groq Error] {e}")
        return None

def is_garbage(text):
    if not text: return True
    garbage_patterns = ["%PDF", "obj <<", "stream", "endstream", "endobj"]
    if any(p in text for p in garbage_patterns): return True
    skip_kws = ["Table of Contents", "Contributors", "Dedication", "Acknowledgements", "References"]
    if len(text) < 500:
        for kw in skip_kws:
            if kw.lower() in text.lower(): return True
    alnum_ratio = sum(c.isalnum() for c in text) / max(len(text), 1)
    return alnum_ratio < 0.4

def run_ultra_distiller():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    splitter = SentenceSplitter(chunk_size=2048, chunk_overlap=200)
    
    # 모든 PDF 파일 수집 (중복 제거)
    all_pdfs = {}
    for folder in TARGET_FOLDERS:
        if not os.path.exists(folder): continue
        for root, dirs, files in os.walk(folder):
            for f in files:
                if f.lower().endswith(".pdf"):
                    # 파일명을 키로 하여 나중 경로가 우선(혹은 처음 경로)
                    if f not in all_pdfs:
                        # 카테고리 판별
                        cat = "health" if "health" in root.lower() or "caffeine" in f.lower() else "design"
                        all_pdfs[f] = {"path": os.path.join(root, f), "category": cat}

    print(f"[*] Found {len(all_pdfs)} unique papers to process.")
    
    paper_insights = {}
    final_nodes = {"design": [], "health": []}

    for i, (filename, info) in enumerate(all_pdfs.items(), 1):
        print(f"  [{i}/{len(all_pdfs)}] Reading PDF: {filename}")
        sys.stdout.flush()
        
        try:
            reader = PdfReader(info['path'])
            full_text = ""
            for p_idx, page in enumerate(reader.pages):
                try:
                    text = page.extract_text()
                    if text and not is_garbage(text):
                        full_text += f"[Page {p_idx+1}]\n{text}\n\n"
                except: continue
            
            if not full_text.strip(): 
                print(f"    [Skip] No valid text found in {filename}")
                continue
            
            print(f"    - Extracting insights from Groq...")
            sys.stdout.flush()
            
            # Groq 인사이트 추출
            insight = get_insight_from_groq(filename, full_text)
            if not insight:
                insight = {"insight_en": "N/A", "insight_ko": "N/A", "tags": []}
            
            print(f"    - Tags: {insight['tags']}")
            sys.stdout.flush()
            
            doc = Document(
                text=full_text,
                metadata={
                    "file_name": filename,
                    "category": info['category'],
                    "project": "Mood-DNA" if info['category'] == "design" else "Cof/fee",
                    "core_insight_en": insight['insight_en'],
                    "core_insight_ko": insight['insight_ko'],
                    "hub_tags": insight['tags']
                }
            )
            
            nodes = splitter.get_nodes_from_documents([doc])
            final_nodes[info['category']].extend(nodes)
            
        except Exception as e:
            print(f"    [Error] Skipping {filename}: {e}")

    # 결과 저장
    for cat in ["design", "health"]:
        output_file = os.path.join(OUTPUT_DIR, f"{cat}_chunks.jsonl")
        with open(output_file, "w", encoding="utf-8") as f:
            for node in final_nodes[cat]:
                chunk_data = {"id": node.node_id, "text": node.text, "metadata": node.metadata}
                f.write(json.dumps(chunk_data, ensure_ascii=False) + "\n")
        print(f"  [SUCCESS] {len(final_nodes[cat])} chunks saved to {cat}_chunks.jsonl")

if __name__ == "__main__":
    run_ultra_distiller()
