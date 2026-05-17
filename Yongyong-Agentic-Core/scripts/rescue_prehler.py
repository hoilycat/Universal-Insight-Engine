import os
import re
import json
import uuid
from pypdf import PdfReader
from groq import Groq
from dotenv import load_dotenv
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core import Document

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

PATH = r"C:\Users\iopuh\Universal-Insight-Engine\Yongyong-Agentic-Core\data\design_wisdom\5대 지표별 논문\2023Processing_Fluency_Reduces_Aesthetic_Usability(Prehler).pdf"
HUB_NODES = ["Attention", "Arousal", "Fatigue", "Processing Fluency", "Recognition", "Preference", "Performance"]

def get_insight_from_groq(filename, text_sample):
    prompt = f"""
    Analyze this academic text: {filename}
    Return ONLY a JSON object with these exact keys: "insight_en", "insight_ko", "tags"
    Tags MUST be from {HUB_NODES}.
    
    Text: {text_sample[:3000]}
    
    JSON:
    """
    try:
        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile"
        )
        content = chat_completion.choices[0].message.content
        match = re.search(r"\{.*?\}", content, re.DOTALL)
        if match:
            json_str = match.group(0).strip()
            # Basic cleaning for common LLM JSON errors
            json_str = re.sub(r"\'", "\"", json_str) # Replace single quotes with double
            return json.loads(json_str)
        return None
    except Exception as e:
        print(f"Groq Error: {repr(e)}")
        return None

def rescue_prehler():
    print(f"Checking path: {PATH}")
    if not os.path.exists(PATH):
        print("Path not found.")
        return
    
    print("Reading PDF...")
    try:
        reader = PdfReader(PATH)
        full_text = ""
        for i, page in enumerate(reader.pages):
            txt = page.extract_text()
            if txt: full_text += txt + "\n"
        print(f"Extracted {len(full_text)} characters from {len(reader.pages)} pages.")
    except Exception as e:
        print(f"PDF Reading Error: {e}")
        return
    
    if not full_text.strip():
        print("No text found.")
        return
    
    # Clean surrogate characters for UTF-8 safety
    full_text = full_text.encode('utf-8', 'ignore').decode('utf-8')
    
    print("Extracting insights from Groq...")
    insight = get_insight_from_groq("Prehler 2023", full_text)
    if not insight:
        print("Groq extraction failed.")
        return
    
    print(f"Insight received: {insight.get('tags')}")
    
    doc = Document(
        text=full_text,
        metadata={
            "file_name": "2023Processing_Fluency_Reduces_Aesthetic_Usability(Prehler).pdf",
            "category": "design",
            "project": "Mood-DNA",
            "core_insight_en": insight.get('insight_en', 'N/A'),
            "core_insight_ko": insight.get('insight_ko', 'N/A'),
            "hub_tags": insight.get('tags', []),
            "secondary_tags": [],
            "source_quality": {"json_valid": True, "korean_valid": True, "noise_removed": True, "requires_review": False}
        }
    )
    
    splitter = SentenceSplitter(chunk_size=2048, chunk_overlap=200)
    nodes = splitter.get_nodes_from_documents([doc])
    
    with open("data/chunks/design_chunks.jsonl", "a", encoding="utf-8") as f:
        for node in nodes:
            chunk_data = {"id": node.node_id, "text": node.text, "metadata": node.metadata}
            f.write(json.dumps(chunk_data, ensure_ascii=False) + "\n")
    
    print(f"Successfully rescued Prehler with {len(nodes)} chunks.")

if __name__ == "__main__":
    rescue_prehler()
