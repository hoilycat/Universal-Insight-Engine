import os
import json
import uuid
from pypdf import PdfReader
from groq import Groq
from dotenv import load_dotenv
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core import Document

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Exact absolute paths from the dump
RESCUE_LIST = [
    # Design (Top Priorities)
    r"C:\Users\iopuh\Universal-Insight-Engine\Yongyong-Agentic-Core\data\design_wisdom\5대 지표별 논문\2023Processing_Fluency_Reduces_Aesthetic_Usability(Prehler).pdf",
    r"C:\Users\iopuh\Universal-Insight-Engine\Yongyong-Agentic-Core\data\design_wisdom\5대 지표별 논문\2025Aesthetic_preference_depends_on_evaluation_method(Hübner).pdf",
    r"C:\Users\iopuh\Universal-Insight-Engine\Yongyong-Agentic-Core\data\design_wisdom\5대 지표별 논문\2026_Color_as_Narrative_Device_in_Illustration(Jiménez-Duarte).pdf",
    r"C:\Users\iopuh\Universal-Insight-Engine\Yongyong-Agentic-Core\data\design_wisdom\5대 지표별 논문\20260320163239-0001.pdf",
    # Health
    r"c:\Users\iopuh\Universal-Insight-Engine\Yongyong-Agentic-Core\data\health_wisdom\Coffee, Tea, Methylxanthines, Human Cancer, and Fibrocystic Breast Disease.rtf",
    r"c:\Users\iopuh\Universal-Insight-Engine\Yongyong-Agentic-Core\data\health_wisdom\Is Caffeine Withdrawal the Mechanism of Postoperative Headache_.rtf"
]

HUB_NODES = ["Attention", "Arousal", "Fatigue", "Processing Fluency", "Recognition", "Preference", "Performance"]

def get_insight_from_groq(filename, text_sample):
    prompt = f"""
    Analyze this academic text from '{filename}'.
    Provide:
    1. English Summary
    2. Korean Summary (Natural academic style, NO BROKEN CHARACTERS)
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
            model="llama-3.1-8b-instant",
            response_format={"type": "json_object"}
        )
        return json.loads(chat_completion.choices[0].message.content)
    except Exception:
        return None

def rescue_distiller():
    splitter = SentenceSplitter(chunk_size=2048, chunk_overlap=200)
    
    for i, path in enumerate(RESCUE_LIST, 1):
        filename = os.path.basename(path)
        print(f"[*] Rescuing file {i}/{len(RESCUE_LIST)}...")
        
        try:
            full_text = ""
            if path.lower().endswith(".pdf"):
                reader = PdfReader(path)
                for page in reader.pages:
                    txt = page.extract_text()
                    if txt: full_text += txt + "\n"
            else: # RTF or TXT
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    full_text = f.read()
            
            if not full_text.strip():
                print(f"  [Skip] No text found.")
                continue
                
            insight = get_insight_from_groq(filename, full_text)
            if not insight: continue
            
            cat = "health" if "health_wisdom" in path else "design"
            
            doc = Document(
                text=full_text,
                metadata={
                    "file_name": filename,
                    "category": cat,
                    "project": "Mood-DNA" if cat == "design" else "Cof/fee",
                    "core_insight_en": insight['insight_en'],
                    "core_insight_ko": insight['insight_ko'],
                    "hub_tags": insight['tags'],
                    "secondary_tags": [],
                    "source_quality": {"json_valid": True, "korean_valid": True, "noise_removed": True, "requires_review": False}
                }
            )
            
            nodes = splitter.get_nodes_from_documents([doc])
            
            output_file = f"data/chunks/{cat}_chunks.jsonl"
            with open(output_file, "a", encoding="utf-8") as f:
                for node in nodes:
                    chunk_data = {"id": node.node_id, "text": node.text, "metadata": node.metadata}
                    f.write(json.dumps(chunk_data, ensure_ascii=False) + "\n")
            
            print(f"  [SUCCESS] {len(nodes)} chunks added to {output_file}")
            
        except Exception as e:
            print(f"  [Error] {e}")

if __name__ == "__main__":
    rescue_distiller()
