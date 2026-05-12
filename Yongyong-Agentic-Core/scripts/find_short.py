import json

def find_issues(file_path, prefix):
    with open(file_path, 'r', encoding='utf-8-sig') as f:
        for i, line in enumerate(f):
            if not line.strip(): continue
            chunk = json.loads(line)
            ko = chunk.get("metadata", {}).get("core_insight_ko", "")
            # Check if it's less than 20 characters
            if len(ko) < 20:
                print(f"{prefix}:{i+1}: len={len(ko)} : {ko}")

print("--- DESIGN ---")
find_issues(r"C:\Users\iopuh\Universal-Insight-Engine\Yongyong-Agentic-Core\data\chunks\design_chunks.jsonl", "design")
print("--- HEALTH ---")
find_issues(r"C:\Users\iopuh\Universal-Insight-Engine\Yongyong-Agentic-Core\data\chunks\health_chunks.jsonl", "health")
