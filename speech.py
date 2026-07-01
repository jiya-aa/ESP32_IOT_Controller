"""Speech-to-text and microphone capture.

Recording (PC microphone) and transcription (Whisper) are kept separate so
the audio *source* can change later — e.g. audio streamed from the ESP32's
MAX98357A — without touching the transcription path. The Whisper model is
loaded lazily so importing this module stays cheap for a web backend that
only needs to transcribe uploaded files.
"""

import scipy.io.wavfile as wav

import config

_model = None


def _get_model():
    global _model
    if _model is None:
        import whisper
        _model = whisper.load_model(config.WHISPER_MODEL)
    return _model


def record_to_file(path: str = "command.wav", seconds: float = None) -> str:
    """Record from the PC microphone to a WAV file and return its path."""
    import sounddevice as sd
    seconds = seconds or config.RECORD_SECONDS
    fs = config.SAMPLE_RATE
    audio = sd.rec(int(seconds * fs), samplerate=fs, channels=1, dtype="int16")
    sd.wait()
    wav.write(path, fs, audio)
    return path


def record(path: str = "command.wav", seconds: float = None, esp32=None) -> str:
    """Record from the configured source (PC mic or ESP32 mic) to `path`.

    If AUDIO_DEVICE=esp32 but the ESP32 is offline, logs a warning and falls
    back to the PC microphone so the voice loop keeps running.
    """
    if config.AUDIO_DEVICE == "esp32" and esp32 is not None:
        try:
            return esp32.record(seconds=seconds, path=path)
        except RuntimeError as e:
            print(f"  [warn] {e} — falling back to PC mic.")
    return record_to_file(path, seconds)


def transcribe(path: str) -> str:
    """Transcribe a WAV file to text. Works for any audio source."""
    result = _get_model().transcribe(path, fp16=False)
    return result["text"].strip()
