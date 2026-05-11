import json
import os

def merge_chunks(original_path, refined_path, output_path, expected_count):
    print(f"[*] Merging {original_path} and {refined_path} -> {output_path}")
    
    refined_data = []
    if os.path.exists(refined_path):
        with open(refined_path, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    refined_data.append(json.loads(line))
                except:
                    pass
    
    refined_ids = {d["id"] for d in refined_data}
    print(f"    [+] Loaded {len(refined_data)} refined chunks.")
    
    merged_data = list(refined_data)
    
    with open(original_path, "r", encoding="utf-8") as f:
        for line in f:
            d = json.loads(line)
            if d["id"] not in refined_ids:
                merged_data.append(d)
                
    print(f"    [+] Total merged chunks: {len(merged_data)}")
    
    if len(merged_data) != expected_count:
        print(f"    [!] Warning: Count mismatch! Expected {expected_count}, got {len(merged_data)}")
    
    with open(output_path, "w", encoding="utf-8") as out:
        for d in merged_data:
            out.write(json.dumps(d, ensure_ascii=False) + "\n")
    
    print(f"DONE: Successfully merged to {output_path}")

if __name__ == "__main__":
    # Design chunks
    merge_chunks(
        "data/chunks/design_chunks.jsonl",
        "data/chunks/design_chunks.jsonl.refined_v4",
        "data/chunks/design_chunks_final.jsonl",
        1043
    )
    # Health chunks (Already complete in v3, but use merge for consistency check)
    merge_chunks(
        "data/chunks/health_chunks.jsonl",
        "data/chunks/health_chunks.jsonl.refined_v3",
        "data/chunks/health_chunks_final.jsonl",
        331
    )
