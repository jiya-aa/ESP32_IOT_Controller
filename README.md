<div align="center">

# 🎙️ ESP32 AI Voice Controller

**Talk to your home. Your ESP32 listens.**

A voice-controlled IoT assistant that pipes your speech through
**OpenAI Whisper** → **Google Gemini 2.5 Flash** → **ESP32 HTTP server**
to control real hardware with natural language.

![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)
![ESP32](https://img.shields.io/badge/ESP32-Arduino-E7352C?style=for-the-badge&logo=arduino&logoColor=white)
![Gemini](https://img.shields.io/badge/Gemini-2.5%20Flash-4285F4?style=for-the-badge&logo=google&logoColor=white)
![Whisper](https://img.shields.io/badge/Whisper-STT-412991?style=for-the-badge&logo=openai&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-22c55e?style=for-the-badge)

</div>

---

## ✨ How It Works

```
🎤 Microphone (PC or ESP32 INMP441)
     │
     ▼  (WAV clip)
 Whisper STT  ──────────────────────►  Text command
     │
     ▼
 Keyword check (fast path)           ──►  LED on/off, OLED display
     │  (no match)
     ▼
 Gemini 2.5 Flash  ─────────────────►  JSON action or chat answer
     │
     ▼
 ESP32 HTTP Request  ───────────────►  GPIO / OLED / I2S speaker
     │
     ▼
 TTS (PC speaker or ESP32 MAX98357A) ►  Spoken response
```

---

## 🏗️ Architecture

The project is split into clean, reusable modules:

```
iot_control.py         ← CLI entry point (thin voice loop)
    ↓
controller.py          ← Orchestration core — pluggable into a web backend
    ├── assistant.py       ← Gemini AI interpreter (returns structured JSON actions)
    ├── esp32_client.py    ← HTTP client for the ESP32 REST API
    ├── speech.py          ← STT + microphone (Whisper, PC or ESP32 mic)
    └── tts.py             ← TTS (pyttsx3 local or streamed PCM to ESP32 speaker)
            └── tts_worker.py  ← Subprocess to avoid pyttsx3/SAPI5 deadlock on Windows

config.py              ← Central config (loads .env, validates secrets)
requirements.txt       ← Python dependencies
```

---

## 🔧 Hardware

| Component | Detail |
|-----------|--------|
| **ESP32 DevKit** | Any Wi-Fi-capable variant |
| **SSD1306 OLED 128×64** | I²C — SDA = GPIO 4, SCL = GPIO 15 |
| **INMP441 mic** *(optional)* | I2S mic — BCLK=26, WS=25, SD=32, L/R=17 |
| **MAX98357A amp** *(optional)* | I2S amp — BCLK=14, LRC=27, DIN=33 |
| **On-board LED** | GPIO 2 (built-in) |

> The mic and speaker are optional. Without them the system uses your PC's microphone and speakers (`AUDIO_DEVICE=pc`, the default).

### Wiring (OLED)

```
ESP32 3.3V  ──►  OLED VCC
ESP32 GND   ──►  OLED GND
GPIO 4      ──►  OLED SDA
GPIO 15     ──►  OLED SCL
```

---

## 🚀 Quick Start

### 1. Flash the ESP32

```
esp32_sketch/
├── esp32_sketch.ino
├── secrets.h.example   ← copy this to secrets.h and fill in your WiFi creds
└── secrets.h           ← gitignored, never committed
```

Open `esp32_sketch/esp32_sketch.ino` in **Arduino IDE**.

**Install libraries** via *Tools → Manage Libraries*:
- `Adafruit SSD1306`
- `Adafruit GFX Library`

After boot, open Serial Monitor at 115200 baud to see the IP address.  
A **440 Hz beep** on startup confirms the I2S speaker is wired correctly.

### 2. Set Up Python

```bash
pip install -r requirements.txt
```

> **FFmpeg is required by Whisper.** Download from [ffmpeg.org](https://ffmpeg.org/download.html) and either add to PATH or set `FFMPEG_PATH` in `.env`.

### 3. Configure Secrets

```bash
cp .env.example .env
```

Edit `.env`:

```env
GEMINI_API_KEY=your_gemini_api_key_here
ESP32_IP=192.168.1.72        # ← your ESP32's IP from Serial Monitor
FFMPEG_PATH=C:\path\to\ffmpeg\bin   # optional, if not on PATH

# Audio routing: "pc" (default) or "esp32" (INMP441 mic + MAX98357A speaker)
AUDIO_DEVICE=pc
```

Get a free API key at [aistudio.google.com](https://aistudio.google.com/apikey).

### 4. Run

```bash
python iot_control.py
```

---

## 🗣️ Voice Commands

| What you say | What happens |
|-------------|--------------|
| `"turn on LED"` / `"LED on"` | GPIO 2 → HIGH (fast path, no API call) |
| `"turn off LED"` / `"LED off"` | GPIO 2 → LOW (fast path, no API call) |
| `"display Good morning"` | Scrolls text on OLED (fast path) |
| *Any question or command* | Sent to Gemini → answer spoken + shown on OLED |
| `"exit"` / `"quit"` / `"stop"` | Gracefully exits |

---

## 📁 Project Structure

```
esp32_ai/
├── iot_control.py              ← Main voice-control CLI loop
├── controller.py               ← Orchestration core (reusable by a web backend)
├── assistant.py                ← Gemini AI natural-language interpreter
├── esp32_client.py             ← HTTP client for the ESP32
├── speech.py                   ← STT + microphone recording
├── tts.py                      ← Text-to-speech (PC or ESP32 speaker)
├── tts_worker.py               ← Subprocess helper for pyttsx3
├── config.py                   ← Centralised configuration
├── requirements.txt            ← Python dependencies
│
├── esp32_sketch/
│   ├── esp32_sketch.ino        ← ESP32 Arduino firmware
│   ├── secrets.h.example       ← WiFi credentials template
│   └── secrets.h               ← Your real creds (gitignored)
│
├── .env                        ← Your secrets (⛔ never commit)
├── .env.example                ← Safe-to-commit template
├── .gitignore
│
├── esp32_audio_test.py         ← Test ESP32 mic + speaker independently
├── mic_test.py                 ← PC microphone sanity check
├── voice_test.py               ← Record → Whisper transcription test
├── speaker_test.py             ← pyttsx3 TTS test
└── new_test.py                 ← edge-tts (higher-quality voice) test
```

---

## 🔌 ESP32 REST API

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/led/on` | Turn on GPIO 2 LED |
| GET | `/led/off` | Turn off GPIO 2 LED |
| GET | `/display?text=...` | Show scrolling text on OLED |
| GET | `/record?seconds=N` | Stream WAV from INMP441 mic (1–10 s) |
| POST | `/play` | Receive raw 16 kHz/16-bit PCM → play via MAX98357A |
| GET | `/tone` | Play a 440 Hz diagnostic beep |


## 🛠️ Troubleshooting

| Symptom | Fix |
|---------|-----|
| `OLED init failed` in Serial Monitor | Check SDA/SCL wiring; try I²C address `0x3D` |
| No beep on boot | Check MAX98357A BCLK/LRC/DIN wiring |
| Whisper FP16 warning | Already fixed — `fp16=False` is set |
| `Gemini unavailable` after 3 retries | Check API key and internet connection |
| ESP32 not reachable | Ensure PC and ESP32 are on the same Wi-Fi network |
| No audio recorded | Run `mic_test.py` to verify your PC microphone |
| ESP32 mic not working | Run `python esp32_audio_test.py record 3` and play back `test.wav` |
| Wrong pitch from ESP32 speaker | Sample-rate mismatch — check `AUDIO_RATE` in sketch matches `SAMPLE_RATE` in `.env` |

---

## 📦 Dependencies

| Package | Purpose |
|---------|---------|
| `openai-whisper` | Speech-to-text (runs locally) |
| `sounddevice` + `scipy` | Audio recording + WAV handling |
| `numpy` | PCM buffer math for ESP32 audio |
| `google-genai` | Gemini 2.5 Flash API |
| `pyttsx3` | Offline text-to-speech |
| `edge-tts` | Higher-quality online TTS |
| `requests` | HTTP calls to ESP32 |
| `python-dotenv` | Load `.env` secrets automatically |

---

## 📄 License

MIT — do whatever you like, just don't blame me if your LED stays on. 💡
