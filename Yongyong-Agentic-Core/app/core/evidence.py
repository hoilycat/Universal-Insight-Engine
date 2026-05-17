# app/core/evidence.py
"""
Domain-filtered wide search (30개) + intent-aware query expansion.
graph expansion은 wide_search에서 제거 → reranker 후 context enrichment만 수행.
"""
import os
import re
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv
from neo4j import GraphDatabase

from app.core import intent_classifier as ic
from app.core import reranker as rr

CORE_DIR = Path(__file__).resolve().parents[2]
ROOT_DIR = CORE_DIR.parent

load_dotenv(ROOT_DIR / ".env")
load_dotenv(CORE_DIR / ".env", override=True)

NEO4J_URI      = os.getenv("NEO4J_URI", "neo4j://127.0.0.1:7687")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "yongyong1234")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")

# ── 검색 상수 ──────────────────────────────────────────────────────────
MAX_RAW          = 30   # Neo4j 1차 wide search 개수
MAX_CONTEXT_CHARS = 6000

# ── 기본 용어 확장 (domain-agnostic) ─────────────────────────────────
BASE_TERM_EXPANSIONS: dict[str, list[str]] = {
    "브랜드":  ["brand", "branding", "brand recognition", "brand preference"],
    "디자인":  ["design", "visual", "aesthetic", "layout"],
    "논문":    ["paper", "study", "research", "article"],
    "연구":    ["study", "research", "experiment"],
    "주의":    ["attention", "visual attention", "attentional"],
    "피로":    ["fatigue", "tiredness", "sleep"],
    "각성":    ["arousal", "alertness", "stimulation"],
    "선호":    ["preference", "liking"],
    "기억":    ["memory", "recognition", "recall"],
    "카페인":  ["caffeine", "coffee", "adenosine"],
    "수면":    ["sleep", "insomnia", "circadian"],
    "집중력":  ["focus", "concentration", "attention"],
    "두통":    ["headache", "migraine", "pain"],
    "아데노신": ["adenosine", "receptor", "purine"],
}


def _driver():
    return GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))


def _expand_terms(question: str, extra_hints: list[str] | None = None) -> list[str]:
    """Base expansion + intent query_hints 합산."""
    raw_terms = re.findall(
        r"[A-Za-z0-9\uac00-\ud7a3][A-Za-z0-9\uac00-\ud7a3_-]{1,}",
        question.lower()
    )
    terms = set(raw_terms)

    for key, expansions in BASE_TERM_EXPANSIONS.items():
        if key in question:
            terms.update(t.lower() for t in expansions)

    if extra_hints:
        terms.update(h.lower() for h in extra_hints)

    return sorted(terms)


def _build_search_cypher(domain_filter: Optional[str]) -> str:
    domain_clause = "WHERE c.domain = $domain" if domain_filter else ""
    return f"""
    MATCH (d:Document)-[:CONTAINS]->(c:Chunk)
    OPTIONAL MATCH (c)-[:HAS_TAG]->(t:Tag)
    WITH d, c, collect(DISTINCT t.name) AS tags
    {domain_clause}
    WITH d, c, tags,
         reduce(score = 0, term IN $terms |
            score
            + CASE WHEN toLower(coalesce(c.text, '')) CONTAINS term THEN 3 ELSE 0 END
            + CASE WHEN toLower(coalesce(c.core_insight_en, '')) CONTAINS term THEN 5 ELSE 0 END
            + CASE WHEN toLower(coalesce(c.core_insight_ko, '')) CONTAINS term THEN 5 ELSE 0 END
            + CASE WHEN toLower(coalesce(d.name, '')) CONTAINS term THEN 4 ELSE 0 END
            + CASE WHEN any(tag IN tags WHERE toLower(tag) CONTAINS term) THEN 4 ELSE 0 END
         ) AS score
    WHERE score > 0
    RETURN
        c.id          AS id,
        d.name        AS document,
        c.text        AS text,
        c.core_insight_en AS insight_en,
        c.core_insight_ko AS insight_ko,
        c.domain      AS domain,
        tags          AS tags,
        score         AS score
    ORDER BY score DESC
    LIMIT $limit
    """


def wide_search(
    question: str,
    domain: Optional[str] = None,
    query_hints: list[str] | None = None,
    limit: int = MAX_RAW,
) -> list[dict[str, Any]]:
    """
    Neo4j keyword wide search (graph expansion 없음).
    intent.query_hints로 검색어 확장.
    """
    terms = _expand_terms(question, extra_hints=query_hints)
    if not terms:
        return []

    cypher = _build_search_cypher(domain)
    params: dict = {"terms": terms, "limit": limit}
    if domain:
        params["domain"] = domain

    with _driver() as driver:
        with driver.session(database=NEO4J_DATABASE) as session:
            records = session.run(cypher, **params)
            return [dict(r) for r in records]


