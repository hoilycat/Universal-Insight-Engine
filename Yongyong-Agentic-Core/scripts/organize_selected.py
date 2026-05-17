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
TARGET_DESIGN = os.path.join(TARGET_BASE, "design")
TARGET_HEALTH = os.path.join(TARGET_BASE, "health")

def find_file_recursive(base_path, target_filename):
    """하위 폴더까지 뒤져서 파일을 찾음"""
    for root, dirs, files in os.walk(base_path):
        if target_filename in files:
            return os.path.join(root, target_filename)
    return None

def organize_separately():
    for d in [TARGET_DESIGN, TARGET_HEALTH]:
        os.makedirs(d, exist_ok=True)
        
    if not os.path.exists(REPORT_PATH):
        print(f"[Error] Report not found")
        return

    with open(REPORT_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    content = content.replace(r"\_", "_")
    papers = re.findall(r"### (.*?\.pdf)\n(.*?)(?=### |$)", content, re.DOTALL)
    
    design_list = []
    health_list = []
    
    print(f"[*] Total papers in report: {len(papers)}")
    
    for filename, details in papers:
        filename = filename.strip()
        if "[KEEP]" in details:
            metrics_match = re.search(r"\*\*핵심 데이터\*\*:(.*?)(?=---|\*\*|$)", details, re.DOTALL)
            metrics_text = metrics_match.group(1).strip() if metrics_match else "N/A"
            summary_lines = [line.strip().replace("- ", "").replace("* ", "") for line in metrics_text.split("\n") if line.strip()]
            summary = " | ".join(summary_lines[:3])
            
            # 1. 디자인 폴더에서 재귀적 탐색
            design_path = find_file_recursive(SRC_DESIGN, filename)
            if design_path:
                shutil.copy2(design_path, os.path.join(TARGET_DESIGN, filename))
                design_list.append({"filename": filename, "summary": summary})
                print(f"  [DESIGN] {filename}")
                continue
            
            # 2. 건강 폴더에서 재귀적 탐색
            health_path = find_file_recursive(SRC_HEALTH, filename)
            if health_path:
                shutil.copy2(health_path, os.path.join(TARGET_HEALTH, filename))
                health_list.append({"filename": filename, "summary": summary})
                print(f"  [HEALTH] {filename}")
                continue
            
            print(f"  [NOT FOUND] {filename}")

    # 요약 맵 생성
    map_path = os.path.join(TARGET_BASE, "data_summary_map.md")
    with open(map_path, "w", encoding="utf-8") as f:
        f.write("# 🗺️ Selected Wisdom: Categorized Data Summary Map\n\n")
        f.write("## 🎨 Mood-DNA (Design Wisdom)\n")
        f.write("| No | Filename | Key Design Metrics |\n")
        f.write("|---|---|---|\n")
        for i, p in enumerate(design_list, 1):
            f.write(f"| {i} | {p['filename']} | {p['summary'].replace('|', '\\|')} |\n")
        f.write("\n---\n\n")
        f.write("## ☕ Cof/fee (Health & Caffeine Wisdom)\n")
        f.write("| No | Filename | Key Health Metrics |\n")
        f.write("|---|---|---|\n")
        for i, p in enumerate(health_list, 1):
            f.write(f"| {i} | {p['filename']} | {p['summary'].replace('|', '\\|')} |\n")
            
    print(f"\n[!] Final Task Completed.")
    print(f"  - Design: {len(design_list)} papers")
    print(f"  - Health: {len(health_list)} papers")
    print(f"  - Map: {map_path}")

if __name__ == "__main__":
    organize_separately()
