"""Gemini-backed natural-language interpreter.

Turns a free-form user command into a list of structured action dicts,
e.g. [{"mode": "LED_ON"}] or [{"mode": "CHAT", "text": "..."}].
Pure logic: no hardware, no audio, no printing — ideal for reuse by a
web backend.
"""

from __future__ import annotations

import json
import re
import time

from google import genai

import config

PROMPT_TEMPLATE = """\
You are an AI IoT assistant that controls smart home devices.

Available devices and actions — return JSON exactly as shown:

  LED (built-in light)
    ON  → {{"mode":"LED_ON"}}
    OFF → {{"mode":"LED_OFF"}}

  RELAY (mains switch / appliance)
    ON  → {{"mode":"RELAY_ON"}}
    OFF → {{"mode":"RELAY_OFF"}}

  PUMP (water pump)
    ON  → {{"mode":"PUMP_ON"}}
    OFF → {{"mode":"PUMP_OFF"}}

  OLED display
    Show text → {{"mode":"DISPLAY","text":"<text to show>"}}

For any general question or chat, return:
    {{"mode":"CHAT","text":"<your answer>"}}

You may return a JSON array to execute multiple actions at once.
Respond ONLY with valid JSON — no markdown fences, no extra text.

User: {command}
"""


def _strip_json_fences(text: str) -> str:
    """Remove ```json ... ``` or ``` ... ``` markdown fences if present."""
    text = text.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    return match.group(1).strip() if match else text


class Assistant:
    def __init__(self, api_key: str = None, model: str = "gemini-2.5-flash"):
        self.client = genai.Client(api_key=api_key or config.require_api_key())
        self.model = model

    def interpret(self, command: str, retries: int = 3) -> list[dict] | None:
        """Return a list of action dicts, or None if Gemini is unreachable."""
        prompt = PROMPT_TEMPLATE.format(command=command)
        for attempt in range(retries):
            response = None
            try:
                response = self.client.models.generate_content(
                    model=self.model, contents=prompt
                )
                data = json.loads(_strip_json_fences(response.text))
                # Normalise to a list so callers handle one shape only.
                return data if isinstance(data, list) else [data]
            except json.JSONDecodeError as e:
                raw = (response.text[:120] if response else "")
                print("  JSON parse error:", e, "| Raw:", raw)
            except Exception as e:
                print(f"  Gemini error (attempt {attempt + 1}):", e)
                if attempt < retries - 1:
                    print("  Retrying in 3 s...")
                    time.sleep(3)
        return None
