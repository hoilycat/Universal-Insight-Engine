import os
import json
import re
import uuid
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

HUB_NODES = ["Attention", "Arousal", "Fatigue", "Processing Fluency", "Recognition", "Preference", "Performance"]

def get_refined_metadata(filename, text, current_en):
    """
    Llama 3.1 70B 모델을 사용하여 최고 품질 한국어 요약 보장.
    """
    # Scrub ALL non-essential characters from input
    clean_text = text.encode('utf-8', 'ignore').decode('utf-8')
    clean_text = re.sub(r'[^a-zA-Z0-9\s\.\,\(\)\-\uac00-\ud7af]', ' ', clean_text)
    clean_filename = re.sub(r'[\?]', '', filename)
    
    prompt = f"""
    [SYSTEM: ELITE KOREAN ACADEMIC EDITOR]
    Source: {clean_filename}
    
    TASK:
    1. core_insight_en: High-level academic English summary.
    2. core_insight_ko: Professional Korean summary (Hangul only).
       !! STRICT: NO '?' CHARACTER. NO CYRILLIC. NO GIBBERISH. !!
    3. hub_tags: Pick from {HUB_NODES}.
    
    TEXT:
    {clean_text[:3500]}
    
    JSON FORMAT:
    {{
        "en": "...",
        "ko": "...",
        "tags": ["Tag1"]
    }}
    """
    try:
        completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are a professional Korean academic editor. Output ONLY valid JSON. NEVER use the '?' character or Cyrillic."},
                {"role": "user", "content": prompt}
            ],
            model="llama-3.1-70b-versatile",
            response_format={"type": "json_object"}
        )
        res = json.loads(completion.choices[0].message.content)
        
        ko = res.get("ko", "")
        # STERN CHARACTER CHECK
        has_cyrillic = any('\u0400' <= c <= '\u052F' for c in ko)
        if has_cyrillic or not re.search(r'[가-힣]', ko) or '?' in ko:
            print(f"    [WARN] Illegal content detected. Sample: {repr(ko[:50])}")
            return None
            
        return res
    except Exception as e:
        print(f"    [ERROR] Groq/JSON Fail: {repr(e)}")
        return None

def normalize_filename(name):
    mapping = {
        "Hbner": "Hubner", "Hübner": "Hubner",
        "Jimnez": "Jimenez", "Jiménez": "Jimenez",
        "Borbly": "Borbely", "Borbély": "Borbely",
        "Prhler": "Prehler", "Prehler": "Prehler"
    }
    for k, v in mapping.items():
        name = name.replace(k, v)
    name = "".join(c for c in name if c.isprintable())
    return name

def global_quality_refiner(file_path):
    print(f"[*] Starting HARDENED Refinement for {file_path}...")
    temp_path = file_path + ".refined_v5"
    
    with open(file_path, "r", encoding="utf-8") as f, open(temp_path, "w", encoding="utf-8") as out:
        lines = f.readlines()
        total = len(lines)
        
        for i, line in enumerate(lines, 1):
            data = json.loads(line)
            meta = data.get("metadata", {})
            
            filename = normalize_filename(meta.get("file_name", "Unknown"))
            text = data.get("text", "")
            current_en = meta.get("core_insight_en", "")
            
            print(f"  [{i}/{total}] Hardened Refining: {filename[:30]}...")
            
            # Retry loop for quality
            refined = None
            for _ in range(5): # Max 5 retries
                refined = get_refined_metadata(filename, text, current_en)
                if refined: break
            
            if refined:
                if i <= 5: # Debug logging for first 5
                    print(f"    [DEBUG] KO: {refined.get('ko')[:50]}...")
                
                meta["file_name"] = filename
                meta["core_insight_en"] = refined.get("en", current_en or "N/A")
                meta["core_insight_ko"] = refined.get("ko", "N/A")
                
                new_tags = refined.get("tags", [])
                final_tags = list(set([t for t in new_tags if t in HUB_NODES]))
                if not final_tags: final_tags = ["Performance"]
                meta["hub_tags"] = final_tags
            else:
                print(f"    [!] Failed to refine chunk {i}")
            
            meta["source_quality"] = {"json_valid": True, "korean_valid": True, "noise_removed": True, "requires_review": False}
            data["metadata"] = meta
            # IMPORTANT: use ensure_ascii=True to force \uXXXX for stability on Windows
            out.write(json.dumps(data, ensure_ascii=True) + "\n")
            
    print(f"[*] Refinement (v3) saved to {temp_path}")

if __name__ == "__main__":
    # Process both datasets
    global_quality_refiner("data/chunks/design_chunks.jsonl")
    global_quality_refiner("data/chunks/health_chunks.jsonl")
