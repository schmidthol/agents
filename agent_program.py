import os
import asyncio
from dotenv import load_dotenv
#from google.adk import agent
import google.generativeai as genai
from helper_tools import read_html_accessibility_tree
from google.adk.agents import Agent



# Load Gemini API Key
load_dotenv()

api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    raise ValueError("GOOGLE_API_KEY Umgebungsvariable ist nicht gesetzt. Bitte setze sie.")

genai.configure(api_key=api_key)

# Initialisiere das Gemini Flash 1.5 Modell
# Der Modellname für Gemini Flash 1.5 ist in der Regel "gemini-1.5-flash-latest" oder "gemini-1.5-flash".
# Überprüfe die aktuelle Dokumentation für den genauen und empfohlenen Modellnamen.
gemini_flash_model = genai.GenerativeModel('gemini-2.5-flash-preview-05-20')
# Optional: Setze hier weitere Konfigurationen wie safety_settings
# gemini_flash_model = genai.GenerativeModel(
#     'gemini-1.5-flash',
#     safety_settings=[
#         {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
#         # ... weitere Kategorien
#     ]
# )
"""Coroutinen sind der Baustein der asynchronen Programmierung in Python (asyncio). 
Sie ermöglichen es, I/O-intensive Operationen (wie Netzwerkaufrufe, Datenbankabfragen, 
Dateizugriffe) effizienter zu handhaben, indem sie die CPU nicht blockieren, 
während auf externe Operationen gewartet wird.
async def: Eine Funktion wird zu einer Coroutine, 
indem sie mit dem Schlüsselwort async def definiert wird.
Das Schlüsselwort await wird innerhalb einer Coroutine verwendet, 
um die Ausführung an einem bestimmten Punkt anzuhalten und die Kontrolle an die Event-Loop zurückzugeben. 
Die Event-Loop kann dann andere Coroutinen ausführen, die bereit sind. 
Sobald die Operation, auf die await gewartet hat, abgeschlossen ist 
(z.B. Daten von einem Netzwerk empfangen wurden), wird die Coroutine genau an dieser Stelle fortgesetzt.
Funktionen, die mit async definiert sind, müssen später im Programm auch mit dem await Zusatz aufgerufen werden.
"""

async def wcag_analyst_agent(url: str) -> str:
    """
    Analysiert den HTML-Code einer Webseite auf WCAG-Verletzungen (Semantik und Kontext)
    mithilfe eines LLM (Google Gemini Flash 1.5).
    """
    print(f"Abrufen des HTML-Codes für: {url}")
    # 1. HTML-Code abrufen
    # Wähle hier die korrekte Methode basierend auf deiner Implementierung:
    # html_content = await read_html_from_url(url) # Für statischen HTML-Code
    html_content = await read_html_accessibility_tree.read_dynamic_html_from_url(url) # Für dynamischen HTML-Code

    #if "Fehler" in html_content:
    #    print(f"Fehler beim Abrufen des HTML-Codes: {html_content}")
    #    return html_content # Fehler vom Tool weitergebe

    print("HTML-Code erfolgreich abgerufen. Erstelle Prompt für LLM...")
    # 2. Prompt für das LLM erstellen
    # Dies ist der entscheidende Teil für deine Analyse. Sei hier sehr präzise!
    prompt = f"""
    Analysiere den folgenden HTML-Code einer Webseite auf Verletzungen der WCAG 2.1 Kriterien, insbesondere in Bezug auf semantisches Verständnis und Kontext.
    Konzentriere dich auf folgende Aspekte:
    - 1.1.1 Nicht-Text-Inhalt (A)
    - 1.3.1 Info und Beziehungen (A)
    - 1.3.2 Bedeutungstragende Reihenfolge (A)
    - 1.3.3 Sensorische Eigenschaften (A)
    - 1.3.5 Bestimmung des Eingabezwecks (AA)
    - 2.4.1 Blöcke umgehen (A)
    - 2.4.4 Linkzweck (Im Kontext) (A)
    - 2.4.5 Verschiedene Methoden (AA)
    - 2.4.6 Überschriften und Beschriftungen (Labels) AA
    - 2.5.3 Beschriftung (Label) im Namen (A)
    - 3.2.3 Konsistente Navigation (A)
    - 3.2.4 Konsistente Erkennung (A)
    - 3.3.3 Fehlerempfehlung (AA)
    - 4.1.2 Name, Rolle, Wert (A)

    Identifiziere spezifische WCAG Verletzungen und setzen in Klammern die Konformitätsstufe (A oder AA) dahinter .
    Gib die Anzahl der WCAG Verletzungen wider.
    Nenne die Konformitätsstufe der Verletzung.
    Beschreibe in wenigen Worten die Verletzung.
    Nenne den HTML Ausschnitt, in dem die Verletzung vorkommt.
    Schlage eine konkrete, codebasierte Korrektur vor und beschränke dich dabei auf das Wesentliche.  
    Gib die Änderung zusätzlich einzeln aus.
    Beschreibe die Funktion bzw. Rolle des HTML-Elements im Kontext der gesamten Webseite.
    Berücksichtige auch zuvor aufgerufene Webseiten.
    Formatiere deine Antwort als eine Liste von JSON-Objekten.
    Jedes Objekt stellt ein verletztes WCAG Kriterium dar.
    Die Namen-Objekt-Paare in der JSON-Struktur sollen untereinander stehen.
    Die Beispiele innerhalb eines Namen-Objekt-Paares sollen untereinander stehen.

    Beispiel-JSON-Struktur für ein Problem:
    ```json
    {{
        "Verletztes WCAG_kriterium": "1.1.1 Nicht-Text-Inhalt" (A),
        "Anzahl der Verletzungen": "4",
        "Beschreibung der Verletzung": "Fehlender oder unzureichender Alt-Text für ein informatives Bild.",
        "Html Ausschnitt auf Webseite": "<img src=\"logo.png\">",
        "Änderungsvorschlag": "<img src=\"logo.png\" alt=\"Firmenlogo von der Firma Otto\">",
        "Änderungen einzeln": "alt=\"Firmenlogo von Beispiel GmbH\",
        "Funktion/Rolle des Elements im Kontext der Webseite ": "Logo im Header-Bereich der Webseite."
    
    ```

    Hier ist der HTML-Code zur Analyse:
    ```html
    {html_content} # <--- Hier wird der html_content in den Prompt-String eingefügt
    ```
    """

    # 3. LLM-Anfrage senden
    try:
        print("Sende Anfrage an Gemini Flash 2.5...")
        response = gemini_flash_model.generate_content(
            contents=[prompt],
            # Tools können hier hinzugefügt werden, wenn Gemini Flash 1.5 sie direkt unterstützt
            # und dein Prompt so formuliert ist, dass es die Tools aufruft.
            # Für die reine HTML-Analyse wie hier sind sie oft nicht direkt notwendig.
            # tools=[read_html_from_url], # Wenn du Tools über das LLM steuern möchtest
            generation_config={"response_mime_type": "application/json"} # Versuche JSON-Ausgabe zu erzwingen
        )
        
        # Der Zugriff auf die Text-Antwort hängt von der Konfiguration ab
        # Wenn response_mime_type gesetzt ist, sollte response.text funktionieren
        print("Antwort vom LLM erhalten. Extrahiere Text...")
        return response.text
    except Exception as e:
        print(f"Fehler bei der LLM-Analyse: {e}")
        return f"Fehler bei der LLM-Analyse: {e}"


