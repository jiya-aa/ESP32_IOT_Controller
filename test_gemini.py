import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.environ.get("GEMINI_API_KEY", "")
genai.configure(api_key=API_KEY)

model = genai.GenerativeModel("gemini-1.5-flash")

response = model.generate_content(
    "Convert 'turn on led' into JSON. Respond only with JSON."
)

print(response.text)