import json
import os
import re
import urllib.request
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from neo4j import GraphDatabase


CORE_DIR = Path(__file__).resolve().parents[2]
ROOT_DIR = CORE_DIR.parent

load_dotenv(ROOT_DIR / ".env")
load_dotenv(CORE_DIR / ".env", override=True)

NEO4J_URI = os.getenv("NEO4J_URI", "neo4j://127.0.0.1:7687")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "yongyong1234")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434/api/generate")
EXAONE_MODEL = os.getenv("EXAONE_MODEL", "exaone3.5:latest")

MAX_CONTEXT_CHARS = 5500

TERM_EXPANSIONS = {
    "\ube0c\ub79c\ub4dc": ["brand", "branding", "brand recognition", "brand preference"],
    "\ub514\uc790\uc778": ["design", "visual", "aesthetic", "layout"],
    "\ub17c\ubb38": ["paper", "study", "research", "article"],
    "\uc5f0\uad6c": ["study", "research", "experiment"],
    "\uc8fc\uc758": ["attention", "visual attention", "attentional"],
    "\ud53c\ub85c": ["fatigue", "tiredness", "sleep"],
    "\uac01\uc131": ["arousal", "alertness", "stimulation"],
    "\uc120\ud638": ["preference", "liking"],
    "\uae30\uc5b5": ["memory", "recognition", "recall"],
}


def _driver():
    return GraphDatabase.driver(
        NEO4J_URI,
        auth=(NEO4J_USERNAME, NEO4J_PASSWORD),
    )


def _expand_terms(question: str) -> list[str]:
    raw_terms = re.findall(r"[A-Za-z0-9\uac00-\ud7a3][A-Za-z0-9\uac00-\ud7a3_-]{1,}", question.lower())
    terms = set(raw_terms)

    for key, expansions in TERM_EXPANSIONS.items():
        if key in question:
            terms.update(term.lower() for term in expansions)

    return sorted(terms)


def search_knowledge_base(question: str, limit: int = 8) -> list[dict[str, Any]]:
    terms = _expand_terms(question)
    if not terms:
        return []

    cypher = """
    MATCH (d:Document)-[:CONTAINS]->(c:Chunk)
    OPTIONAL MATCH (c)-[:HAS_TAG]->(t:Tag)
    WITH d, c, collect(DISTINCT t.name) AS tags
    WITH d, c, tags,
         reduce(score = 0, term IN $terms |
            score
            + CASE WHEN toLower(coalesce(c.text, "")) CONTAINS term THEN 3 ELSE 0 END
            + CASE WHEN toLower(coalesce(c.core_insight_en, "")) CONTAINS term THEN 5 ELSE 0 END
            + CASE WHEN toLower(coalesce(c.core_insight_ko, "")) CONTAINS term THEN 5 ELSE 0 END
            + CASE WHEN toLower(coalesce(d.name, "")) CONTAINS term THEN 4 ELSE 0 END
            + CASE WHEN any(tag IN tags WHERE toLower(tag) CONTAINS term) THEN 4 ELSE 0 END
         ) AS score
    WHERE score > 0
    RETURN
        c.id AS id,
        d.name AS document,
        c.text AS text,
        c.core_insight_en AS insight_en,
        c.core_insight_ko AS insight_ko,
        tags AS tags,
        score AS score
    ORDER BY score DESC
    LIMIT $limit
    """

    with _driver() as driver:
        with driver.session(database=NEO4J_DATABASE) as session:
            records = session.run(cypher, terms=terms, limit=limit)
            return [dict(record) for record in records]


def _format_context(results: list[dict[str, Any]]) -> str:
    blocks = []
    used_chars = 0

    for index, item in enumerate(results, start=1):
        text = (item.get("text") or "").strip()
        if len(text) > 900:
            text = text[:900].rstrip() + "..."

        block = "\n".join(
            [
                f"[Source {index}]",
                f"Document: {item.get('document')}",
                f"Chunk ID: {item.get('id')}",
                f"Tags: {', '.join(item.get('tags') or [])}",
                f"Korean insight: {item.get('insight_ko') or ''}",
                f"English insight: {item.get('insight_en') or ''}",
                f"Text excerpt: {text}",
            ]
        )

        if used_chars + len(block) > MAX_CONTEXT_CHARS:
            break

        blocks.append(block)
        used_chars += len(block)

    return "\n\n".join(blocks)


def _call_exaone(prompt: str) -> str:
    payload = {
        "model": EXAONE_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.2,
            "top_p": 0.9,
            "num_predict": 700,
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


def _fallback_answer(question: str, results: list[dict[str, Any]]) -> str:
    lines = [
        "Neo4j found relevant evidence, but the EXAONE call failed.",
        f"Question: {question}",
        "",
        "Top evidence:",
    ]

    for index, item in enumerate(results[:5], start=1):
        insight = item.get("insight_ko") or item.get("insight_en") or ""
        lines.append(f"{index}. {item.get('document')} / {item.get('id')}: {insight}")

    return "\n".join(lines)


def ask_knowledge_base(question: str) -> str:
    results = search_knowledge_base(question)
    if not results:
        return "Neo4j knowledge base did not find matching evidence. Try adding more specific keywords."

    context = _format_context(results)
    prompt = f"""
You are Yongyong Agentic Core, an expert Korean research assistant.
Answer the user's question using ONLY the provided Neo4j knowledge base context.

[STRICT RULES]
1. ANTI-HALLUCINATION: NEVER invent or guess papers, findings, or numbers that are not explicitly stated in the context. If the context does not contain the answer, explicitly state that there is not enough information.
2. LANGUAGE: You must answer entirely in professional, academic Korean.
3. OUTPUT FORMAT: You must strictly structure your response into the following three sections using markdown headings:

### [요약]
Write a clear, concise summary answering the user's question (2-3 sentences).

### [관련 근거]
List the specific documents and chunk IDs used to form your answer.
Example format:
- **논문명**: `Document Name`
  - **핵심 내용**: (Brief description of the chunk's insight)
  - **Chunk ID**: `chunk_id`

### [실무 적용]
Provide 1-2 practical, actionable insights on how this knowledge can be applied to real-world design, healthcare, or business strategies.

[User Question]
{question}

[Neo4j Knowledge Base Context]
{context}
""".strip()

    try:
        answer = _call_exaone(prompt)
    except Exception:
        return _fallback_answer(question, results)

    return answer or _fallback_answer(question, results)
