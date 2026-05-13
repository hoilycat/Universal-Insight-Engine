#!/usr/bin/env python
# scripts/test_regression.py
"""
GraphRAG Evidence Pipeline Regression Test

고정 질문 세트로 curated_results 품질을 체크한다.
서버가 실행 중이어야 한다: python -m uvicorn app.main:app --reload

사용법:
    cd Yongyong-Agentic-Core
    python scripts/test_regression.py
    python scripts/test_regression.py --url http://localhost:8000
    python scripts/test_regression.py --fail-fast
"""
import argparse
import json
import sys
import urllib.request
from dataclasses import dataclass, field
from typing import Optional


# ─── 고정 테스트 케이스 ────────────────────────────────────────────────
@dataclass
class TestCase:
    name: str
    domain: str
    task: str
    question: str
    # 검증 조건
    min_raw: int = 5
    min_curated: int = 3
    expected_intent: Optional[str] = None
    forbidden_in_curated: list[str] = field(default_factory=list)   # curated insight에 있으면 안 되는 단어
    required_in_curated: list[str] = field(default_factory=list)    # curated insight에 하나라도 있어야 하는 단어


TEST_CASES: list[TestCase] = [
    # ── Coffee 도메인 ───────────────────────────────────────────────────
    TestCase(
        name="coffee_mechanism_adenosine",
        domain="coffee", task="mechanism_query",
        question="카페인이 아데노신 수용체에 미치는 영향",
        expected_intent="mechanism_query",
        required_in_curated=["adenosine", "아데노신", "수용체", "receptor"],
        forbidden_in_curated=["브랜드 아이덴티티", "brand identity"],
        min_curated=3,
    ),
    TestCase(
        name="coffee_sleep_effect",
        domain="coffee", task="symptom_query",
        question="카페인이 수면에 미치는 영향",
        expected_intent="symptom_query",
        required_in_curated=["수면", "sleep", "fatigue", "피로"],
        forbidden_in_curated=["브랜드", "brand identity", "visual design"],
        min_curated=3,
    ),
    TestCase(
        name="coffee_headache_withdrawal",
        domain="coffee", task="symptom_query",
        question="카페인 금단 두통의 원인과 메커니즘",
        expected_intent="symptom_query",
        required_in_curated=["headache", "두통", "withdrawal", "금단"],
        min_curated=2,
    ),
    TestCase(
        name="coffee_stats_pattern",
        domain="coffee", task="stats_insight",
        question="하루 카페인 섭취 패턴 분석",
        expected_intent="stats_insight",
        min_curated=2,
    ),

    # ── Design 도메인 ───────────────────────────────────────────────────
    TestCase(
        name="design_brand_visual",
        domain="design", task="brand_analysis",
        question="브랜드 가치를 시각적으로 전달하는 방법",
        expected_intent="brand_analysis",
        required_in_curated=["brand", "브랜드", "visual", "시각"],
        forbidden_in_curated=["카페인", "caffeine", "두통", "headache"],
        min_curated=3,
    ),
    TestCase(
        name="design_visual_attention",
        domain="design", task="visual_reasoning",
        question="시각적 주의와 디자인 복잡도의 관계",
        expected_intent="visual_reasoning",
        required_in_curated=["attention", "주의", "visual", "design"],
        forbidden_in_curated=["카페인", "수면 장애"],
        min_curated=3,
    ),
    TestCase(
        name="design_processing_fluency",
        domain="design", task="research_query",
        question="처리 유창성이 디자인 선호도에 미치는 영향",
        expected_intent="research_query",
        required_in_curated=["fluency", "preference", "design"],
        min_curated=2,
    ),

    # ── Integrated 도메인 ───────────────────────────────────────────────
    TestCase(
        name="integrated_cross_domain",
        domain="integrated", task="cross_domain_insight",
        question="카페인이 디자인 집중력에 미치는 영향",
        min_raw=3,
        min_curated=2,
    ),
]


# ─── 테스트 실행 ──────────────────────────────────────────────────────
@dataclass
class TestResult:
    name: str
    passed: bool
    failures: list[str]
    debug: Optional[dict] = None
    curated_count: int = 0
    raw_count: int = 0


