# app/core/rag_engine.py
"""
공통 GraphRAG 파이프라인.

흐름:
  1. domain_policy → neo4j_domain 결정
  2. evidence.search_evidence() → 기반 청크 + 그래프 확장
  3. domain_policy.build_domain_prompt_header() → 도메인 프롬프트 조립
  4. _call_exaone() → LLM 호출
  5. response_formatter.build_response() → 공통 응답 포맷 반환
"""
import json
import os
import urllib.request
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv

from app.core.domain_policy import get_policy, build_domain_prompt_header
from app.core.evidence import get_evidence_pipeline, format_context
from app.core.response_formatter import build_response, build_fallback_response

CORE_DIR = Path(__file__).resolve().parents[2]
ROOT_DIR = CORE_DIR.parent

load_dotenv(ROOT_DIR / ".env")
load_dotenv(CORE_DIR / ".env", override=True)

OLLAMA_URL   = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434/api/generate")
EXAONE_MODEL = os.getenv("EXAONE_MODEL", "exaone3.5:latest")


def _call_exaone(prompt: str) -> str:
    payload = {
        "model": EXAONE_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.2,
            "top_p": 0.9,
            "num_predict": 800,
        },
    }
    request = urllib.request.Request(
        OLLAMA_URL,
        headers={"Content-Type": "application/json"},
        data=json.dumps(payload).encode("utf-8"),
    )
    with urllib.request.urlopen(request, timeout=180) as response:
        data = json.loads(response.read().decode("utf-8"))
        return data.get("response", "").strip()


def query(
    domain: str,
    task: str,
    question: str,
    context: Optional[dict] = None,
    expand_graph: bool = False,
) -> dict[str, Any]:
    """
    메인 RAG 파이프라인.
    classify → wide_search(30) → rerank → curated(5-6) → LLM
    """
    # 1. Evidence pipeline (classify → search → rerank)
    raw_results, curated, debug = get_evidence_pipeline(
        question=question,
        domain=domain,
        task=task,
        enrich_context=expand_graph,
    )

    if not curated:
        # curated가 없으면 raw에서 상위 5개 fallback
        fallback = raw_results[:5] if raw_results else []
        return build_fallback_response(
            domain=domain,
            task=task,
            question=question,
            raw_results=fallback,
            error_hint="Reranker 후 관련 근거를 찾지 못했습니다." if fallback
                       else "Neo4j knowledge base에서 관련 근거를 찾지 못했습니다.",
        )

    # 2. 컨텍스트 포맷 (curated만 사용)
    kb_context = format_context(curated)

    # 3. 도메인 프롬프트 조립
    prompt_header = build_domain_prompt_header(domain, task, question)
    full_prompt = f"{prompt_header}\n\n[Neo4j Knowledge Base Context]\n{kb_context}"

    # 4. cross_domain 감지
    policy = get_policy(domain)
    neo4j_domain = policy.get("neo4j_domain")
    cross_domain_used = bool(neo4j_domain) and any(
        r.get("domain") and r["domain"] != neo4j_domain
        for r in curated
    )

    # 5. LLM 호출
    try:
        llm_output = _call_exaone(full_prompt)
    except Exception as e:
        return build_fallback_response(
            domain=domain, task=task, question=question,
            raw_results=curated, error_hint=str(e),
        )

    if not llm_output:
        return build_fallback_response(
            domain=domain, task=task, question=question,
            raw_results=curated, error_hint="LLM이 빈 응답을 반환했습니다.",
        )

    # 6. 응답 정규화
    return build_response(
        domain=domain,
        task=task,
        llm_output=llm_output,
        raw_results=curated,
        cross_domain_used=cross_domain_used,
    )


def search_only(
    domain: str,
    question: str,
    task: Optional[str] = None,
    limit: int = 30,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], Any]:
    """
    /rag/evidence 용: raw + curated + debug 반환. LLM 호출 없음.
    """
    raw, curated, debug = get_evidence_pipeline(
        question=question,
        domain=domain,
        task=task,
        enrich_context=False,
    )
    return raw, curated, debug

