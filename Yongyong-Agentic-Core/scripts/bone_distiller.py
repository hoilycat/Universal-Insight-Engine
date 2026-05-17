import json
import uuid
from datetime import datetime

# Collected Search Results (Distilled by Yongyong)
BONE_DATA = [
    {
        "title": "Load Theory of Selective Attention and Cognitive Control (Lavie et al., 2004)",
        "category": "design",
        "tags": ["Attention", "Performance", "Processing Fluency"],
        "insight_en": "Lavie's Load Theory proposes that selective attention is determined by perceptual load and cognitive control. High perceptual load reduces distractor processing by exhausting perceptual capacity (early selection), while high cognitive load increases distractor interference by taxing executive functions required for top-down control.",
        "insight_ko": "Lavie의 부하 이론(Load Theory)은 선택적 주의가 지각 부하와 인지 제어에 의해 결정된다고 제안합니다. 높은 지각 부하(디자인 복잡성 등)는 지각 용량을 모두 소모하여 방해 자극 처리를 줄이는 반면(초기 선택), 높은 인지 부하(멀티태스킹 등)는 상향식 제어에 필요한 실행 기능을 고갈시켜 오히려 방해 자극에 더 취약하게 만듭니다."
    },
    {
        "title": "A Two Process Model of Sleep Regulation (Borbély, 1982)",
        "category": "health",
        "tags": ["Arousal", "Fatigue", "Performance"],
        "insight_en": "Borbély's Two-Process Model posits that sleep is regulated by the interaction of Process S (Homeostatic sleep drive that builds up during wakefulness) and Process C (Circadian rhythm controlled by the biological clock). Caffeine acts as an adenosine antagonist, effectively masking the buildup of Process S.",
        "insight_ko": "Borbély의 2-프로세스 모델은 수면이 프로세스 S(깨어 있는 동안 쌓이는 항상성 수면 압박)와 프로세스 C(생체 시계에 의해 조절되는 일주기 리듬)의 상호작용에 의해 조절된다고 설명합니다. 카페인은 아데노신 길항제로 작용하여 프로세스 S의 축적을 일시적으로 차단하거나 마스킹하는 역할을 합니다."
    },
    {
        "title": "The Attention System of the Human Brain: 20 Years After (Petersen & Posner, 2012)",
        "category": "design",
        "tags": ["Attention", "Arousal", "Recognition", "Performance"],
        "insight_en": "Reaffirming and updating the 1990 framework, this paper identifies three distinct attentional networks: Alerting (arousal/vigilance), Orienting (prioritizing sensory input), and Executive Control (resolving conflict/goal-directed behavior). These networks provide the anatomical and functional common path for all cognitive tasks.",
        "insight_ko": "1990년의 뼈대 이론을 업데이트한 이 논문은 주의력 시스템을 세 가지 네트워크로 구분합니다: 경고(Alerting, 각성/경계), 지향(Orienting, 감각 입력 우선순위 지정), 실행 제어(Executive Control, 갈등 해결/목표 지향 행동). 이 네트워크들은 모든 인지 작업의 해부학적, 기능적 공통 경로를 제공합니다."
    },
    {
        "title": "Microcomputer analysis of performance on a portable, simple visual RT task (Dinges & Powell, 1985)",
        "category": "health",
        "tags": ["Performance", "Fatigue", "Attention"],
        "insight_en": "Introduced the Psychomotor Vigilance Task (PVT), the gold standard for measuring behavioral alertness. It focuses on 'lapsing' (slow responses >= 500ms) and 'response slowing' as primary indicators of sleep loss and fatigue, showing high sensitivity to even minor attentional declines.",
        "insight_ko": "행동 각성도를 측정하는 골드 스탠다드인 PVT(Psychomotor Vigilance Task)를 도입했습니다. 수면 부족과 피로의 주요 지표로 'Lapsing(500ms 이상의 늦은 응답)'과 '응답 저하'에 집중하며, 아주 미세한 주의력 저하에도 높은 민감도를 보임을 증명했습니다."
    },
    {
        "title": "Caffeine Attenuates Waking and Sleep EEG Markers of Sleep Homeostasis in Humans (Landolt et al., 2004)",
        "category": "health",
        "tags": ["Arousal", "Fatigue", "Performance"],
        "insight_en": "Physiological evidence that caffeine, as an adenosine receptor antagonist, attenuates EEG markers of sleep pressure (theta activity during wakefulness and slow-wave activity during recovery sleep). This confirms that caffeine interferes with the brain's homeostatic tracking of sleep need.",
        "insight_ko": "카페인이 아데노신 수용체 길항제로서 수면 압박의 EEG 지표(깨어 있을 때의 세타 활동 및 회복 수면 중의 서파 활동)를 감쇄시킨다는 생리학적 증거를 제시했습니다. 이는 카페인이 뇌의 항상성 수면 추적 시스템을 방해한다는 것을 확인해 줍니다."
    },
    {
        "title": "Emotional Design (Norman, 2004)",
        "category": "design",
        "tags": ["Preference", "Recognition", "Processing Fluency"],
        "insight_en": "Don Norman identifies three levels of design processing: Visceral (instinctive/aesthetic), Behavioral (functional/usability), and Reflective (meaning/identity). Attractive things work better because positive affect enhances cognitive flexibility at the visceral level.",
        "insight_ko": "도널드 노먼은 디자인 처리의 세 단계를 본능적(미학/첫인상), 행동적(기능/사용성), 성찰적(의미/정체성) 단계로 구분합니다. 긍정적인 감정은 본능적 수준에서 인지적 유연성을 높여주기 때문에, '보기 좋은 떡이 먹기도 좋다(매력적인 것이 더 잘 작동한다)'는 원리를 설명합니다."
    },
    {
        "title": "The Attention System of the Human Brain (Posner & Petersen, 1990)",
        "category": "design",
        "tags": ["Attention", "Arousal", "Performance"],
        "insight_en": "The original foundational paper establishing that attention is an independent anatomical system organized into specific functional networks. It introduced the influential 'Disengage, Move, Engage' model for the orienting network in the parietal cortex.",
        "insight_ko": "주의력이 특정 기능 네트워크로 구성된 독립적인 해부학적 시스템임을 확립한 원조 논문입니다. 특히 두정엽의 지향 네트워크를 설명하는 '해제(Disengage), 이동(Move), 결합(Engage)' 모델을 도입하여 큰 반향을 일으켰습니다."
    }
]

