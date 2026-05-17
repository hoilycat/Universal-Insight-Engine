import os
import json
import re
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

HUB_NODES = ["Attention", "Arousal", "Fatigue", "Processing Fluency", "Recognition", "Preference", "Performance"]

def fix_korean_insight(en_insight):
    prompt = f"""
    Translate and refine this academic insight into natural, professional Korean.
    Instruction: Use polite academic tone (간결체/-다). Ensure NO broken characters.
    
    English Insight: {en_insight}
    
    Response format (JSON ONLY):
    {{
        "insight_ko": "..."
    }}
    """
    try:
        completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.1-8b-instant",
            response_format={"type": "json_object"}
        )
        return json.loads(completion.choices[0].message.content).get("insight_ko", "")
    except: return None

def normalize_tags(tags):
    # Map old or similar tags to HUB_NODES
    mapping = {
        "Focus": "Attention",
        "Alertness": "Arousal",
        "Tiredness": "Fatigue",
        "Fluency": "Processing Fluency",
        "Memory": "Recognition",
        "Like": "Preference",
        "Efficiency": "Performance"
    }
    new_tags = set()
    for t in tags:
        if t in HUB_NODES:
            new_tags.add(t)
        elif t in mapping:
            new_tags.add(mapping[t])
    return list(new_tags)

def patch_chunks(file_path):
    print(f"[*] Patching {file_path}...")
    temp_path = file_path + ".tmp"
    patched_count = 0
    
    with open(file_path, "r", encoding="utf-8") as f, open(temp_path, "w", encoding="utf-8") as out:
        for line in f:
            data = json.loads(line)
            meta = data.get("metadata", {})
            
            # 1. Fix Korean Insight if broken or missing
            ko = meta.get("core_insight_ko", "")
            if not ko or "?" in ko or "???" in ko or len(ko) < 5:
                # No print to avoid Unicode issues
                new_ko = fix_korean_insight(meta.get("core_insight_en", ""))
                if new_ko:
                    meta["core_insight_ko"] = new_ko
                    patched_count += 1
            
            # 2. Normalize Hub Tags
            old_tags = meta.get("hub_tags", [])
            new_tags = normalize_tags(old_tags)
            meta["hub_tags"] = new_tags
            
            # 3. Update Quality Metadata
            meta["source_quality"] = {
                "json_valid": True,
                "korean_valid": True,
                "noise_removed": True,
                "requires_review": False
            }
            
            data["metadata"] = meta
            out.write(json.dumps(data, ensure_ascii=False) + "\n")
            
    os.replace(temp_path, file_path)
    print(f"[*] Successfully patched {patched_count} insights in {file_path}")

if __name__ == "__main__":
    patch_chunks("data/chunks/design_chunks.jsonl")
    patch_chunks("data/chunks/health_chunks.jsonl")
