import json
import asyncio
import aiohttp
import re

DESIGN_FILE = r"C:\Users\iopuh\Universal-Insight-Engine\Yongyong-Agentic-Core\data\chunks\design_chunks.jsonl"
OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
MODEL_NAME = "gemma4:e4b"

async def generate_text(session, prompt):
    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.3, "top_p": 0.9, "num_predict": 150}
    }
    try:
        async with session.post(OLLAMA_URL, json=payload, timeout=60) as response:
            if response.status == 200:
                data = await response.json()
                return data.get("response", "").strip()
    except Exception as e:
        print(f"Error: {e}")
    return ""

def has_hangul(text):
    return any(0xAC00 <= ord(c) <= 0xD7A3 for c in text)

async def process_chunk(session, line):
    try:
        chunk = json.loads(line)
    except:
        return line
        
    meta = chunk.get("metadata", {})
    changed = False
    
    en_insight = meta.get("core_insight_en", "").strip()
    if not en_insight or en_insight == "N/A" or en_insight == "null":
        prompt_en = f"Write a concise 1-2 sentence academic summary in English based on this text:\n\n{chunk.get('text', '')[:1000]}"
        new_en = await generate_text(session, prompt_en)
        if new_en:
            meta["core_insight_en"] = new_en
            en_insight = new_en
            changed = True
            
    ko_insight = meta.get("core_insight_ko", "").strip()
    if not has_hangul(ko_insight) or "???" in ko_insight or "Please" in ko_insight:
        prompt_ko = f"Translate the following academic summary into natural, professional Korean. Output ONLY the Korean translation, keeping it concise (1-3 sentences).\n\nEnglish Summary: {en_insight}"
        new_ko = await generate_text(session, prompt_ko)
        if new_ko and has_hangul(new_ko):
            meta["core_insight_ko"] = new_ko
        else:
            meta["core_insight_ko"] = "오류 발생으로 번역할 수 없습니다."
        changed = True
        
    if changed:
        chunk["metadata"] = meta
        return json.dumps(chunk, ensure_ascii=False) + "\n"
    return line

async def main():
    with open(DESIGN_FILE, "r", encoding="utf-8-sig") as f:
        lines = f.readlines()
        
    async with aiohttp.ClientSession() as session:
        tasks = []
        for line in lines:
            if line.strip():
                tasks.append(process_chunk(session, line))
        
        # We process sequentially to avoid any timeout issues
        results = []
        for t in tasks:
            results.append(await t)
            
    with open(DESIGN_FILE, "w", encoding="utf-8-sig") as f:
        for res in results:
            f.write(res)
            
if __name__ == "__main__":
    asyncio.run(main())
