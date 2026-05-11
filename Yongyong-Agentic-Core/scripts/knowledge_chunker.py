import os
import json
import re
import sys
from pypdf import PdfReader
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core import Document

if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE_DIR = r"c:\Users\iopuh\Universal-Insight-Engine"
REPORT_PATH = os.path.join(BASE_DIR, "Yongyong-Agentic-Core", "screening_report.md")
SELECTED_DIR = os.path.join(BASE_DIR, "data", "selected_wisdom")
OUTPUT_DIR = os.path.join(BASE_DIR, "Yongyong-Agentic-Core", "data", "chunks")

CATEGORIES = ["design", "health"]

def parse_report_summaries_v2():
    if not os.path.exists(REPORT_PATH): return {}
    with open(REPORT_PATH, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read().replace(r"\_", "_")
    summaries = {}
    sections = re.findall(r"### (.*?\.pdf)\n(.*?)(?=### |$)", content, re.DOTALL)
    for filename, details in sections:
        insight_match = re.search(r"(\*\*핵심 데이터\*\*|\*\*?심?사? ?요?약\*\*?|\*\*?🎯 핵심 데이터\*\*?)(.*?)(?=---|$)", details, re.DOTALL | re.IGNORECASE)
        if insight_match:
            insight_text = insight_match.group(2).strip()
            insight_text = re.sub(r"[\*#>-]", "", insight_text).strip()
            summaries[filename.strip()] = insight_text
        else:
            summaries[filename.strip()] = "Knowledge base foundation for Mood-DNA/Coffee analysis."
    return summaries

def is_garbage_v2(text):
    if not text: return True
    if any(p in text for p in ["%PDF", "obj <<", "stream", "endstream", "endobj"]): return True
    skip_keywords = ["Table of Contents", "Contributors", "Dedication", "List of Figures", "Acknowledgements", "References"]
    if len(text) < 500:
        for kw in skip_keywords:
            if kw.lower() in text.lower(): return True
    alnum_chars = [c for c in text if c.isalnum()]
    if len(text) > 0 and len(alnum_chars) / len(text) < 0.4: return True
    return False

def run_chunking_v5():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    report_summaries = parse_report_summaries_v2()
    # 청크 사이즈를 2048로 확대하여 메타데이터가 차지하는 공간을 확보
    splitter = SentenceSplitter(chunk_size=2048, chunk_overlap=200)
    
    for cat in CATEGORIES:
        input_dir = os.path.join(SELECTED_DIR, cat)
        if not os.path.exists(input_dir): continue
            
        print(f"[*] Starting {cat} category (High-Capacity Insight Mode)...")
        all_nodes = []
        pdf_files = []
        for root, dirs, files in os.walk(input_dir):
            for f in files:
                if f.lower().endswith(".pdf"):
                    pdf_files.append(os.path.join(root, f))

        total = len(pdf_files)
        for i, pdf_path in enumerate(pdf_files, 1):
            filename = os.path.basename(pdf_path)
            if i % 10 == 0 or i == total: print(f"  - Processing: {i}/{total}")
            
            try:
                reader = PdfReader(pdf_path)
                full_text = ""
                for page_idx, page in enumerate(reader.pages):
                    try:
                        text = page.extract_text()
                        if text and not is_garbage_v2(text):
                            full_text += f"[Page {page_idx+1}]\n{text}\n\n"
                    except: continue
                
                if not full_text.strip(): continue
                full_text = full_text.encode('utf-8', 'ignore').decode('utf-8')
                
                # 메타데이터 글자수 제한 (안정성을 위해 1500자로 제한)
                core_insight = report_summaries.get(filename, "General Insight")
                if len(core_insight) > 1500:
                    core_insight = core_insight[:1497] + "..."
                
                doc = Document(
                    text=full_text,
                    metadata={
                        "file_name": filename,
                        "project": "Mood-DNA" if cat == "design" else "Cof/fee",
                        "category": cat,
                        "core_insight": core_insight
                    }
                )
                nodes = splitter.get_nodes_from_documents([doc])
                all_nodes.extend(nodes)
                
            except Exception as e:
                print(f"    [Error] Problem with {filename}: {e}")

        output_file = os.path.join(OUTPUT_DIR, f"{cat}_chunks.jsonl")
        with open(output_file, "w", encoding="utf-8", errors="ignore") as f:
            for node in all_nodes:
                chunk_data = {"id": node.node_id, "text": node.text, "metadata": node.metadata}
                f.write(json.dumps(chunk_data, ensure_ascii=False) + "\n")
        
        print(f"  [SUCCESS] {len(all_nodes)} high-capacity chunks saved.")

if __name__ == "__main__":
    run_chunking_v5()
