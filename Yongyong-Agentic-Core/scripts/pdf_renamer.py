import os
import re
import sys
import io
import requests
from pypdf import PdfReader

# 윈도우 터미널 인코딩 문제 해결
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Ollama 설정
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "gemma4:e4b" # 사용자 로컬 모델

def extract_pdf_info(file_path):
    """PDF의 첫 2페이지에서 텍스트를 추출합니다."""
    try:
        reader = PdfReader(file_path)
        text = ""
        for i in range(min(2, len(reader.pages))):
            page_text = reader.pages[i].extract_text()
            if page_text:
                text += page_text + "\n"
        return text[:3000]
    except Exception as e:
        print(f"  [ERROR] PDF 읽기 실패 ({os.path.basename(file_path)}): {e}")
        return None

def get_new_filename(text, original_name):
    """로컬 Ollama(Gemma)를 통해 새 파일명을 생성합니다."""
    prompt = f"""
    Analyze the following text from a PDF document and suggest a standardized English filename.
    Format: [YYYY]Title_In_English(Author).pdf
    
    Rules:
    1. YYYY: The year of publication. If unknown, use "0000".
    2. Title: A concise English title. Use underscores (_) instead of spaces. Max 5-7 words.
    3. Author: The last name of the first author.
    4. If the text is in Korean, translate the title and author name into English.
    5. Output ONLY the filename string. No quotes, no markdown, no explanation.
    
    Text snippet:
    {text}
    
    Original Filename: {original_name}
    """
    
    try:
        payload = {
            "model": MODEL_NAME,
            "prompt": prompt,
            "stream": False
        }
        response = requests.post(OLLAMA_URL, json=payload, timeout=60)
        if response.status_code == 200:
            new_name = response.json().get("response", "").strip()
            # 따옴표 및 특수문자 제거
            new_name = re.sub(r'[`"\' ]', '', new_name)
            if not new_name.lower().endswith('.pdf'):
                new_name += '.pdf'
            return new_name
        else:
            print(f"  [ERROR] Ollama 응답 오류: {response.status_code}")
            return original_name
    except Exception as e:
        print(f"  [ERROR] Ollama 요청 실패: {e}")
        return original_name

def process_directory(target_dir, dry_run=True):
    """디렉토리 내의 PDF 파일들을 처리합니다."""
    print(f"\n--- Scanning: {target_dir} ---")
    for root, dirs, files in os.walk(target_dir):
        for file in files:
            if file.lower().endswith(".pdf"):
                if re.match(r'^\[\d{4}\]', file):
                    continue
                
                file_path = os.path.join(root, file)
                print(f"Analyzing: {file}...")
                
                text = extract_pdf_info(file_path)
                if text:
                    new_name = get_new_filename(text, file)
                    # 파일 시스템 안전 문자만 남기기
                    new_name = "".join([c for c in new_name if c.isalnum() or c in "[]_().- "]).strip()
                    
                    if file != new_name:
                        print(f"  [SUGGESTION] {file} -> {new_name}")
                        if not dry_run:
                            try:
                                new_path = os.path.join(root, new_name)
                                if os.path.exists(new_path):
                                    new_name = "COPY_" + new_name
                                    new_path = os.path.join(root, new_name)
                                os.rename(file_path, new_path)
                                print(f"  [DONE] Renamed successfully.")
                            except Exception as e:
                                print(f"  [ERROR] Rename failed: {e}")
                    else:
                        print(f"  [KEEP] Name is fine.")

if __name__ == "__main__":
    base_path = os.getcwd()
    target_paths = [
        os.path.join(base_path, "data", "design_wisdom"),
        os.path.join(base_path, "data", "health_wisdom")
    ]
    
    is_dry_run = "execute" not in sys.argv
    mode_text = "EXECUTION" if not is_dry_run else "DRY RUN"
    print(f"--- {mode_text} MODE (Using Local Ollama: {MODEL_NAME}) ---")
    
    for path in target_paths:
        if os.path.exists(path):
            process_directory(path, dry_run=is_dry_run)
            
    print(f"\n--- {mode_text} Finished ---")
