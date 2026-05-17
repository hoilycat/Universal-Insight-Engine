import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-flash')

prompt = """
Analyze this text and return a JSON object with 'insight_en', 'insight_ko', and 'tags'.
Text: 'Designing Visual Recognition for the Brand. Nokia and Volvo case studies.'
"""

response = model.generate_content(prompt)
print("--- RAW RESPONSE ---")
print(response.text)
