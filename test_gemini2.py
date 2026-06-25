import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY", ""))

response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents="""
You are an IoT controller.

Available devices:
- LED
- RELAY
- PUMP

Available actions:
- ON
- OFF

Return ONLY valid JSON.

Examples:

Turn on LED
{"device":"LED","action":"ON"}

Turn off pump
{"device":"PUMP","action":"OFF"}

User: Turn on LED
"""
)

print(response.text)