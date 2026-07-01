"""One-shot pyttsx3 synthesis worker (run as a subprocess).

pyttsx3 on Windows/SAPI5 deadlocks if a cached engine runs `save_to_file` +
`runAndWait` more than once in a process. Doing each synthesis in its own
short-lived process sidesteps that entirely.

Usage:  python tts_worker.py <out.wav>   # text is read (UTF-8) from stdin
"""

import sys


def main() -> int:
    out = sys.argv[1]
    text = sys.stdin.buffer.read().decode("utf-8")

    import pyttsx3
    engine = pyttsx3.init()
    engine.save_to_file(text, out)
    engine.runAndWait()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
