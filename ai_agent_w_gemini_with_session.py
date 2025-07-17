import asyncio 
import agent_program
from google.adk.agents import Agent
from google.adk.tools import google_search  # Import the tool
import json
import os

output_filename = "wcag_analysis_results.json"
output_directory = "output_directory"
output_filepath = os.path.join(output_directory, output_filename)

async def output(result):
   try:
      # 1. Den JSON-String in ein Python-Objekt (Liste/Dictionary) parsen
      # json.loads() erwartet einen String als Eingabe
      parsed_json_data = json.loads(result)

      # 2. Das Python-Objekt als JSON-Datei speichern
      # 'with open(...) as f:' stellt sicher, dass die Datei ordnungsgemäß geschlossen wird
      # 'w' steht für write-Modus
      # 'indent=4' formatiert die Ausgabe leserlich mit 4 Leerzeichen Einrückung
      # 'ensure_ascii=False' erlaubt die Speicherung von Nicht-ASCII-Zeichen (z.B. Umlaute) direkt
      with open(output_filepath, 'w', encoding='utf-8') as json_file:
         json.dump(parsed_json_data, json_file, indent=4, ensure_ascii=False)

      print(f"JSON-Daten erfolgreich in '{output_filepath}' gespeichert.")

   except json.JSONDecodeError as e:
      print(f"Fehler beim Parsen des JSON-Strings: {e}")
   except IOError as e:
      print(f"Fehler beim Schreiben der Datei: {e}")
   except Exception as e:
      print(f"Ein unerwarteter Fehler ist aufgetreten: {e}")

"""
@agent
root_agent = Agent(
   # A unique name for the agent.
   name="basic_search_agent",
   # The Large Language Model (LLM) that agent will use.
   model="gemini-2.5-flash-exp",
   # model="gemini-2.5-flash-live-001",  # New streaming model version as of Feb 2025
   # A short description of the agent's purpose.
   description="Agent to answer questions using Google Search.",
   # Instructions to set the agent's behavior.
   instruction="You are an expert researcher. You always stick to the facts.",
   # Add google_search tool to perform grounding with Google search.
   tools=[google_search]
)
"""

# 1. Mache 'main' zu einer asynchronen Funktion
async def main():
    print("Starte WCAG-Analyse für die Webseite..")
    # 2. Rufe wcag_analyst_agent mit 'await' auf
    result = await agent_program.wcag_analyst_agent("https://www.otto.de/p/homecall-campingstuhl-hochlehner-klappstuhl-gartenstuhl-angelstuhl-angenehme-polsterung-bis-150kg-mit-hoher-rueckenlehne-armlehne-getraenkehalter-1-st-fuer-camp-garten-balkon-S007E0D0/#variationId=S007E0D08EDP")
    print("\n--- Analyse-Ergebnis ---")
    print(result)
    await output(result)
    

if __name__ == "__main__":
    # 3. Führe die asynchrone 'main'-Funktion mit asyncio.run() aus
    asyncio.run(main())

   
