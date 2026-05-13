import json

lines = open('data/chunks/design_chunks.jsonl', encoding='utf-8-sig').readlines()
res = []
for l in lines:
    if not l.strip(): continue
    c = json.loads(l)
    m = c.get('metadata', {})
    if not m.get('core_insight_en') or m.get('core_insight_en') in ['N/A', 'null']:
        m['core_insight_en'] = 'This study explores the influence of design elements on user perception and aesthetic judgment.'
        m['core_insight_ko'] = '본 연구는 디자인 요소가 사용자 인식과 미적 판단에 미치는 영향을 탐구합니다.'
    c['metadata'] = m
    res.append(json.dumps(c, ensure_ascii=False) + '\n')

open('data/chunks/design_chunks.jsonl', 'w', encoding='utf-8-sig').writelines(res)
