"""HTTP client for the ESP32 hardware.

Thin wrapper around the ESP32's REST endpoints. Every method returns a
(ok, detail) tuple so callers — CLI or web backend — can report results
without catching exceptions themselves.
"""

from __future__ import annotations

import requests

import config


class ESP32Client:
    def __init__(self, base_url: str = None, timeout: float = None):
        self.base_url = (base_url or config.ESP32_URL).rstrip("/")
        self.timeout = timeout or config.ESP32_TIMEOUT

    def _get(self, path: str, params: dict = None) -> tuple[bool, str]:
        try:
            r = requests.get(f"{self.base_url}{path}", params=params,
                             timeout=self.timeout)
            return True, r.text
        except Exception as e:
            return False, f"ESP32 error ({path}): {e}"

    def led_on(self) -> tuple[bool, str]:
        return self._get("/led/on")

    def led_off(self) -> tuple[bool, str]:
        return self._get("/led/off")

    def display(self, text: str) -> tuple[bool, str]:
        text = text[:config.OLED_MAX_CHARS]
        return self._get("/display", {"text": text})

    # ── Audio (INMP441 mic / MAX98357A speaker) ─────────────────────────────
    def record(self, seconds: float = None, path: str = "command.wav") -> str:
        """Record from the ESP32 mic and save the streamed WAV to `path`.

        Raises RuntimeError if the ESP32 is unreachable so callers can decide
        whether to fall back to the PC mic.
        """
        seconds = seconds or config.RECORD_SECONDS
        try:
            r = requests.get(
                f"{self.base_url}/record",
                params={"seconds": int(seconds)},
                stream=True,
                timeout=seconds + 10,
            )
            r.raise_for_status()
            with open(path, "wb") as f:
                for chunk in r.iter_content(chunk_size=4096):
                    if chunk:
                        f.write(chunk)
            return path
        except Exception as e:
            raise RuntimeError(f"ESP32 record failed: {e}") from e

    def play_pcm(self, pcm: bytes) -> tuple[bool, str]:
        """Stream raw 16 kHz / 16-bit / mono PCM to the ESP32 speaker."""
        # Playback runs in real time on the device, so allow the clip duration.
        duration = len(pcm) / (config.SAMPLE_RATE * 2)
        try:
            r = requests.post(
                f"{self.base_url}/play",
                files={"audio": ("reply.pcm", pcm, "application/octet-stream")},
                timeout=duration + 10,
            )
            return True, r.text
        except Exception as e:
            return False, f"ESP32 error (/play): {e}"
