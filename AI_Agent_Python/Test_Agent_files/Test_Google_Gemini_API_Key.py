import os
from dotenv import load_dotenv
import google.generativeai as genai

# Load Gemini API Key
load_dotenv()

api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    raise ValueError("GOOGLE_API_KEY Umgebungsvariable ist nicht gesetzt. Bitte setze sie.")

genai.configure(api_key=api_key)
print(api_key)
