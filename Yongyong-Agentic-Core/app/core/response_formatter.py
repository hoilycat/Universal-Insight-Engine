# app/core/response_formatter.py
"""
공통 응답 정규화.
LLM 출력 텍스트를 sections 구조로 파싱하고
EvidenceItem 목록을 정규화한다.
"""
import re
from typing import Any, Optional


def parse_sections(llm_output: str) -> dict[str, Optional[str]]:
    """
    LLM 출력에서 ### [섹션명] 블록을 추출한다.
    누락된 섹션은 None으로 채운다.
    """
    section_patterns = {
        "summary":        r"###\s*\[요약\](.*?)(?=###|\Z)",
        "evidence":       r"###\s*\[관련 근거\](.*?)(?=###|\Z)",
        "recommendation": r"###\s*\[실무 적용\](.*?)(?=###|\Z)",
    }

    result: dict[str, Optional[str]] = {}
    for key, pattern in section_patterns.items():
        match = re.search(pattern, llm_output, re.DOTALL)
        result[key] = match.group(1).strip() if match else None

    # 섹션 파싱 실패 시 전체 텍스트를 summary에 담아 데이터 손실 방지
    if not any(result.values()):
        result["summary"] = llm_output.strip()
        result["evidence"] = None
        result["recommendation"] = None

    result.setdefault("warning", None)
    return result


def normalize_evidence(raw_results: list[dict[str, Any]]) -> list[dict]:
    """
    Neo4j 검색 결과를 EvidenceItem 직렬화 포맷으로 정규화.
    score는 int로 강제 변환 (Neo4j 반환값이 float일 수 있음).
    """
    normalized = []
    for item in raw_results:
        normalized.append({
            "document": item.get("document") or "Unknown",
            "chunk_id": item.get("id") or "",
            "tags":     list(item.get("tags") or []),
            "insight_ko": item.get("insight_ko") or "",
            "score":    int(item.get("score") or 0),
        })
    return normalized


def build_response(
    domain: str,
    task: str,
    llm_output: str,
    raw_results: list[dict[str, Any]],
    cross_domain_used: bool = False,
) -> dict:
    """
    최종 RagResponse 딕셔너리 조립.
    schemas.py의 RagResponse와 1:1 매핑.
    """
    sections = parse_sections(llm_output)
    evidence = normalize_evidence(raw_results)

    return {
        "domain": domain,
        "task": task,
        "answer": llm_output.strip(),
        "sections": sections,
        "evidence": evidence,
        "cross_domain_used": cross_domain_used,
    }


def build_fallback_response(
    domain: str,
    task: str,
    question: str,
    raw_results: list[dict[str, Any]],
    error_hint: str = "",
) -> dict:
    """
    LLM 호출 실패 시 근거 목록만으로 구성하는 fallback 응답.
    """
    top_insights = []
    for i, item in enumerate(raw_results[:5], 1):
        insight = item.get("insight_ko") or item.get("insight_en") or ""
        top_insights.append(f"{i}. [{item.get('document')}] {insight}")

    fallback_text = "\n".join([
        f"[LLM 호출 실패{': ' + error_hint if error_hint else ''}]",
        f"질문: {question}",
        "",
        "상위 근거 목록:",
        *top_insights,
    ])

    return build_response(
        domain=domain,
        task=task,
        llm_output=fallback_text,
        raw_results=raw_results,
        cross_domain_used=False,
    )
