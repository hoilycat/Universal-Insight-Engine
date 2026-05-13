# app/core/intent_classifier.py
"""
Domain + query → intent type + boost/penalty terms.

intent는 reranker와 query expansion 양쪽에서 사용된다.
분류 방식: keyword matching (간단하고 설명 가능한 방식 우선)
"""
from dataclasses import dataclass, field
from typing import Optional

# ─────────────────────────────────────────────────────────────────────
# Intent Profile 정의
# ─────────────────────────────────────────────────────────────────────
@dataclass
class IntentProfile:
    intent: str
    boost_terms: list[str]
    penalty_terms: list[str]
    query_hints: list[str]          # query expansion에 추가될 영문 힌트
    min_score: int = 5              # reranker min_score
    max_per_document: int = 3       # reranker max chunks per document


INTENT_PROFILES: dict[str, dict[str, IntentProfile]] = {
    "coffee": {
        "mechanism_query": IntentProfile(
            intent="mechanism_query",
            boost_terms=["adenosine", "receptor", "metabolism", "pharmacology",
                         "half-life", "halflife", "caffeine", "아데노신", "수용체", "대사"],
            penalty_terms=["design", "brand", "visual", "aesthetic", "ux", "브랜드", "디자인"],
            query_hints=["adenosine", "receptor", "caffeine", "mechanism", "pharmacokinetics"],
            min_score=6,
            max_per_document=3,
        ),
        "symptom_query": IntentProfile(
            intent="symptom_query",
            boost_terms=["headache", "fatigue", "withdrawal", "insomnia", "anxiety",
                         "두통", "피로", "금단", "불면", "불안"],
            penalty_terms=["design", "brand", "visual", "브랜드", "디자인"],
            query_hints=["headache", "fatigue", "withdrawal", "sleep", "symptom"],
            min_score=5,
            max_per_document=3,
        ),
        "stats_insight": IntentProfile(
            intent="stats_insight",
            boost_terms=["pattern", "analysis", "intake", "dose", "frequency", "average",
                         "패턴", "분석", "섭취", "용량", "빈도"],
            penalty_terms=["design", "brand", "visual", "브랜드", "디자인"],
            query_hints=["caffeine", "intake", "pattern", "dose", "daily"],
            min_score=4,
            max_per_document=3,
        ),
        "recommendation": IntentProfile(
            intent="recommendation",
            boost_terms=["recommend", "optimal", "safe", "guideline", "limit",
                         "권장", "최적", "안전", "가이드라인", "한도"],
            penalty_terms=["design", "brand", "visual", "브랜드", "디자인"],
            query_hints=["caffeine", "recommend", "guideline", "safe", "limit"],
            min_score=4,
            max_per_document=3,
        ),
        "general": IntentProfile(
            intent="general",
            boost_terms=["caffeine", "coffee", "health", "카페인", "커피", "건강"],
            penalty_terms=["design", "brand", "visual", "브랜드", "디자인"],
            query_hints=["caffeine", "coffee"],
            min_score=3,
            max_per_document=4,
        ),
    },
    "design": {
        "brand_analysis": IntentProfile(
            intent="brand_analysis",
            boost_terms=["brand", "identity", "recognition", "consistency", "value",
                         "브랜드", "아이덴티티", "인식", "일관성", "가치"],
            penalty_terms=["caffeine", "sleep", "headache", "카페인", "수면", "두통"],
            query_hints=["brand", "identity", "recognition", "logo", "value"],
            min_score=6,
            max_per_document=3,
        ),
        "visual_reasoning": IntentProfile(
            intent="visual_reasoning",
            boost_terms=["visual", "attention", "perception", "color", "saliency", "contrast",
                         "시각", "주의", "인지", "색상", "현저성", "대비"],
            penalty_terms=["caffeine", "sleep", "headache", "카페인", "수면", "두통"],
            query_hints=["visual", "attention", "perception", "saliency", "color"],
            min_score=6,
            max_per_document=3,
        ),
        "critique": IntentProfile(
            intent="critique",
            boost_terms=["design", "aesthetic", "fluency", "preference", "quality", "evaluate",
                         "디자인", "미학", "유창성", "선호", "품질", "평가"],
            penalty_terms=["caffeine", "sleep", "headache", "카페인", "수면"],
            query_hints=["design", "aesthetic", "fluency", "preference", "evaluate"],
            min_score=5,
            max_per_document=3,
        ),
        "research_query": IntentProfile(
            intent="research_query",
            boost_terms=["study", "research", "experiment", "paper", "finding",
                         "연구", "실험", "논문", "결과", "발견"],
            penalty_terms=["caffeine", "sleep", "카페인", "수면"],
            query_hints=["study", "research", "design", "experiment", "finding"],
            min_score=5,
            max_per_document=2,
        ),
        "general": IntentProfile(
            intent="general",
            boost_terms=["design", "brand", "visual", "디자인", "브랜드", "시각"],
            penalty_terms=["caffeine", "sleep", "headache", "카페인", "수면", "두통"],
            query_hints=["design", "brand", "visual"],
            min_score=3,
            max_per_document=4,
        ),
    },
    "travel": {
        "packing_plan": IntentProfile(
            intent="packing_plan",
            boost_terms=["packing", "luggage", "essentials", "checklist",
                         "짐", "패킹", "필수품", "체크리스트"],
            penalty_terms=[],
            query_hints=["packing", "luggage", "travel", "essentials"],
            min_score=3,
            max_per_document=4,
        ),
        "general": IntentProfile(
            intent="general",
            boost_terms=["travel", "trip", "destination", "schedule",
                         "여행", "출장", "목적지", "일정"],
            penalty_terms=[],
            query_hints=["travel", "destination", "schedule"],
            min_score=2,
            max_per_document=5,
        ),
    },
    "integrated": {
        "cross_domain_insight": IntentProfile(
            intent="cross_domain_insight",
            boost_terms=[],
            penalty_terms=[],
            query_hints=[],
            min_score=3,
            max_per_document=5,
        ),
        "general": IntentProfile(
            intent="general",
            boost_terms=[],
            penalty_terms=[],
            query_hints=[],
            min_score=2,
            max_per_document=5,
        ),
    },
}

