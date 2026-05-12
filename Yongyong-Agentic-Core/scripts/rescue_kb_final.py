import json
import asyncio
import aiohttp
from pathlib import Path

ROOT_DIR = Path(r"C:\Users\iopuh\Universal-Insight-Engine")
DESIGN_FILE = ROOT_DIR / "Yongyong-Agentic-Core" / "data" / "chunks" / "design_chunks.jsonl"
HEALTH_FILE = ROOT_DIR / "Yongyong-Agentic-Core" / "data" / "chunks" / "health_chunks.jsonl"
OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
MODEL_NAME = "exaone3.5:latest"

async def generate_text(session, prompt):
    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.3}
    }
    try:
        async with session.post(OLLAMA_URL, json=payload, timeout=120) as response:
            if response.status == 200:
                data = await response.json()
                return data.get("response", "").strip()
    except Exception as e:
        print(f"Error: {e}")
    return ""

def is_valid_korean(text):
    return any(0xAC00 <= ord(c) <= 0xD7A3 for c in text)

async def process_chunk(session, semaphore, line):
    async with semaphore:
        try:
            chunk = json.loads(line)
        except Exception:
            return line
            
        meta = chunk.get("metadata", {})
        
        # 1. Handle missing/generic core_insight_en
        en_insight = meta.get("core_insight_en", "").strip()
        is_generic_en = "This study explores the influence of design elements on user perception" in en_insight
        
        if not en_insight or en_insight == "N/A" or en_insight == "null" or is_generic_en:
            prompt_en = f"Write a concise 1-2 sentence academic summary in English based on this text:\n\n{chunk.get('text', '')[:1500]}"
            new_en = await generate_text(session, prompt_en)
            if new_en:
                meta["core_insight_en"] = new_en
                en_insight = new_en
                
        # 2. Handle core_insight_ko
        ko_insight = meta.get("core_insight_ko", "").strip()
        is_generic_ko = "오류 발생으로 번역할 수 없습니다" in ko_insight or "본 연구는 디자인 요소가 사용자 인식과" in ko_insight or "???" in ko_insight
        
        if not is_valid_korean(ko_insight) or is_generic_ko:
            prompt_ko = f"Translate the following academic summary into natural, professional Korean. Output ONLY the Korean translation, keeping it concise (1-3 sentences).\n\nEnglish Summary: {en_insight}"
            new_ko = await generate_text(session, prompt_ko)
            if new_ko and is_valid_korean(new_ko):
                meta["core_insight_ko"] = new_ko
                meta["source_quality"]["korean_valid"] = True
            else:
                meta["source_quality"]["korean_valid"] = False
        else:
            meta["source_quality"]["korean_valid"] = True
            
        chunk["metadata"] = meta
        return json.dumps(chunk, ensure_ascii=False) + "\n"

async def process_file(file_path):
    print(f"Loading {file_path.name}...")
    with open(file_path, "r", encoding="utf-8-sig") as f:
        lines = [line for line in f if line.strip()]
        
    async with aiohttp.ClientSession() as session:
        semaphore = asyncio.Semaphore(2) # Limit concurrency so EXAONE doesn't overheat
        tasks = []
        for line in lines:
            tasks.append(process_chunk(session, semaphore, line))
            
        print(f"Processing {len(tasks)} chunks in {file_path.name}...")
        results = []
        for i, task in enumerate(asyncio.as_completed(tasks)):
            res = await task
            results.append(res)
            if (i+1) % 50 == 0:
                print(f"Completed {i+1}/{len(tasks)} in {file_path.name}")
                
        # Write back results properly ordered? No, as_completed returns out of order.
        # So we should use asyncio.gather to keep order
        
    # Let's re-do with gather to preserve order
    async with aiohttp.ClientSession() as session:
        semaphore = asyncio.Semaphore(3)
        print(f"Processing {len(lines)} chunks in {file_path.name} sequentially/batched...")
        tasks = [process_chunk(session, semaphore, line) for line in lines]
        results = await asyncio.gather(*tasks)
            
    with open(file_path, "w", encoding="utf-8-sig") as f:
        for res in results:
            f.write(res)
            
    print(f"Finished {file_path.name}!")

async def main():
    await process_file(DESIGN_FILE)
    await process_file(HEALTH_FILE)
    print("All datasets completed!")

if __name__ == "__main__":
    asyncio.run(main())
