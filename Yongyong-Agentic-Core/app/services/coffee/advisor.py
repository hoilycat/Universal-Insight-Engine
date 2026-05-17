from app.core.provider import UnifiedBrain

brain = UnifiedBrain()

def get_coffee_advice(caffeine_level: float, symptom: str):
    """커피 전문가의 시크하고 전문적인 조언"""
    prompt = f"""
    사용자의 현재 혈중 카페인 농도는 {caffeine_level}mg이며, '{symptom}' 증상을 호소하고 있습니다.
    의학적 근거(카페인 반감기 등)를 바탕으로 사용자에게 짧고 강렬한 컨디션 조언을 3줄 이내로 작성해줘.
    """
    return brain.call_analyst(prompt)