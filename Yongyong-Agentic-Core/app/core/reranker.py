# app/core/reranker.py
"""
Python reranker for GraphRAG evidence chunks.

Pipeline:
  raw_chunks (30개)
  → boost/penalty 점수 조정
  → 중복 제거 (chunk_id + insight 유사도)
  → min_score 필터
  → max_per_document 제한
  → 상위 N개 반환 (curated)
"""
from dataclasses import dataclass, field
from typing import Any

MAX_CURATED = 6       # 최종 LLM에 전달할 최대 청크 수
MIN_CURATED = 3       # 최소 확보 목표 (min_score 낮춰서라도)


@dataclass
class RerankDebug:
    intent: str
    boost_terms: list[str]
    penalty_terms: list[str]
    total_raw: int
    total_after_dedup: int
    total_after_min_score: int
    total_curated: int
    score_min: float
    score_max: float
    score_avg: float
    per_document_counts: dict[str, int] = field(default_factory=dict)


def _adjust_score(
    chunk: dict[str, Any],
    boost_terms: list[str],
    penalty_terms: list[str],
) -> float:
    """
    base_score + boost 매치 수 * 3 - penalty 매치 수 * 5
    텍스트/인사이트를 합쳐서 검사 (대소문자 무시)
    """
    text = " ".join([
        (chunk.get("text") or ""),
        (chunk.get("insight_ko") or ""),
        (chunk.get("insight_en") or ""),
        " ".join(chunk.get("tags") or []),
    ]).lower()

    base = float(chunk.get("score") or 0)
    boost_hit = sum(1 for t in boost_terms if t.lower() in text)
    penalty_hit = sum(1 for t in penalty_terms if t.lower() in text)

    return base + boost_hit * 3 - penalty_hit * 5


def _dedup(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    중복 제거:
    1) 동일 chunk_id
    2) insight_ko 앞 60자가 동일 (순차 청크 중복 필터)
    """
    seen_ids: set[str] = set()
    seen_insights: set[str] = set()
    result = []

    for chunk in chunks:
        cid = chunk.get("id") or chunk.get("chunk_id") or ""
        insight = (chunk.get("insight_ko") or "")[:60].strip()

        if cid in seen_ids:
            continue
        if insight and insight in seen_insights:
            continue

        seen_ids.add(cid)
        if insight:
            seen_insights.add(insight)
        result.append(chunk)

    return result


def rerank(
    chunks: list[dict[str, Any]],
    boost_terms: list[str],
    penalty_terms: list[str],
    min_score: int = 5,
    max_per_document: int = 3,
    intent: str = "general",
) -> tuple[list[dict[str, Any]], RerankDebug]:
    """
    chunks를 reranking해서 curated 목록과 debug 정보를 반환한다.

    Returns:
        curated: 최종 5-6개 청크 (adjusted_score 필드 추가됨)
        debug: RerankDebug 통계
    """
    if not chunks:
        return [], RerankDebug(
            intent=intent,
            boost_terms=boost_terms,
            penalty_terms=penalty_terms,
            total_raw=0,
            total_after_dedup=0,
            total_after_min_score=0,
            total_curated=0,
            score_min=0, score_max=0, score_avg=0,
        )

    total_raw = len(chunks)

    # 1. adjusted_score 계산
    for chunk in chunks:
        chunk["adjusted_score"] = _adjust_score(chunk, boost_terms, penalty_terms)

    # 2. 중복 제거 (점수 높은 순으로 정렬 후 제거해야 좋은 것이 남음)
    chunks_sorted = sorted(chunks, key=lambda c: c["adjusted_score"], reverse=True)
    deduped = _dedup(chunks_sorted)
    total_after_dedup = len(deduped)

    # 3. min_score 필터
    filtered = [c for c in deduped if c["adjusted_score"] >= min_score]
    total_after_min_score = len(filtered)

    # min_score 통과한 게 MIN_CURATED보다 적으면 기준을 낮춰서 보완
    if len(filtered) < MIN_CURATED:
        relaxed_min = max(0, min_score - 3)
        filtered = [c for c in deduped if c["adjusted_score"] >= relaxed_min]

    # 4. max_per_document 제한
    doc_counts: dict[str, int] = {}
    limited: list[dict[str, Any]] = []

    for chunk in filtered:
        doc = chunk.get("document") or "unknown"
        count = doc_counts.get(doc, 0)
        if count < max_per_document:
            doc_counts[doc] = count + 1
            limited.append(chunk)

    # 5. 상위 MAX_CURATED개만
    curated = limited[:MAX_CURATED]

    # Debug 통계
    all_scores = [c["adjusted_score"] for c in chunks]
    debug = RerankDebug(
        intent=intent,
        boost_terms=boost_terms,
        penalty_terms=penalty_terms,
        total_raw=total_raw,
        total_after_dedup=total_after_dedup,
        total_after_min_score=total_after_min_score,
        total_curated=len(curated),
        score_min=round(min(all_scores), 1),
        score_max=round(max(all_scores), 1),
        score_avg=round(sum(all_scores) / len(all_scores), 1),
        per_document_counts=doc_counts,
    )

    return curated, debug
