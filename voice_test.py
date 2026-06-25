import os

os.environ["PATH"] += os.pathsep + r"C:\Users\Jayati\Downloads\ffmpeg-8.1.1-essentials_build\ffmpeg-8.1.1-essentials_build\bin"

import sounddevice as sd
import scipy.io.wavfile as wav
import whisper

fs = 16000

print("Speak now...")

audio = sd.rec(
    int(5 * fs),
    samplerate=fs,
    channels=1,
    dtype="int16"
)

sd.wait()

wav.write("command.wav", fs, audio)

print("Transcribing...")

model = whisper.load_model("base")
result = model.transcribe("command.wav", fp16=False)

print("You said:")
print(result["text"])