def distill_bones():
    design_bones = []
    health_bones = []
    
    timestamp = datetime.now().isoformat() + "Z"
    
    for bone in BONE_DATA:
        chunk = {
            "id": str(uuid.uuid4()),
            "text": f"Foundational Bone: {bone['title']}\nSummary: {bone['insight_en']}",
            "metadata": {
                "file_name": bone['title'],
                "category": bone['category'],
                "project": "YIE-Foundation",
                "core_insight_en": bone['insight_en'],
                "core_insight_ko": bone['insight_ko'],
                "hub_tags": bone['tags'],
                "is_structural_bone": True
            }
        }
        
        if bone['category'] == "design":
            design_bones.append(chunk)
        else:
            health_bones.append(chunk)
            
    # Append to existing files
    with open("data/chunks/design_chunks.jsonl", "a", encoding="utf-8") as f:
        for chunk in design_bones:
            f.write(json.dumps(chunk, ensure_ascii=False) + "\n")
            
    with open("data/chunks/health_chunks.jsonl", "a", encoding="utf-8") as f:
        for chunk in health_bones:
            f.write(json.dumps(chunk, ensure_ascii=False) + "\n")
            
    print(f"Success! Added {len(design_bones)} design bones and {len(health_bones)} health bones to the knowledge base.")

if __name__ == "__main__":
    distill_bones()
