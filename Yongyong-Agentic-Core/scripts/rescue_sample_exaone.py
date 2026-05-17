import json
import urllib.request
from pathlib import Path

ROOT_DIR = Path(r"C:\Users\iopuh\Universal-Insight-Engine")
DESIGN_FILE = ROOT_DIR / "Yongyong-Agentic-Core" / "data" / "chunks" / "design_chunks.jsonl"
SAMPLE_OUTPUT_FILE = ROOT_DIR / "Yongyong-Agentic-Core" / "data" / "chunks" / "exaone_sample_20.json"

def generate_exaone(prompt):
    url = "http://127.0.0.1:11434/api/generate"
    payload = {
        "model": "exaone3.5:latest",
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.3}
    }
    req = urllib.request.Request(url, headers={'Content-Type': 'application/json'}, data=json.dumps(payload).encode('utf-8'))
    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            data = json.loads(response.read())
            return data.get("response", "").strip()
    except Exception as e:
        print(f"Error: {e}")
        return ""

def main():
    with open(DESIGN_FILE, "r", encoding="utf-8-sig") as f:
        lines = [line for line in f if line.strip()][:20]
        
    print(f"Loaded {len(lines)} chunks for EXAONE sampling.")
    
    results = []
    for i, line in enumerate(lines):
        chunk = json.loads(line)
        en_insight = chunk["metadata"].get("core_insight_en", "")
        if not en_insight or en_insight == "N/A" or "This study explores the influence of design elements" in en_insight:
            en_insight = chunk["text"][:1000] # Fallback if missing or placeholder
            
        prompt = f"Translate the following academic summary into natural, professional Korean. Output ONLY the Korean translation, without quotes, keeping it concise (1-3 sentences).\n\nText to translate:\n{en_insight}"
        print(f"Processing sample {i+1}/20 with EXAONE...")
        ko_insight = generate_exaone(prompt)
        
        results.append({
            "id": chunk.get("id"),
            "file_name": chunk["metadata"]["file_name"],
            "core_insight_en": en_insight,
            "core_insight_ko_generated": ko_insight
        })
        
    with open(SAMPLE_OUTPUT_FILE, "w", encoding="utf-8-sig") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
        
    print("Done! Saved to exaone_sample_20.json")

if __name__ == "__main__":
    main()
