"""Test the ESP32 audio path independently of the full voice loop.

Usage:
    python esp32_audio_test.py record [seconds] [out.wav]
        Record from the ESP32's INMP441 mic and save a WAV. Play it back on the
        PC to confirm the mic works. If it's too quiet/loud, tune MIC_SHIFT in
        esp32_sketch.ino (lower = louder).

    python esp32_audio_test.py play "some text to speak"
        Synthesize on the PC and play it through the ESP32's MAX98357A speaker.
        Wrong pitch => sample-rate mismatch between PC and firmware.

Requires ESP32_IP in .env (or the environment).
"""

import sys

import config
from esp32_client import ESP32Client


def main(argv: list[str]) -> int:
    if not argv or argv[0] not in ("record", "play"):
        print(__doc__)
        return 1

    client = ESP32Client()
    print(f"ESP32 at {config.ESP32_URL}")

    if argv[0] == "record":
        seconds = float(argv[1]) if len(argv) > 1 else config.RECORD_SECONDS
        out = argv[2] if len(argv) > 2 else "test.wav"
        print(f"Recording {seconds:g}s from the ESP32 mic...")
        path = client.record(seconds=seconds, path=out)
        import os
        print(f"Saved {os.path.getsize(path)} bytes to {path}. "
              f"Play it to verify the mic.")
        return 0

    # play
    text = argv[1] if len(argv) > 1 else "hello from the E S P 32"
    import tts
    pcm = tts.synthesize_pcm(text)
    print(f"Streaming {len(pcm)} bytes of PCM to the ESP32 speaker...")
    ok, detail = client.play_pcm(pcm)
    print("OK" if ok else f"FAILED: {detail}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
