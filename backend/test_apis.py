import asyncio
import os
from dotenv import load_dotenv

load_dotenv()
from app.services.tts_service import synthesize_speech

async def main():
    print("Testing TTS...")
    audio = await synthesize_speech("नमस्ते, मेरा नाम जन वाणी है।", "hi")
    print(f"TTS result bytes length: {len(audio)}")
    if len(audio) == 0:
        print("TTS failed!")

if __name__ == "__main__":
    asyncio.run(main())