def run_test(case: TestCase, base_url: str) -> TestResult:
    failures = []
    debug_info = None
    curated_count = 0
    raw_count = 0

    try:
        payload = json.dumps({
            "domain": case.domain,
            "task": case.task,
            "question": case.question,
        }).encode("utf-8")

        req = urllib.request.Request(
            f"{base_url}/rag/evidence",
            headers={"Content-Type": "application/json"},
            data=payload,
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read())

    except Exception as e:
        return TestResult(
            name=case.name, passed=False,
            failures=[f"HTTP 요청 실패: {e}"],
        )

    raw_count = len(body.get("raw_results", []))
    curated = body.get("curated_results", [])
    curated_count = len(curated)
    debug_info = body.get("debug", {})

    # 1. min_raw 체크
    if raw_count < case.min_raw:
        failures.append(f"raw_results {raw_count} < min_raw {case.min_raw}")

    # 2. min_curated 체크
    if curated_count < case.min_curated:
        failures.append(f"curated_results {curated_count} < min_curated {case.min_curated}")

    # 3. intent 체크
    if case.expected_intent and debug_info:
        actual_intent = debug_info.get("intent", "")
        if actual_intent != case.expected_intent:
            failures.append(
                f"intent mismatch: expected={case.expected_intent}, got={actual_intent}"
            )

    # 4. required_in_curated 체크 (하나라도 있으면 OK)
    if case.required_in_curated and curated:
        all_text = " ".join([
            (c.get("insight_ko") or "") + " " + (c.get("document") or "")
            for c in curated
        ]).lower()
        found_any = any(t.lower() in all_text for t in case.required_in_curated)
        if not found_any:
            failures.append(
                f"required terms not found in curated: {case.required_in_curated}"
            )

    # 5. forbidden_in_curated 체크 (하나라도 있으면 FAIL)
    if case.forbidden_in_curated and curated:
        all_text = " ".join([
            (c.get("insight_ko") or "") for c in curated
        ]).lower()
        found_forbidden = [t for t in case.forbidden_in_curated if t.lower() in all_text]
        if found_forbidden:
            failures.append(
                f"forbidden terms found in curated insights: {found_forbidden}"
            )

    return TestResult(
        name=case.name,
        passed=len(failures) == 0,
        failures=failures,
        debug=debug_info,
        curated_count=curated_count,
        raw_count=raw_count,
    )


def main():
    parser = argparse.ArgumentParser(description="YIE GraphRAG Regression Test")
    parser.add_argument("--url", default="http://localhost:8000", help="API base URL")
    parser.add_argument("--fail-fast", action="store_true", help="첫 실패 시 중단")
    parser.add_argument("--verbose", "-v", action="store_true", help="debug 정보 출력")
    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"  YIE GraphRAG Regression Test")
    print(f"  Target: {args.url}")
    print(f"  Cases:  {len(TEST_CASES)}")
    print(f"{'='*60}\n")

    results: list[TestResult] = []

    for case in TEST_CASES:
        print(f"  [{case.domain.upper():<12}] {case.name} ...", end=" ", flush=True)
        result = run_test(case, args.url)
        results.append(result)

        status = "[PASS]" if result.passed else "[FAIL]"
        debug = result.debug or {}
        print(f"{status}  raw={result.raw_count} curated={result.curated_count} "
              f"intent={debug.get('intent','?')} "
              f"score_avg={debug.get('score_avg','?')}")

        if not result.passed:
            for f in result.failures:
                print(f"         └─ {f}")

        if args.verbose and result.debug:
            print(f"         debug: {result.debug}")

        if args.fail_fast and not result.passed:
            print("\n  --fail-fast: 중단\n")
            sys.exit(1)

    # 요약
    passed = sum(1 for r in results if r.passed)
    failed = len(results) - passed

    print(f"\n{'='*60}")
    print(f"  결과: {passed}/{len(results)} passed  ({failed} failed)")
    print(f"{'='*60}\n")

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
