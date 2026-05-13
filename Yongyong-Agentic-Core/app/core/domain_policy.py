# app/core/domain_policy.py
"""
도메인 정책 정의.
- search 단계에서는 넓게 탐색
- LLM 프롬프트/응답 단계에서 도메인 언어 경계 적용 (출력 정책 필터)
"""
from typing import Optional

POLICIES: dict[str, dict] = {
    "coffee": {
        # Neo4j 도메인 필터 (c.domain)
        "neo4j_domain": "health",
        # 검색 키워드 확장용 힌트 (선택적)
        "search_hints": ["caffeine", "sleep", "fatigue", "headache", "alertness", "focus"],
        # 출력 단계 금지 주제 — 응답에 이 단어가 노출되면 안 됨
        "output_forbidden": ["디자인", "브랜드 아이덴티티", "시각 처리", "UX", "brand identity"],
        # 허용 주제 (프롬프트에 명시)
        "allowed_topics": [
            "카페인", "수면", "두통", "피로", "집중력", "각성",
            "caffeine", "sleep", "fatigue", "headache", "alertness", "focus",
        ],
        "prompt_tone": (
            "건강 데이터 기반의 과학적이고 실용적인 언어로 답하세요. "
            "카페인, 수면, 피로, 집중력, 두통 등 건강/인지 주제만 다루세요."
        ),
        "task_types": [
            "stats_insight", "pattern_analysis",
            "symptom_correlation", "recommendation",
        ],
        "response_language": "ko",
    },
    "design": {
        "neo4j_domain": "design",
        "search_hints": ["brand", "visual", "design", "aesthetic", "attention", "preference"],
        "output_forbidden": ["카페인", "두통", "수면 장애", "caffeine", "headache", "sleep disorder"],
        "allowed_topics": [
            "디자인", "브랜드", "시각", "주의", "선호", "처리 유창성",
            "design", "brand", "visual", "attention", "preference", "fluency",
        ],
        "prompt_tone": (
            "디자인 전략 및 브랜드 컨설팅 언어로 답하세요. "
            "시각 인지, 브랜드 가치, 디자인 지표에 집중하세요."
        ),
        "task_types": ["critique", "brand_analysis", "visual_reasoning", "recommendation"],
        "response_language": "ko",
    },
    "travel": {
        "neo4j_domain": None,  # 아직 여행 전용 청크 없음 → 전체 KB 탐색
        "search_hints": ["travel", "packing", "schedule", "fatigue", "destination"],
        "output_forbidden": [],
        "allowed_topics": [
            "여행", "짐", "동선", "피로", "일정", "준비물",
            "travel", "packing", "schedule", "fatigue", "destination",
        ],
        "prompt_tone": (
            "여행 계획 및 경험 최적화 언어로 답하세요. "
            "짐, 동선, 피로 관리, 일정 최적화에 집중하세요."
        ),
        "task_types": ["packing_plan", "schedule_optimize", "destination_brief"],
        "response_language": "ko",
    },
    "integrated": {
        "neo4j_domain": None,  # 전체 KB 탐색 (내부 리서치용)
        "search_hints": [],
        "output_forbidden": [],
        "allowed_topics": [],
        "prompt_tone": "학술 연구 통합 분석 언어로 답하세요. 도메인 경계 없이 통합적으로 분석하세요.",
        "task_types": ["cross_domain_insight", "research_synthesis"],
        "response_language": "ko",
    },
}


def get_policy(domain: str) -> dict:
    """도메인 정책 반환. 알 수 없는 도메인은 integrated로 fallback."""
    return POLICIES.get(domain, POLICIES["integrated"])


def build_domain_prompt_header(domain: str, task: str, question: str) -> str:
    """도메인+태스크 기반 LLM 프롬프트 헤더 생성."""
    policy = get_policy(domain)
    tone = policy["prompt_tone"]
    allowed = ", ".join(policy["allowed_topics"]) if policy["allowed_topics"] else "제한 없음"
    forbidden = ", ".join(policy["output_forbidden"]) if policy["output_forbidden"] else "없음"

    return f"""당신은 Yongyong Agentic Core입니다. 도메인: [{domain.upper()}] / 태스크: [{task}]

[도메인 정책]
- 답변 톤: {tone}
- 허용 주제: {allowed}
- 응답 금지 주제: {forbidden} (근거로 사용은 가능하나 직접 언급 금지)

[반드시 지킬 규칙]
1. 환각 금지: 컨텍스트에 없는 논문/수치/사실을 절대 만들어내지 마세요.
2. 언어: 반드시 전문적인 한국어로 답하세요.
3. 형식: 아래 세 섹션을 반드시 사용하세요.

### [요약]
질문에 대한 핵심 답변 (2-3문장)

### [관련 근거]
사용한 출처 목록
- **논문명**: `문서명`
  - **핵심 내용**: (청크 인사이트)
  - **Chunk ID**: `chunk_id`

### [실무 적용]
실제 적용 가능한 인사이트 1-2개

[사용자 질문]
{question}
"""
