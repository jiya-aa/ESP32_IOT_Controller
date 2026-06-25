import asyncio
import edge_tts

async def main():
    communicate = edge_tts.Communicate(
        "Hello Jayati, your AI assistant is working.",
        "en-US-AriaNeural"
    )

    await communicate.save("answer.wav")

asyncio.run(main())