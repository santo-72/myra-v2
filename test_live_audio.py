import asyncio
import os
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

async def main():
    client = genai.Client()
    config = types.LiveConnectConfig(
        response_modalities=["AUDIO"]
    )
    
    print("Connecting...")
    async with client.aio.live.connect(model="gemini-2.5-flash-native-audio-latest", config=config) as session:
        print("Connected! Sending 'Say hello in 3 words.'")
        await session.send(input="Say hello in 3 words.", end_of_turn=True)
        
        async for msg in session.receive():
            if msg.server_content and msg.server_content.model_turn:
                for part in msg.server_content.model_turn.parts:
                    if part.text:
                        print("Text:", part.text)
                    if part.inline_data:
                        print("Audio received! Data type:", type(part.inline_data.data), "Length:", len(part.inline_data.data))
            if msg.server_content and msg.server_content.turn_complete:
                print("Turn complete!")
                break

asyncio.run(main())
