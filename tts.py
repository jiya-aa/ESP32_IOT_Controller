"""Text-to-speech output.

Two sinks, chosen by `config.AUDIO_DEVICE`:
  - "pc"    → speak locally through pyttsx3 (PC speaker).
  - "esp32" → synthesize on the PC, then stream 16 kHz/16-bit/mono PCM to the
              ESP32's MAX98357A amplifier.

The TTS engine is created lazily so a web backend that only returns text never
spins it up.
"""

import math
import os
import subprocess
import sys
import tempfile

import numpy as np
import scipy.io.wavfile as wav
from scipy.signal import resample_poly

import config

_WORKER = os.path.join(os.path.dirname(__file__), "tts_worker.py")

_engine = None


def _get_engine():
    global _engine
    if _engine is None:
        import pyttsx3
        _engine = pyttsx3.init()
    return _engine


def speak_local(text: str) -> None:
    """Speak through the PC speaker."""
    if not text:
        return
    engine = _get_engine()
    engine.say(text)
    engine.runAndWait()


def synthesize_pcm(text: str, rate: int = None) -> bytes:
    """Render `text` to raw mono 16-bit PCM at `rate` (default config.SAMPLE_RATE).

    pyttsx3 writes a WAV at the voice's native rate; we down/up-sample it to the
    fixed rate the ESP32 I2S speaker expects.
    """
    rate = rate or config.SAMPLE_RATE
    tmp = os.path.join(tempfile.gettempdir(), "esp32_reply.wav")

    # Synthesize in a fresh subprocess — pyttsx3 deadlocks on a 2nd save_to_file
    # in the same process, which would freeze the loop on the 2nd reply.
    try:
        subprocess.run(
            [sys.executable, _WORKER, tmp],
            input=text.encode("utf-8"),
            check=True,
            timeout=60,
        )
    except FileNotFoundError:
        raise RuntimeError(
            f"tts_worker.py not found at '{_WORKER}'. "
            "Make sure you are running from the project directory."
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"TTS worker failed (exit {e.returncode}).") from e

    src_rate, data = wav.read(tmp)
    if data.ndim > 1:                       # stereo → mono
        data = data.mean(axis=1)
    data = data.astype(np.float32)

    if src_rate != rate:                    # resample to the target rate
        g = math.gcd(int(src_rate), int(rate))
        data = resample_poly(data, rate // g, src_rate // g)

    pcm = np.clip(data, -32768, 32767).astype("<i2")
    return pcm.tobytes()


def speak(text: str, esp32=None) -> None:
    """Speak `text` via the configured sink.

    If ESP32 audio synthesis fails, falls back to the local PC speaker.
    """
    if not text:
        return
    if config.AUDIO_DEVICE == "esp32" and esp32 is not None:
        try:
            esp32.play_pcm(synthesize_pcm(text))
            return
        except RuntimeError as e:
            print(f"  [warn] ESP32 TTS failed ({e}), falling back to PC speaker.")
    speak_local(text)