def enrich_with_next(
    session: Any,
    curated: list[dict[str, Any]],
    seen_ids: set[str],
) -> list[dict[str, Any]]:
    """
    Reranking 후 최종 curated chunks에 NEXT ±1 문맥 청크를 추가.
    (graph expansion은 여기서만 수행)
    """
    enriched = list(curated)
    for chunk in curated:
        chunk_id = chunk.get("id") or ""
        if not chunk_id:
            continue

        result = session.run("""
            MATCH (c:Chunk {id: $chunk_id})
            OPTIONAL MATCH (prev:Chunk)-[:NEXT]->(c)
            OPTIONAL MATCH (c)-[:NEXT]->(nxt:Chunk)
            WITH collect(prev) + collect(nxt) AS neighbors
            UNWIND neighbors AS neighbor
            WITH neighbor WHERE neighbor IS NOT NULL
            MATCH (d:Document)-[:CONTAINS]->(neighbor)
            OPTIONAL MATCH (neighbor)-[:HAS_TAG]->(t:Tag)
            RETURN
                neighbor.id AS id,
                d.name AS document,
                neighbor.text AS text,
                neighbor.core_insight_en AS insight_en,
                neighbor.core_insight_ko AS insight_ko,
                neighbor.domain AS domain,
                collect(DISTINCT t.name) AS tags,
                1 AS score
        """, chunk_id=chunk_id)

        for rec in result:
            rec_dict = dict(rec)
            rid = rec_dict.get("id") or ""
            if rid and rid not in seen_ids:
                seen_ids.add(rid)
                enriched.append(rec_dict)

    return enriched


def get_evidence_pipeline(
    question: str,
    domain: str,
    task: Optional[str] = None,
    enrich_context: bool = False,
) -> tuple[list[dict], list[dict], rr.RerankDebug]:
    """
    전체 파이프라인:
      1. intent classify
      2. wide_search (30개)
      3. rerank → curated (5-6개)
      4. (선택) NEXT ±1 context enrich

    Returns:
        raw_results: 30개 원본
        curated_results: 5-6개 최종
        debug: RerankDebug
    """
    from app.core.domain_policy import get_policy

    policy = get_policy(domain)
    neo4j_domain: Optional[str] = policy.get("neo4j_domain")

    # 1. Intent classify
    profile = ic.classify(domain, question, task)

    # 2. Wide search
    raw_results = wide_search(
        question=question,
        domain=neo4j_domain,
        query_hints=profile.query_hints,
        limit=MAX_RAW,
    )

    # 3. Rerank
    curated, debug = rr.rerank(
        chunks=raw_results,
        boost_terms=profile.boost_terms,
        penalty_terms=profile.penalty_terms,
        min_score=profile.min_score,
        max_per_document=profile.max_per_document,
        intent=profile.intent,
    )

    # 4. (선택) NEXT context enrichment
    if enrich_context and curated:
        seen_ids = {c.get("id") for c in curated if c.get("id")}
        with _driver() as driver:
            with driver.session(database=NEO4J_DATABASE) as session:
                curated = enrich_with_next(session, curated, seen_ids)

    return raw_results, curated, debug


def format_context(results: list[dict[str, Any]]) -> str:
    """LLM에 넘길 컨텍스트 블록 구성."""
    blocks = []
    used_chars = 0

    for index, item in enumerate(results, start=1):
        text = (item.get("text") or "").strip()
        if len(text) > 900:
            text = text[:900].rstrip() + "..."

        block = "\n".join([
            f"[Source {index}]",
            f"Document: {item.get('document')}",
            f"Chunk ID: {item.get('id')}",
            f"Domain: {item.get('domain', 'unknown')}",
            f"Tags: {', '.join(item.get('tags') or [])}",
            f"Korean insight: {item.get('insight_ko') or ''}",
            f"English insight: {item.get('insight_en') or ''}",
            f"Text excerpt: {text}",
        ])

        if used_chars + len(block) > MAX_CONTEXT_CHARS:
            break

        blocks.append(block)
        used_chars += len(block)

    return "\n\n".join(blocks)


# ── 하위 호환: 기존 search_evidence 인터페이스 유지 ─────────────────────
def search_evidence(
    question: str,
    domain: Optional[str] = None,
    limit: int = MAX_RAW,
    expand_graph: bool = False,
) -> list[dict[str, Any]]:
    """legacy: raw wide_search만 반환. rag_engine은 get_evidence_pipeline 사용."""
    return wide_search(question=question, domain=domain, limit=limit)
