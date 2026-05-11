import os
import json
import sys
import re
import google.generativeai as genai
from dotenv import load_dotenv

# 인코딩 설정
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import time

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-flash-latest') # 더 안정적인 모델로 변경

BASE_DIR = r"c:\Users\iopuh\Universal-Insight-Engine"
CHUNKS_DIR = os.path.join(BASE_DIR, "Yongyong-Agentic-Core", "data", "chunks")

HUB_NODES = ["Attention", "Arousal", "Fatigue", "Processing Fluency", "Recognition", "Preference", "Performance"]

def refine_insight_with_gemini(filename, text_sample):
    """제미나이를 사용하여 논문의 핵심 인사이트를 깨끗한 한글/영어로 재생성"""
    prompt = f"""
    Analyze the following academic text from the paper '{filename}'.
    Extract the core quantitative metrics and design/health insights.
    Provide a concise summary in English followed by a clean Korean translation.
    Focus on variables related to: {', '.join(HUB_NODES)}
    
    Text Sample:
    {text_sample[:3000]}
    
    Return in JSON format:
    {{
        "insight_en": "Summary in English...",
        "insight_ko": "Summary in Korean...",
        "tags": ["Attention", "Arousal", ...]
    }}
    """
    try:
        response = model.generate_content(prompt)
        # JSON 추출 강화: 마크다운 코드 블록 제거 및 유연한 파싱
        text = response.text
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]
        
        json_match = re.search(r"\{.*\}", text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(0))
    except Exception as e:
        print(f"      [LLM Error] {e}")
    return None

def refine_chunks():
    files = ["design_chunks.jsonl", "health_chunks.jsonl"]
    
    for filename in files:
        path = os.path.join(CHUNKS_DIR, filename)
        if not os.path.exists(path): continue
        
        print(f"[*] Refining {filename}...")
        refined_nodes = []
        paper_insights = {} # 파일별로 한 번만 LLM 호출
        
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                try:
                    node = json.loads(line)
                    file_name = node['metadata']['file_name']
                    
                    if file_name not in paper_insights:
                        print(f"  - Generating new insight for: {file_name}")
                        new_info = refine_insight_with_gemini(file_name, node['text'])
                        if new_info:
                            paper_insights[file_name] = new_info
                        else:
                            paper_insights[file_name] = {"insight_en": "N/A", "insight_ko": "N/A", "tags": []}
                        
                        # 할당량 방지를 위해 잠시 휴식
                        time.sleep(5) 
                    
                    # 인사이트 및 태그 업데이트
                    node['metadata']['core_insight_en'] = paper_insights[file_name]['insight_en']
                    node['metadata']['core_insight_ko'] = paper_insights[file_name]['insight_ko']
                    node['metadata']['hub_tags'] = paper_insights[file_name]['tags']
                    # 기존 깨진 한글 메타데이터 삭제
                    if 'core_insight' in node['metadata']: del node['metadata']['core_insight']
                    
                    refined_nodes.append(node)
                except:
                    continue # 깨진 줄은 과감히 버림
                    
        # 다시 저장 (안전하게)
        with open(path, "w", encoding="utf-8") as f:
            for node in refined_nodes:
                f.write(json.dumps(node, ensure_ascii=False) + "\n")
                
        print(f"  [SUCCESS] {len(refined_nodes)} chunks refined in {filename}")

if __name__ == "__main__":
    refine_chunks()
