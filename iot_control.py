import os
import json
import re
import time

# Auto-load .env from the project folder (no shell setup needed)
try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))
except ImportError:
    pass  # python-dotenv not installed; fall back to shell env vars

import pyttsx3
import requests
import sounddevice as sd
import scipy.io.wavfile as wav
import whisper
from google import genai

# ── Config ────────────────────────────────────────────────────────────────────
# Set GEMINI_API_KEY in your environment, or paste it here as a fallback.
API_KEY   = os.environ.get("GEMINI_API_KEY", "YOUR_API_KEY_HERE")
ESP32_IP  = os.environ.get("ESP32_IP", "192.168.1.72")
ESP32_URL = f"http://{ESP32_IP}"

os.environ["PATH"] += os.pathsep + r"C:\Users\Jayati\Downloads\ffmpeg-8.1.1-essentials_build\ffmpeg-8.1.1-essentials_build\bin"

# ── Init ──────────────────────────────────────────────────────────────────────
client = genai.Client(api_key=API_KEY)
tts    = pyttsx3.init()
model  = whisper.load_model("base")
fs     = 16000

OLED_MAX_CHARS = 80   # trim long AI answers before sending to display


def esp32_get(path: str, params: dict = None) -> bool:
    """Send a GET request to the ESP32. Returns True on success."""
    try:
        requests.get(f"{ESP32_URL}{path}", params=params, timeout=3)
        return True
    except Exception as e:
        print(f"  ESP32 error ({path}):", e)
        return False


def speak(text: str) -> None:
    tts.say(text)
    tts.runAndWait()


def strip_json_fences(text: str) -> str:
    """Remove ```json ... ``` or ``` ... ``` markdown fences if present."""
    text = text.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if match:
        return match.group(1).strip()
    return text


def call_gemini(user_command: str):
    """Call Gemini with retry. Returns parsed JSON (dict or list) or None."""
    prompt = f"""
You are an AI IoT assistant that can control smart home devices.

Available IoT actions (return JSON for these):
- LED ON:      {{"mode":"LED_ON"}}
- LED OFF:     {{"mode":"LED_OFF"}}
- Display text:{{"mode":"DISPLAY","text":"<text to show>"}}

For any other question or general chat, return:
           {{"mode":"CHAT","text":"<your answer>"}}

Respond ONLY with valid JSON (no markdown fences, no extra text).

User: {user_command}
"""
    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
            raw = strip_json_fences(response.text)
            data = json.loads(raw)
            return data
        except json.JSONDecodeError as e:
            print("  JSON parse error:", e, "| Raw:", response.text[:120])
        except Exception as e:
            print(f"  Gemini error (attempt {attempt + 1}):", e)
            if attempt < 2:
                print("  Retrying in 3 s…")
                time.sleep(3)
    return None


# ── Main loop ─────────────────────────────────────────────────────────────────
while True:
    print("\nSpeak now…")

    audio = sd.rec(int(5 * fs), samplerate=fs, channels=1, dtype="int16")
    sd.wait()
    wav.write("command.wav", fs, audio)

    result = model.transcribe("command.wav", fp16=False)
    user_command = result["text"].strip()

    if not user_command:
        continue

    print("You said:", user_command)
    cmd = user_command.lower()

    # ── Exit ──────────────────────────────────────────────────────────────────
    if cmd in ("exit", "quit", "stop"):
        print("Goodbye!")
        speak("Goodbye!")
        break

    # ── Direct keyword shortcuts (fast path, no API call) ─────────────────────
    if "turn on led" in cmd or "led on" in cmd:
        if esp32_get("/led/on"):
            print("LED turned ON")
            speak("LED turned on")
        continue

    if "turn off led" in cmd or "led off" in cmd:
        if esp32_get("/led/off"):
            print("LED turned OFF")
            speak("LED turned off")
        continue

    if cmd.startswith("display "):
        text = user_command[8:].strip()
        if text:
            if esp32_get("/display", {"text": text[:OLED_MAX_CHARS]}):
                print("Displayed:", text)
                speak("Displayed on OLED")
        continue

    # ── Gemini fallback ───────────────────────────────────────────────────────
    data = call_gemini(user_command)

    if data is None:
        print("Gemini unavailable or quota exhausted.")
        speak("Sorry, I could not reach the AI right now.")
        continue

    # Normalise to list so we can handle single command or array of commands
    if isinstance(data, dict):
        data = [data]

    for command in data:
        mode = command.get("mode", "")

        if mode == "LED_ON":
            if esp32_get("/led/on"):
                print("AI → LED ON")
                speak("LED turned on")

        elif mode == "LED_OFF":
            if esp32_get("/led/off"):
                print("AI → LED OFF")
                speak("LED turned off")

        elif mode == "DISPLAY":
            text = command.get("text", "")[:OLED_MAX_CHARS]
            if text:
                esp32_get("/display", {"text": text})
                print("AI → Display:", text)
                speak("Displayed on OLED")

        elif mode == "CHAT":
            answer = command.get("text", "")
            # Show trimmed version on OLED; speak full answer
            esp32_get("/display", {"text": answer[:OLED_MAX_CHARS]})
            print("AI Answer:", answer)
            speak(answer)

        else:
            print("Unknown command mode:", mode)