import os
import re
import shutil
import sys

if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE_DIR = r"c:\Users\iopuh\Universal-Insight-Engine"
REPORT_PATH = os.path.join(BASE_DIR, "Yongyong-Agentic-Core", "screening_report.md")

SRC_DESIGN = os.path.join(BASE_DIR, "Yongyong-Agentic-Core", "data", "design_wisdom")
SRC_HEALTH = os.path.join(BASE_DIR, "Yongyong-Agentic-Core", "data", "health_wisdom")

TARGET_BASE = os.path.join(BASE_DIR, "data", "selected_wisdom")
# 보조 자료용 폴더 추가
TARGET_SUPP_DESIGN = os.path.join(TARGET_BASE, "design", "supplementary")
TARGET_SUPP_HEALTH = os.path.join(TARGET_BASE, "health", "supplementary")

def find_file_recursive(base_path, target_filename):
    for root, dirs, files in os.walk(base_path):
        if target_filename in files:
            return os.path.join(root, target_filename)
    return None

def rescue_operation():
    os.makedirs(TARGET_SUPP_DESIGN, exist_ok=True)
    os.makedirs(TARGET_SUPP_HEALTH, exist_ok=True)
        
    if not os.path.exists(REPORT_PATH):
        print(f"[Error] Report not found")
        return

    with open(REPORT_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    content = content.replace(r"\_", "_")
    papers = re.findall(r"### (.*?\.pdf)\n(.*?)(?=### |$)", content, re.DOTALL)
    
    rescued_design = []
    rescued_health = []
    
    print(f"[*] Rescuing [PASS] papers...")
    
    for filename, details in papers:
        filename = filename.strip()
        # [PASS] 논문 구제!
        if "[PASS]" in details:
            # 평가 내용 요약
            eval_match = re.search(r"\*(.*?)\*", details) # 소괄호나 별표 사이의 평가 내용 추출 시도
            eval_text = eval_match.group(1).strip() if eval_match else "Conceptually useful (Pass-Rescue)"
            
            # 1. 디자인 폴더에서 탐색
            design_path = find_file_recursive(SRC_DESIGN, filename)
            if design_path:
                shutil.copy2(design_path, os.path.join(TARGET_SUPP_DESIGN, filename))
                rescued_design.append({"filename": filename, "eval": eval_text})
                print(f"  [RESCUE-DESIGN] {filename}")
                continue
            
            # 2. 건강 폴더에서 탐색
            health_path = find_file_recursive(SRC_HEALTH, filename)
            if health_path:
                shutil.copy2(health_path, os.path.join(TARGET_SUPP_HEALTH, filename))
                rescued_health.append({"filename": filename, "eval": eval_text})
                print(f"  [RESCUE-HEALTH] {filename}")
                continue

    # 요약 맵 업데이트 (기존 맵에 추가)
    map_path = os.path.join(TARGET_BASE, "data_summary_map.md")
    with open(map_path, "a", encoding="utf-8") as f:
        f.write("\n\n## 📚 Supplementary Wisdom (Rescued Papers)\n")
        f.write("이 섹션은 직접적인 수치 모델링은 어렵지만, 개념적 설계 및 사용자 심리 이해에 도움을 줄 수 있는 보조 자료들입니다.\n\n")
        
        f.write("### 🎨 Rescued Design Papers\n")
        f.write("| No | Filename | Evaluator's Note |\n")
        f.write("|---|---|---|\n")
        for i, p in enumerate(rescued_design, 1):
            f.write(f"| {i} | {p['filename']} | {p['eval']} |\n")
            
        f.write("\n### ☕ Rescued Health Papers\n")
        f.write("| No | Filename | Evaluator's Note |\n")
        f.write("|---|---|---|\n")
        for i, p in enumerate(rescued_health, 1):
            f.write(f"| {i} | {p['filename']} | {p['eval']} |\n")
            
    print(f"\n[!] Rescue Completed.")
    print(f"  - Rescued Design: {len(rescued_design)} papers")
    print(f"  - Rescued Health: {len(rescued_health)} papers")

if __name__ == "__main__":
    rescue_operation()
