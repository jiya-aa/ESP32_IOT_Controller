"""Central configuration: loads .env, validates secrets, exposes settings.

Importing this module has no side effects beyond reading environment
variables, so it is safe to import from a CLI loop or a web backend alike.
"""

import os

# Auto-load .env from the project folder (no shell setup needed).
try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))
except ImportError:
    pass  # python-dotenv not installed; fall back to shell env vars


# ── Secrets / endpoints ─────────────────────────────────────────────────────
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
ESP32_IP       = os.environ.get("ESP32_IP", "192.168.1.72").strip()
ESP32_URL      = f"http://{ESP32_IP}"

# ── Audio / model settings ──────────────────────────────────────────────────
SAMPLE_RATE     = int(os.environ.get("SAMPLE_RATE", "16000"))
RECORD_SECONDS  = float(os.environ.get("RECORD_SECONDS", "5"))
WHISPER_MODEL   = os.environ.get("WHISPER_MODEL", "base")
OLED_MAX_CHARS  = int(os.environ.get("OLED_MAX_CHARS", "80"))
ESP32_TIMEOUT   = float(os.environ.get("ESP32_TIMEOUT", "3"))

# Where audio is captured/played: "pc" (local mic + speaker) or "esp32"
# (INMP441 mic + MAX98357A speaker over HTTP). Default keeps the PC path.
AUDIO_DEVICE    = os.environ.get("AUDIO_DEVICE", "pc").strip().lower()

# ── ffmpeg (required by Whisper) ────────────────────────────────────────────
# Set FFMPEG_PATH in .env to the folder containing ffmpeg.exe if it is not
# already on your system PATH. No machine-specific default is baked in.
FFMPEG_PATH = os.environ.get("FFMPEG_PATH", "").strip()
if FFMPEG_PATH and FFMPEG_PATH not in os.environ.get("PATH", ""):
    os.environ["PATH"] += os.pathsep + FFMPEG_PATH


def require_api_key() -> str:
    """Return the Gemini API key or raise loudly if it is missing."""
    if not GEMINI_API_KEY or GEMINI_API_KEY == "your_gemini_api_key_here":
        raise RuntimeError(
            "GEMINI_API_KEY is not set. Copy .env.example to .env and add your "
            "key (get one free at https://aistudio.google.com/apikey)."
        )
    return GEMINI_API_KEY
