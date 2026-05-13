import json
from pathlib import Path

ROOT_DIR = Path(r"C:\Users\iopuh\Universal-Insight-Engine")
DESIGN_FILE = ROOT_DIR / "Yongyong-Agentic-Core" / "data" / "chunks" / "design_chunks.jsonl"

def remove_cyrillic(text):
    # EXAONE sometimes hallucinates cyrillic 'у' (0x0443) instead of 'y'
    res = []
    for c in text:
        if 0x0400 <= ord(c) <= 0x052F:
            if ord(c) == 0x0443: res.append('y')
            elif ord(c) == 0x0430: res.append('a')
            elif ord(c) == 0x0435: res.append('e')
            elif ord(c) == 0x043E: res.append('o')
            elif ord(c) == 0x0441: res.append('c')
            else: pass # remove other cyrillic
        else:
            res.append(c)
    return "".join(res)

def main():
    with open(DESIGN_FILE, "r", encoding="utf-8-sig") as f:
        lines = f.readlines()
        
    changed = 0
    for i, line in enumerate(lines):
        if not line.strip(): continue
        
        chunk = json.loads(line)
        meta = chunk.get("metadata", {})
        ko = meta.get("core_insight_ko", "")
        
        new_ko = remove_cyrillic(ko)
        new_ko = new_ko.replace("오류", "결함").replace("번역", "해석")
        
        if new_ko != ko:
            meta["core_insight_ko"] = new_ko
            chunk["metadata"] = meta
            lines[i] = json.dumps(chunk, ensure_ascii=False) + "\n"
            changed += 1

    if changed > 0:
        with open(DESIGN_FILE, "w", encoding="utf-8-sig") as f:
            f.writelines(lines)
        print(f"Patched {changed} lines.")
    else:
        print("No lines patched.")

if __name__ == "__main__":
    main()
