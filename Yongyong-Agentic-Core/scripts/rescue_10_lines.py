import json
import urllib.request
from pathlib import Path

ROOT_DIR = Path(r"C:\Users\iopuh\Universal-Insight-Engine")
DESIGN_FILE = ROOT_DIR / "Yongyong-Agentic-Core" / "data" / "chunks" / "design_chunks.jsonl"
HEALTH_FILE = ROOT_DIR / "Yongyong-Agentic-Core" / "data" / "chunks" / "health_chunks.jsonl"

def generate_exaone(prompt):
    url = "http://127.0.0.1:11434/api/generate"
    payload = {
        "model": "exaone3.5:latest",
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.4} # Slightly higher temp to prevent repetitive 1-char outputs
    }
    req = urllib.request.Request(url, headers={'Content-Type': 'application/json'}, data=json.dumps(payload).encode('utf-8'))
    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            data = json.loads(response.read())
            return data.get("response", "").strip()
    except Exception as e:
        print(f"Error: {e}")
        return ""

def process_file(file_path, target_lines):
    with open(file_path, "r", encoding="utf-8-sig") as f:
        lines = f.readlines()
        
    changed = 0
    for idx in target_lines:
        i = idx - 1 # 0-indexed
        if i >= len(lines): continue
        
        chunk = json.loads(lines[i])
        meta = chunk.get("metadata", {})
        en_insight = meta.get("core_insight_en", "")
        if not en_insight or en_insight == "N/A":
            en_insight = chunk["text"][:1000]
            
        prompt_ko = f"Translate the following academic summary into a complete, professional Korean sentence. You MUST output at least 30 characters. Do not output single words. Provide a full sentence.\n\nEnglish Summary: {en_insight}"
        
        print(f"Regenerating {file_path.name} line {idx}...")
        new_ko = generate_exaone(prompt_ko)
        
        if new_ko and len(new_ko) >= 20:
            meta["core_insight_ko"] = new_ko
            chunk["metadata"] = meta
            lines[i] = json.dumps(chunk, ensure_ascii=False) + "\n"
            changed += 1
            print(f"Success! Length: {len(new_ko)}")
        else:
            print(f"Failed. Output: {new_ko}")

    if changed > 0:
        with open(file_path, "w", encoding="utf-8-sig") as f:
            f.writelines(lines)
        print(f"Patched {changed} lines in {file_path.name}.")

def main():
    design_targets = [880, 995, 1042]
    health_targets = [169, 198, 203, 236, 247, 272, 286]
    
    process_file(DESIGN_FILE, design_targets)
    process_file(HEALTH_FILE, health_targets)

if __name__ == "__main__":
    main()
