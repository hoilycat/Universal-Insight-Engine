import os
import re
import sys
import io
import requests
import json
from pypdf import PdfReader

# 윈도우 터미널 인코딩 문제 해결
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "gemma4:e4b"

def extract_pdf_content(file_path):
    """PDF의 주요 섹션(약 5페이지)에서 텍스트를 추출합니다."""
    try:
        reader = PdfReader(file_path)
        text = ""
        # 앞부분 5페이지를 읽어 초록, 도입, 실험 결과 수집
        for i in range(min(5, len(reader.pages))):
            page_text = reader.pages[i].extract_text()
            if page_text:
                text += page_text + "\n"
        return text[:8000] # 분석에 무리가 없는 수준의 길이
    except Exception as e:
        print(f"  [ERROR] PDF 읽기 실패: {e}")
        return None

def analyze_paper(text, file_name):
    """AI에게 논문의 가치를 정밀하게 묻습니다."""
    domain = "디자인/심리학" if "design" in file_name.lower() or "mood" in file_name.lower() else "건강/카페인/대사"
    
    prompt = f"""
    당신은 'Universal Insight Engine' 프로젝트의 수석 연구원입니다.
    다음 논문 텍스트를 읽고, 우리 앱의 알고리즘에 직접적으로 활용할 수 있는 '수치적 근거'나 '핵심 인사이트'를 추출하세요.

    분야: {domain}
    
    [참고: 우리가 찾는 핵심 지표]
    - 디자인: 시각적 복잡도, 채도, 밝기, 대칭성, 여백 비율, 대비, 구도(삼분할)
    - 커피/건강: 카페인 반감기, 수분 희석 효과, 수면 지연 시간, 금단 두통 주점, 대사 속도 영향 요소

    [응답 형식 (Markdown)]
    ### {file_name}
    - **적합성 점수**: (0~10점)
    - **선별 결과**: [KEEP] 또는 [PASS]
    - **핵심 데이터**: (예: "채도가 70% 이상일 때 각성 효과가 20% 증가함"과 같은 구체적 수치)
    - **숨겨진 보물**: (논문 깊숙한 곳에서 발견한 의외의 통찰이나 연결 고리)
    - **활용 방안**: (우리 앱의 어떤 코드/기능에 적용하면 좋을지)

    텍스트 내용:
    {text}
    """
    
    try:
        payload = {
            "model": MODEL_NAME,
            "prompt": prompt,
            "stream": False
        }
        response = requests.post(OLLAMA_URL, json=payload, timeout=180)
        if response.status_code == 200:
            return response.json().get("response", "분석 결과 없음")
        else:
            return f"오류: Ollama 응답 실패 ({response.status_code})"
    except Exception as e:
        return f"분석 중 예외 발생: {e}"

def run_screener():
    base_path = os.getcwd()
    target_dirs = [
        os.path.join(base_path, "data", "design_wisdom"),
        os.path.join(base_path, "data", "health_wisdom")
    ]
    
    report_path = os.path.join(base_path, "screening_report.md")
    
    print(f"--- 딥 스캔 시작 (모델: {MODEL_NAME}) ---")
    
    with open(report_path, "w", encoding="utf-8") as report:
        report.write("# 📑 AI 논문 정밀 선별 보고서 (Deep Scan)\n")
        report.write(f"생성 일시: {os.popen('date /t').read().strip()}\n")
        report.write(f"분석 모델: {MODEL_NAME}\n\n")
        report.write("--- \n\n")
        report.flush()
        
        for d_path in target_dirs:
            if not os.path.exists(d_path): continue
            
            dir_name = os.path.basename(d_path)
            report.write(f"## 📁 디렉토리: {dir_name}\n\n")
            
            for root, dirs, files in os.walk(d_path):
                for file in files:
                    if file.lower().endswith(".pdf"):
                        print(f"Deep Scanning: {file}...")
                        file_path = os.path.join(root, file)
                        
                        content = extract_pdf_content(file_path)
                        if content:
                            analysis = analyze_paper(content, file)
                            report.write(analysis + "\n\n---\n\n")
                            report.flush() # 실시간 저장
                        else:
                            report.write(f"### {file}\n- **오류**: PDF 내용을 읽을 수 없습니다.\n\n---\n\n")

if __name__ == "__main__":
    run_screener()
