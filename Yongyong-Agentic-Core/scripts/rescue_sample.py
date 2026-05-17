import json
import asyncio
import aiohttp
from pathlib import Path
import os
from dotenv import load_dotenv

ROOT_DIR = Path(r"C:\Users\iopuh\Universal-Insight-Engine")
load_dotenv(ROOT_DIR / ".env")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

DESIGN_FILE = ROOT_DIR / "Yongyong-Agentic-Core" / "data" / "chunks" / "design_chunks.jsonl"
SAMPLE_OUTPUT_FILE = ROOT_DIR / "Yongyong-Agentic-Core" / "data" / "chunks" / "gemini_sample_20.json"

async def generate_gemini(session, prompt):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.3}
    }
    try:
        async with session.post(url, json=payload, timeout=30) as response:
            if response.status == 200:
                data = await response.json()
                try:
                    return data["candidates"][0]["content"]["parts"][0]["text"].strip()
                except (KeyError, IndexError):
                    return ""
            else:
                text = await response.text()
                print(f"Gemini API Error {response.status}: {text}")
                return ""
    except Exception as e:
        print(f"Request Error: {e}")
        return ""

async def main():
    if not GEMINI_API_KEY:
        print("Error: GEMINI_API_KEY not found in .env")
        return
        
    with open(DESIGN_FILE, "r", encoding="utf-8-sig") as f:
        lines = [line for line in f if line.strip()][:20]
        
    print(f"Loaded {len(lines)} chunks for sampling.")
    
    async with aiohttp.ClientSession() as session:
        results = []
        for i, line in enumerate(lines):
            chunk = json.loads(line)
            en_insight = chunk["metadata"].get("core_insight_en", "")
            if not en_insight or en_insight == "N/A":
                en_insight = chunk["text"][:1000] # Fallback if missing
                
            prompt = f"Translate the following academic summary into natural, professional Korean. Output ONLY the Korean translation, without quotes, keeping it concise (1-3 sentences).\n\nText to translate:\n{en_insight}"
            print(f"Processing sample {i+1}/20...")
            ko_insight = await generate_gemini(session, prompt)
            
            results.append({
                "id": chunk.get("id"),
                "file_name": chunk["metadata"]["file_name"],
                "core_insight_en": en_insight,
                "core_insight_ko_generated": ko_insight
            })
            
    with open(SAMPLE_OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
        
    print("Done! Saved to gemini_sample_20.json")

if __name__ == "__main__":
    asyncio.run(main())