# ─────────────────────────────────────────────────────────────────────
# 분류 키워드 매핑
# ─────────────────────────────────────────────────────────────────────
INTENT_KEYWORDS: dict[str, dict[str, list[str]]] = {
    "coffee": {
        "mechanism_query": ["아데노신", "수용체", "반감기", "대사", "약리", "adenosine", "receptor", "metabolism", "pharmacology", "half-life"],
        "symptom_query":   ["두통", "피로", "수면", "불면", "금단", "불안", "headache", "fatigue", "sleep", "insomnia", "withdrawal", "anxiety"],
        "stats_insight":   ["패턴", "통계", "분석", "평균", "빈도", "pattern", "statistics", "analysis", "average", "frequency"],
        "recommendation":  ["권장", "추천", "안전", "최적", "한도", "recommend", "optimal", "safe", "guideline", "limit"],
    },
    "design": {
        "brand_analysis":   ["브랜드", "아이덴티티", "로고", "일관성", "brand", "identity", "logo", "consistency"],
        "visual_reasoning": ["시각", "주의", "색상", "대비", "현저성", "visual", "attention", "color", "contrast", "saliency"],
        "critique":         ["비평", "평가", "분석", "품질", "critique", "evaluate", "assess", "quality"],
        "research_query":   ["논문", "연구", "실험", "발견", "paper", "study", "research", "experiment", "finding"],
    },
    "travel": {
        "packing_plan": ["짐", "패킹", "체크리스트", "packing", "luggage", "checklist", "essentials"],
    },
    "integrated": {
        "cross_domain_insight": ["통합", "융합", "크로스", "cross", "integrated", "combined"],
    },
}


def classify(domain: str, question: str, task: Optional[str] = None) -> IntentProfile:
    """
    domain + question → IntentProfile.
    task가 명시되어 있으면 task를 우선 사용, 없으면 keyword matching.
    """
    domain_profiles = INTENT_PROFILES.get(domain, INTENT_PROFILES["integrated"])
    domain_keywords = INTENT_KEYWORDS.get(domain, {})

    # 1) task가 명시되어 있고 해당 intent가 있으면 직접 반환
    if task and task in domain_profiles:
        return domain_profiles[task]

    # 2) 질문 keyword matching
    question_lower = question.lower()
    best_intent: Optional[str] = None
    best_score = 0

    for intent_name, keywords in domain_keywords.items():
        score = sum(1 for kw in keywords if kw in question_lower)
        if score > best_score:
            best_score = score
            best_intent = intent_name

    if best_intent and best_intent in domain_profiles:
        return domain_profiles[best_intent]

    # 3) fallback: general
    return domain_profiles.get("general", IntentProfile(
        intent="general",
        boost_terms=[],
        penalty_terms=[],
        query_hints=[],
    ))
