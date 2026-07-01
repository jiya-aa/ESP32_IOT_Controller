"""Voice-control CLI loop.

Thin presentation layer over the reusable core in `controller.py`:
record → transcribe → handle → speak. All the logic lives in the modules
(config, esp32_client, assistant, speech, tts, controller) so the same core
can back a web frontend later without change.
"""

import config
import speech
import tts
from controller import Controller

EXIT_WORDS = ("exit", "quit", "stop")


def main() -> None:
    # Fail loudly now rather than mid-conversation if the key is missing.
    config.require_api_key()

    controller = Controller()
    print(f"Ready. Talking to ESP32 at {config.ESP32_URL} "
          f"(audio: {config.AUDIO_DEVICE}).  Say 'exit' to quit.")

    try:
        while True:
            print("\nSpeak now...")
            speech.record("command.wav", esp32=controller.esp32)
            transcript = speech.transcribe("command.wav")

            if not transcript:
                continue
            print("You said:", transcript)

            if transcript.lower() in EXIT_WORDS:
                print("Goodbye!")
                tts.speak("Goodbye!", esp32=controller.esp32)
                break

            result = controller.handle_text(transcript)

            if result["error"] == "gemini_unavailable":
                print("Gemini unavailable or quota exhausted.")
            for action in result["actions"]:
                flag = "[ok]" if action["ok"] else "[x]"
                print(f"  {flag} {action['mode']}: {action['detail']}")

            tts.speak(result["reply"], esp32=controller.esp32)
    except KeyboardInterrupt:
        print("\nInterrupted. Goodbye!")


if __name__ == "__main__":
    main()
