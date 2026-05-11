import json, sys
sys.stdout = __import__('io').TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def review(path, label, n=5):
    print(f"\n{'='*60}")
    print(f"[{label}] REVIEW - First {n} chunks")
    print('='*60)
    with open(path, encoding='utf-8', errors='ignore') as f:
        for i, line in enumerate(f):
            if i >= n: break
            d = json.loads(line)
            meta = d['metadata']
            text = d['text']
            print(f"\n--- Chunk {i+1} ---")
            print(f"File      : {meta['file_name']}")
            print(f"Project   : {meta['project']}")
            print(f"Category  : {meta['category']}")
            print(f"Insight   : {str(meta['core_insight'])[:120]}")
            print(f"Text(300) : {text[:300]}")
            # 품질 판단
            has_garbage = any(x in text for x in ['%PDF', 'endobj', 'stream\n', 'obj\n<<'])
            alpha_ratio = sum(c.isalpha() for c in text) / max(len(text), 1)
            print(f"[QA] Garbage: {has_garbage} | Alpha ratio: {alpha_ratio:.2%}")

# 디자인 5개
review(r'Yongyong-Agentic-Core/data/chunks/design_chunks.jsonl', 'DESIGN')
# 건강 5개
review(r'Yongyong-Agentic-Core/data/chunks/health_chunks.jsonl', 'HEALTH')

# 전체 통계
for path, label in [
    (r'Yongyong-Agentic-Core/data/chunks/design_chunks.jsonl', 'DESIGN'),
    (r'Yongyong-Agentic-Core/data/chunks/health_chunks.jsonl', 'HEALTH')
]:
    total = garbage = short = 0
    with open(path, encoding='utf-8', errors='ignore') as f:
        for line in f:
            d = json.loads(line)
            text = d['text']
            total += 1
            if any(x in text for x in ['%PDF', 'endobj', 'stream\n']):
                garbage += 1
            if len(text) < 100:
                short += 1
    print(f"\n[{label}] Total: {total} | Garbage: {garbage} ({garbage/total:.1%}) | Too Short: {short} ({short/total:.1%})")
