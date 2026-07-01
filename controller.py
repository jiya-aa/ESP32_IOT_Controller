"""Orchestration core: turn a command into hardware actions + a reply.

This is the seam a frontend plugs into. `handle_text()` and
`handle_audio()` return a plain, JSON-serialisable dict describing what was
heard, what the device did, and what to say back — with no printing, no
speaking, and no recording. The CLI (and a future web backend) decide how to
present that result.

Result shape:
    {
      "transcript": str,            # what the user said / typed
      "source": "keyword"|"gemini", # how it was interpreted
      "actions": [                  # one entry per hardware action attempted
        {"mode": str, "ok": bool, "detail": str, "text": str|None}
      ],
      "reply": str,                 # text to speak / display back
      "error": str|None,            # set when nothing could be done
    }
"""

from __future__ import annotations

import config
from esp32_client import ESP32Client


class Controller:
    def __init__(self, esp32: ESP32Client = None, assistant=None):
        self.esp32 = esp32 or ESP32Client()
        self._assistant = assistant  # lazily created so keyword-only use needs no API key

    @property
    def assistant(self):
        if self._assistant is None:
            from assistant import Assistant
            self._assistant = Assistant()
        return self._assistant

    # ── Public entry points ─────────────────────────────────────────────────
    def handle_audio(self, wav_path: str) -> dict:
        """Transcribe an audio file, then handle it as a text command."""
        from speech import transcribe
        return self.handle_text(transcribe(wav_path))

    def handle_text(self, text: str) -> dict:
        text = (text or "").strip()
        if not text:
            return self._result(text, "keyword", [], "", error="empty command")

        fast = self._keyword_actions(text)
        if fast is not None:
            return self._run_actions(text, "keyword", fast)

        actions = self.assistant.interpret(text)
        if actions is None:
            return self._result(
                text, "gemini", [],
                "Sorry, I could not reach the AI right now.",
                error="gemini_unavailable",
            )
        return self._run_actions(text, "gemini", actions)

    # ── Internals ───────────────────────────────────────────────────────────
    def _keyword_actions(self, text: str) -> list[dict] | None:
        """Fast path that skips the API for obvious commands. None = no match."""
        cmd = text.lower()
        # LED
        if "turn on led" in cmd or "led on" in cmd:
            return [{"mode": "LED_ON"}]
        if "turn off led" in cmd or "led off" in cmd:
            return [{"mode": "LED_OFF"}]
        # Relay
        if any(p in cmd for p in ("turn on relay", "relay on", "switch on relay", "activate relay")):
            return [{"mode": "RELAY_ON"}]
        if any(p in cmd for p in ("turn off relay", "relay off", "switch off relay", "deactivate relay")):
            return [{"mode": "RELAY_OFF"}]
        # Pump
        if any(p in cmd for p in ("turn on pump", "pump on", "start pump", "activate pump")):
            return [{"mode": "PUMP_ON"}]
        if any(p in cmd for p in ("turn off pump", "pump off", "stop pump", "deactivate pump")):
            return [{"mode": "PUMP_OFF"}]
        # OLED
        if cmd.startswith("display "):
            return [{"mode": "DISPLAY", "text": text[8:].strip()}]
        return None

    def _run_actions(self, text: str, source: str, actions: list[dict]) -> dict:
        results, replies = [], []
        for action in actions:
            mode = action.get("mode", "")

            if mode == "LED_ON":
                ok, detail = self.esp32.led_on()
                results.append({"mode": mode, "ok": ok, "detail": detail, "text": None})
                replies.append("LED turned on" if ok else detail)

            elif mode == "LED_OFF":
                ok, detail = self.esp32.led_off()
                results.append({"mode": mode, "ok": ok, "detail": detail, "text": None})
                replies.append("LED turned off" if ok else detail)

            elif mode == "RELAY_ON":
                ok, detail = self.esp32.relay_on()
                results.append({"mode": mode, "ok": ok, "detail": detail, "text": None})
                replies.append("Relay switched on" if ok else detail)

            elif mode == "RELAY_OFF":
                ok, detail = self.esp32.relay_off()
                results.append({"mode": mode, "ok": ok, "detail": detail, "text": None})
                replies.append("Relay switched off" if ok else detail)

            elif mode == "PUMP_ON":
                ok, detail = self.esp32.pump_on()
                results.append({"mode": mode, "ok": ok, "detail": detail, "text": None})
                replies.append("Pump started" if ok else detail)

            elif mode == "PUMP_OFF":
                ok, detail = self.esp32.pump_off()
                results.append({"mode": mode, "ok": ok, "detail": detail, "text": None})
                replies.append("Pump stopped" if ok else detail)

            elif mode == "DISPLAY":
                disp = action.get("text", "")
                ok, detail = (self.esp32.display(disp) if disp else (False, "no text"))
                results.append({"mode": mode, "ok": ok, "detail": detail, "text": disp})
                replies.append(f"Displayed: {disp}" if ok else detail)

            elif mode == "CHAT":
                answer = action.get("text", "")
                self.esp32.display(answer[:config.OLED_MAX_CHARS])
                results.append({"mode": mode, "ok": True, "detail": "chat", "text": answer})
                replies.append(answer)

            else:
                results.append({"mode": mode, "ok": False,
                                "detail": "unknown mode", "text": None})

        return self._result(text, source, results, " ".join(r for r in replies if r))

    @staticmethod
    def _result(transcript, source, actions, reply, error=None) -> dict:
        return {
            "transcript": transcript,
            "source": source,
            "actions": actions,
            "reply": reply,
            "error": error,
        }
