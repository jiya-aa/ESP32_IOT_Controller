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
🎤 Microphone
     │
     ▼  (5-second audio clip)
 Whisper STT  ──────────────────►  Text command
     │
     ▼
 Keyword check (fast path)        ──►  LED on/off, OLED display
     │  (no match)
     ▼
 Gemini 2.5 Flash  ──────────────►  JSON action or chat answer
     │
     ▼
 ESP32 HTTP Request  ────────────►  GPIO / OLED on physical hardware
     │
     ▼
 pyttsx3 TTS  ───────────────────►  Spoken response back to user
```

---

## 🔧 Hardware

| Component | Detail |
|-----------|--------|
| **ESP32 DevKit** | Any Wi-Fi-capable variant |
| **SSD1306 OLED 128×64** | I²C — SDA = GPIO 4, SCL = GPIO 15 |
| **On-board LED** | GPIO 2 (built-in) |

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

Open `esp32_sketch/esp32_sketch.ino` in the **Arduino IDE**.

**Install these libraries** via *Tools → Manage Libraries*:
- `Adafruit SSD1306`
- `Adafruit GFX Library`

Update the WiFi credentials in the sketch, then upload.  
After boot, open Serial Monitor (115200 baud) — the ESP32 will print its local IP.

### 2. Set Up Python

```bash
pip install sounddevice scipy openai-whisper pyttsx3 requests google-genai python-dotenv
```

> **FFmpeg is required by Whisper.**  
> Download from [ffmpeg.org](https://ffmpeg.org/download.html) and add it to your PATH (or set the path in `iot_control.py`).

### 3. Configure Your Secrets

```bash
# Copy the example file
cp .env.example .env
```

Edit `.env`:

```env
GEMINI_API_KEY=your_gemini_api_key_here
ESP32_IP=192.168.1.72        # ← your ESP32's IP from Serial Monitor
```

Get a free Gemini API key at [aistudio.google.com](https://aistudio.google.com/apikey).

### 4. Run

```bash
python iot_control.py
```

Say something. The program listens for 5 seconds, transcribes, acts.

---

## 🗣️ Voice Commands

| What you say | What happens |
|-------------|--------------|
| `"turn on LED"` / `"LED on"` | GPIO 2 → HIGH |
| `"turn off LED"` / `"LED off"` | GPIO 2 → LOW |
| `"display Good morning"` | Scrolls text on OLED |
| *Any question or command* | Gemini answers → spoken aloud + shown on OLED |
| `"exit"` / `"quit"` / `"stop"` | Gracefully exits |

---

## 📁 Project Structure

```
esp32_ai/
├── iot_control.py              ← Main voice-control loop
├── esp32_sketch/
│   └── esp32_sketch.ino        ← ESP32 Arduino firmware
│
├── .env                        ← Your secrets (⛔ never commit this)
├── .env.example                ← Safe-to-commit template
│
├── mic_test.py                 ← Sanity-check your microphone
├── voice_test.py               ← Record → Whisper transcription test
├── speaker_test.py             ← pyttsx3 TTS test
├── new_test.py                 ← edge-tts (higher-quality voice) test
├── test_gemini2.py             ← Gemini API JSON response test
└── server.py                   ← Minimal static HTTP server

```


## 🛠️ Troubleshooting

| Symptom | Fix |
|---------|-----|
| `OLED init failed` in Serial Monitor | Check SDA/SCL wiring and I²C address (try `0x3C` vs `0x3D`) |
| Whisper prints `FP16 warning` | Already fixed — `fp16=False` is set |
| `Gemini unavailable` after 3 retries | Check your API key and internet connection |
| ESP32 IP not reachable | Make sure PC and ESP32 are on the same Wi-Fi network |
| No audio recorded | Run `mic_test.py` to verify your microphone device index |

---

## 📦 Dependencies

| Package | Purpose |
|---------|---------|
| `openai-whisper` | Speech-to-text (runs locally) |
| `sounddevice` + `scipy` | Audio recording |
| `google-genai` | Gemini 2.5 Flash API |
| `pyttsx3` | Offline text-to-speech |
| `requests` | HTTP calls to ESP32 |
| `python-dotenv` | Load `.env` secrets automatically |

---

## 📄 License

MIT — do whatever you like, just don't blame me if your LED stays on. 💡
