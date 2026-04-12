# 🧠 Y-Insight Engine (YIE)
 
> **The Unified Intelligence Engine for Cross-Domain Insights**

---

🖋️ **Introduction**  
**Y-Insight Engine (YIE)**는 여러 독립적인 서비스(Mood-DNA, Cof/fee, Jim-Ssa)의 지능을 하나로 통합하여 관리하는 **에이전틱 백엔드 엔진**입니다. 단순히 데이터를 처리하는 서버를 넘어, 사용자의 라이프스타일과 디자인 감각을 연결하는 **'공통의 뇌'** 역할을 수행합니다.

이 엔진은 **Hybrid GraphRAG**와 **Agentic Search**를 통해 도메인 간의 지식을 융합하고, 시간이 흐를수록 사용자를 더 잘 이해하는 초개인화된 인사이트를 도출합니다.

---

## 🚀 Core Strategy

### 🕸️ 1. Unified Knowledge Graph (Shared Memory)
모든 앱의 데이터는 **Neo4j 기반의 단일 지식 그래프**에 저장됩니다.
*   **Design Domain:** 시각적 지표와 디자인 이론의 관계.
*   **Health Domain:** 카페인 섭취와 신체 반응(통증, 컨디션)의 인과관계.
*   **Synergy:** "피로도가 높은 날(Health) 작업한 디자인의 특징(Design)"을 분석하는 등 도메인 간 교차 추론 수행.

### 🤖 2. Agentic Reasoning Pipeline
AI 에이전트가 스스로 판단하고 행동합니다.
*   **Self-Planning:** 요청에 따라 어떤 도메인 지식을 꺼내올지 스스로 결정.
*   **Tavily Search Agent:** 내부 지식이 부족할 경우, 실시간 외부 웹 데이터를 검색하여 근거 보강.
*   **LLM Relay:** Gemini 1.5 Pro를 컨트롤러로 하여 상황에 최적인 모델(Groq, Ollama)을 배분.

### 🔌 3. Plug-and-Play Domain Services
새로운 서비스가 추가되어도 엔진의 구조를 변경할 필요가 없습니다.
*   `services/design`: 디자인 분석 특화 모듈
*   `services/coffee`: 신체 반응 추론 특화 모듈
*   `services/travel`: (Coming Soon) 여행 경험 최적화 모듈

---

## 🛠️ Tech Stack

*   **Framework:** FastAPI (Python 3.10+)
*   **Orchestration:** LlamaIndex (Agentic Workflow)
*   **Graph Database:** Neo4j (GraphRAG)
*   **Search Engine:** Tavily API, SerpApi
*   **AI Models:** Google Gemini 1.5 Pro, Llama 3.3, Moondream2

---

## 📁 Project Structure

```bash
Y-Insight-Engine/
├── app/
│   ├── main.py          # 🚦 API Gateway (Routing for Packy, Mood-DNA, Cof/fee)
│   ├── core/            # 🧠 Intelligence Engine
│   │   ├── graph.py     # Unified Knowledge Graph Logic
│   │   ├── search.py    # Tavily Search Agent
│   │   └── planner.py   # Agentic Task Planning
│   ├── services/        # 🔌 Domain Specific Logic
│   │   ├── travel.py    # [Packy] Logic
│   │   ├── design.py    # [Mood-DNA] Logic
│   │   └── coffee.py    # [Cof/fee] Logic
│   └── shared/          # ⚙️ Common Utilities (Auth, MCP Connectors)
└── data/
    ├── travel_wisdom/   # Travel/Customs Knowledge Base
    └── design_wisdom/   # Design Principles Knowledge Base
```

## ✨ Vision
"분절된 앱의 기능을 넘어, 통합된 지능의 경험으로."