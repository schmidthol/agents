import os
import json
from datetime import datetime
import time
import asyncio
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
from playwright.async_api import async_playwright
import google.generativeai as genai
from pydantic import BaseModel # Für Agenten-Input-Modell, falls das ADK verwendet wird
#from google import genai
#from google.genai import types


# --- Konfiguration ---
# API-Schlüssel für Google Gemini (aus Umgebungsvariablen laden)
load_dotenv()
GOOGLE_API_KEY = "none" #os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY Umgebungsvariable ist nicht gesetzt. Bitte setze sie.")
genai.configure(api_key=GOOGLE_API_KEY)
GEMINI_MODEL = genai.GenerativeModel('gemini-2.5-pro') # Oder 'gemini-1.5-pro' für komplexere Analysen

prompt_text="Wie heißt die Hauptstadt von Deutschland?"
response = GEMINI_MODEL.generate_content(
            contents=[prompt_text],
            generation_config={"response_mime_type": "application/json", "temperature": 0.1}
        )

print(response)
