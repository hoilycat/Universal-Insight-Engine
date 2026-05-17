# app/core/provider.py
import os
from google import genai
from groq import Groq

class UnifiedBrain:
    def __init__(self):
        self.gemini_pro = "gemini-1.5-pro" # Architect
        self.gemini_flash = "gemini-1.5-flash" # Worker / Eye
        self.llama_analyst = "llama-3.3-70b-versatile" # Analyst (via Groq)
        
        self.groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.genai_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    def get_architect(self):
        """복잡한 계획 수립용"""
        return self.gemini_pro

    def get_analyst(self):
        """논리적 추론 및 지식 추출용"""
        return self.llama_analyst

    def get_worker(self):
        """단순 작업 및 빠른 응답용"""
        return self.gemini_flash

    def get_eye(self):
        """이미지 이해용"""
        return self.gemini_flash # 혹은 로컬 Moondream 연결
    
  # 필요에 따라 모델을 직접 호출하는 헬퍼 메서드도 제공
    def call_analyst(self, prompt: str) -> str:
        completion = self.groq_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model=self.llama_analyst,
        )
        return completion.choices[0].message.content