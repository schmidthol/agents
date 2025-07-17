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
gemini_flash_model = genai.GenerativeModel('gemini-1.5-flash')
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
    Analysiere den folgenden HTML-Code einer Webseite auf Verletzungen der WCAG 2.1 Kriterien, insbesondere in Bezug auf semantisches Verständnis und Kontext.
    Konzentriere dich auf folgende Aspekte:
    - **1.1.1 Nicht-Text-Inhalt (alt-Texte):** Sind alle informativen Bilder mit aussagekräftigen alt-Texten versehen? Gibt es generische oder fehlende alt-Texte?
    - **1.3.1 Info und Beziehungen:** Ist die Überschriftenhierarchie (`h1`-`h6`) logisch und konsistent? Werden Listen (`ul`, `ol`) und Tabellen (`table`, `th`) korrekt verwendet? Sind Formularfelder (`input`, `select`, `textarea`) korrekt mit `<label>`-Elementen verknüpft? Werden HTML5 semantische Elemente (`header`, `nav`, `main`, `footer`) oder ARIA-Landmarks sinnvoll eingesetzt?
    - **2.4.4 Linkzweck (Im Kontext):** Sind Linktexte aussagekräftig und verständlich aus dem Kontext heraus? Gibt es generische Linktexte wie "hier klicken" oder "mehr"?
    - **4.1.2 Name, Rolle, Wert:** Haben interaktive Elemente (Buttons, Links, Formularfelder) einen programmatisch bestimmbaren Namen, eine Rolle und einen Wert? Werden ARIA-Attribute korrekt und sinnvoll verwendet?

    Identifiziere spezifische Verletzungen und schlage konkrete, codebasierte Korrekturen vor.
    Formatiere deine Antwort als eine Liste von JSON-Objekten, wobei jedes Objekt ein Problem darstellt.

    Beispiel-JSON-Struktur für ein Problem:
    ```json
    {{
        "wcag_kriterium": "1.1.1 Nicht-Text-Inhalt",
        "beschreibung": "Fehlender oder unzureichender Alt-Text für ein informatives Bild.",
        "html_ausschnitt": "<img src=\"logo.png\">",
        "vorschlag": "<img src=\"logo.png\" alt=\"Firmenlogo von Beispiel GmbH\">",
        "schweregrad": "Kritisch",
        "kontext": "Logo im Header-Bereich der Webseite."
    }}
    ```

    Hier ist der HTML-Code zur Analyse:
    ```html
    {html_content} # <--- Hier wird der html_content in den Prompt-String eingefügt
    ```
    """

    # 3. LLM-Anfrage senden
    try:
        print("Sende Anfrage an Gemini Flash 1.5...")
        response = await gemini_flash_model.generate_content(
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


