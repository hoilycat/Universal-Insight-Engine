from app.core.neo4j_kb import ask_knowledge_base


def ask_yie(question: str) -> str:
    return ask_knowledge_base(question)

__all__ = ["ask_yie"]
