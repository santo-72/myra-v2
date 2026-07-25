from google import genai
import os
from dotenv import load_dotenv

load_dotenv()
client = genai.Client()

print("Listing models supporting bidiGenerateContent:")
for m in client.models.list():
    if m.supported_actions and 'bidiGenerateContent' in m.supported_actions:
        print(f"Found model: {m.name}")
    elif 'bidiGenerateContent' in str(m):
        print(f"Found model (fallback check): {m.name}")
    elif 'gemini-2' in m.name:
        print(f"Gemini 2 model: {m.name} - Actions: {m.supported_actions}")
