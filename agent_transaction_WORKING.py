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
GOOGLE_API_KEY = "AIzaSyC2U4wVDLxpDcbcn2Q3zHqss2_zVet54TU" #os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY Umgebungsvariable ist nicht gesetzt. Bitte setze sie.")
genai.configure(api_key=GOOGLE_API_KEY)
#letzte funktionierende Einstellung war mit 'gemini-2.5-flash'
GEMINI_MODEL = genai.GenerativeModel('gemini-2.5-flash') # Oder 'gemini-1.5-pro' für komplexere Analysen

OUTPUT_REPORT_FILE = f"wcag_analysis_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
BASE_URL = "https://www.otto.de"
SEARCH_URL_TSHIRT = f"{BASE_URL}/suche/t-shirt"

SELECTORS = {
    "search_result_item_selector": 'article[data-id="S0O1G0UY"]',
    #size-input-4
    #div:has(input[type="radio"][name="size-input"][value="XXL"])
    #div.pl_selectiontile-text100.js_pdp_dimension-selection__scrollable-tile:has(input[value="XXL"])
    "size_selector": 'div.pl_selectiontile-text100.js_pdp_dimension-selection__scrollable-tile:has(input[value="XXL"])',
    #"size_value": "XXL",
    #button[data-oc-floating-focus-v1-target="true"]:has-text("In den Warenkorb")
    # funktionierender inhalt für cart_button_selector: oc-button-v1[data-qa="goToBasket"]:has-text("Zum Warenkorb")
    "color_selector": 'img.pdp_dimension-selection__color-tile-image[alt="grau"]',
    "add_to_cart_button_selector": 'button.button--variant-primary[type="submit"]',
    "dialog_to_cart_button_selector": 'oc-button-v1[data-qa="goToBasket"]:has-text("Zum Warenkorb")',
    "cart_page_url_substring": "/warenkorb", 
    "cookie_accept_button_selector": '#onetrust-accept-btn-handler' 
}

WCAG_CRITERIA_TO_CHECK = """
WCAG 2.2 Level A und AA Kriterien, insbesondere fokussiert auf semantische und kontextbezogene Aspekte:
- 1.1.1 Nicht-Text-Inhalt (Non-text Content): Alt-Texte auf Aussagekraft und Kontextpassung.
- 1.3.1 Info und Beziehungen (Info and Relationships): Korrekte Überschriftenhierarchie, Listen- und Tabellenstrukturen, Formularbeschriftungen (Labeling).
- 1.3.2 Bedeutungstragende Reihenfolge (Meaningful Sequence): Logische Lesereihenfolge bei visueller Abweichung.
- 2.4.1 Blöcke umgehen (Bypass Blocks): Existenz von Skip-Links für wiederholte Inhalte.
- 2.4.4 Linkzweck (Im Kontext): Aussagekraft von Linktexten im Kontext (z.B. "Hier klicken" vermeiden).
- 2.4.6 Überschriften und Beschriftungen: Sind Überschriften und Beschriftungen deskriptiv?
- 3.2.3 Konsistente Navigation: Navigationselemente sind über die Seite hinweg konsistent.
- 3.2.4 Konsistente Identifikation: Komponenten mit gleicher Funktionalität sind konsistent identifiziert.
- 3.3.2 Beschriftungen oder Anweisungen: Formularfelder haben klare Anweisungen.
- 3.3.3 Fehlervorschläge: Sind Fehlermeldungen klar und hilfreich?
- 3.3.4 Fehlervermeidung: Mechanismen zur Vermeidung schwerwiegender Fehler bei Transaktionen.
"""

interaction_history = []

# --- Funktion zur WCAG-Analyse mit Gemini ---
async def analyze_with_gemini(page_html: str, current_url: str, step_description: str, full_interaction_history: list) -> dict:
    # ... (Dieser Teil des Codes ist bereits asynchron und benötigt keine Änderungen hier) ...
    
    # Baue den Kontext-String aus der Historie
    history_context_str = ""
    if full_interaction_history:
        history_context_str = "\n\nVorheriger Interaktionspfad und Kontext:"
        for i, entry in enumerate(full_interaction_history):
            history_context_str += f"\n  Schritt {i+1}: URL '{entry['url']}', Aktion '{entry['action']}'"
            if entry.get('additional_context'):
                history_context_str += f", Details: {entry['additional_context']}"

    #Berücksichtige dabei den gesamten, bisherigen Interaktionspfad, um den Kontext besser zu verstehen und semantische sowie kontextbezogene WCAG-Verletzungen zu identifizieren.
    #{history_context_str}
    prompt_text = f"""
    Analysiere den folgenden HTML-Code einer Webseite auf Verletzungen der WCAG Kriterien, insbesondere in Bezug auf semantisches Verständnis und Kontext.
    Konzentriere dich auf alle folgenden WCAG Erfolgskriterien:
    - 1.1.1 Nicht-Text-Inhalt (A)
    - 1.3.1 Info und Beziehungen (A)
    - 1.3.2 Bedeutungstragende Reihenfolge (A)
    - 1.3.3 Sensorische Eigenschaften (A)
    - 2.4.1 Blöcke umgehen (A)
    - 2.4.4 Linkzweck (Im Kontext) (A)
    - 2.4.5 Verschiedene Methoden (AA)
    - 2.4.6 Überschriften und Beschriftungen (Labels) (AA)
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
    Nenne die CSS-Selektoren, welche die HTML-Elemente auf der Webseite identifizieren, die die gemeldeten Barrierefreiheitsverletzung verursacht haben.
    Nenne die CSS-Selektoren in dem gleichen Format wie axe-core.
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
        "Html Ausschnitt auf der Webseite": "<img src=\"logo.png\">",
        "CSS-Selektor": " ["div[data-parent-id=\"facet_categorypath\"] > h4:nth-child(1)"
        "Änderungsvorschlag": "<img src=\"logo.png\" alt=\"Firmenlogo von der Firma Otto\">",
        "Änderungen einzeln": "alt=\"Firmenlogo von Beispiel GmbH\",
        "Funktion/Rolle des Elements im Kontext der Webseite ": "Logo im Header-Bereich der Webseite."
    }}
    ---

    Aktuelle Seite: {current_url}
    Aktueller Zustand im Interaktionspfad: {step_description}
    

    ---

    HTML-Code der aktuellen Webseite:
    ```html
    {page_html}
    ```
 
    """
    
    try:
        print(GOOGLE_API_KEY)
        print(f"Sende Anfrage an Gemini für {step_description}...")
        response = await GEMINI_MODEL.generate_content_async(
            contents=[prompt_text],
            generation_config={"response_mime_type": "application/json", "temperature": 0.1}
        )

        json_response_text = response.text 


        try:
            # Versuche, den erhaltenen String in JSON zu parsen
            parsed_response = json.loads(json_response_text)
        except json.JSONDecodeError:
            # ... (Logik zur Bereinigung und erneutem Parsen, falls Gemini kein sauberes JSON liefert) ...
            print(f"WARNUNG: Gemini hat kein gültiges JSON geliefert. Rohantwort: {json_response_text[:200]}...")
            clean_response_text = json_response_text.strip()
            if clean_response_text.startswith("```json") and clean_response_text.endswith("```"):
                clean_response_text = clean_response_text[len("```json"): -len("```")].strip()
            # Fangen Sie auch einen möglichen Fehler hier ab, falls clean_response_text immer noch kein gültiges JSON ist
            try:
                parsed_response = json.loads(clean_response_text)
            except json.JSONDecodeError as e_clean:
                print(f"FEHLER: Bereinigte Antwort ist immer noch kein gültiges JSON: {e_clean}")
                print(f"Fehlerhafte bereinigte Antwort: {clean_response_text[:500]}...")
                return [] # Gib leere Liste im Fehlerfall zurück


        return parsed_response

    except Exception as e:
        print(f"FEHLER bei Gemini-Analyse für '{step_description}': {e}")
        # Versuche, den rohen Antwortinhalt für die Fehlermeldung zu bekommen, wenn 'response' definiert ist
        raw_response_content = ""
        if 'response' in locals() and hasattr(response, 'text'):
            raw_response_content = response.text
        print(f"Gemini Rohantwort (Teil): {raw_response_content[:500]}...")
        return []


# --- Helper-Funktion für die Analyse auf der Seite (muss ebenfalls ASYNCHRON sein) ---
async def perform_accessibility_analysis_on_page(page, axe_options=None):
    print("Führe Zugänglichkeitstests auf dem aktuellen Seitenzustand durch...")
    if axe_options is None:
        axe_options = {'runOnly': {'type': 'tag', 'values': ['wcag2aa']}}
    
    # Assuming axe_playwright.run is designed for async page objects
    # If not, you might need to adjust axe_playwright itself or use a different wrapper.
    # If axe_playwright is not async, this will cause issues.
    # For now, let's assume axe_playwright.run can handle async 'page' object or is also async.
    # If not, you might need to perform page.content() and pass to analyze_with_gemini directly.
    # Given your current error, axe_playwright.run might not be purely async
    # Let's just return HTML content for direct passing to Gemini
    return await page.content() # Just return HTML for now to avoid axe_playwright issues

# --- Haupt-Simulations-Workflow ---
async def run_shopping_workflow_and_analyze(search_url: str, selectors: dict):
    all_analysis_results = []
    
    # <--- WICHTIG: async with statt nur with ---
    async with async_playwright() as p:
        # <--- WICHTIG: await vor p.chromium.launch ---
        browser = await p.chromium.launch(headless=False, slow_mo=100)
        # <--- WICHTIG: await vor browser.new_page ---
        page = await browser.new_page()
        
        try:
            # --- Webseite 1: Suchergebnisseite ---
            print("\n--- Schritt 1: Navigiere zur Suchergebnisseite ---")
            # <--- WICHTIG: await vor page.goto ---
            await page.goto(search_url, wait_until="networkidle")

            # --- CODE ZUM ENTFERNEN DES COOKIE-BANNERS HIER EINFÜGEN ---
            if selectors.get("cookie_accept_button_selector"):
                cookie_button_selector = selectors["cookie_accept_button_selector"]
                print("Versuche, Cookie-Banner zu akzeptieren...")
                try:
                    # Warte bis der Button sichtbar ist (timeout für den Fall, dass er nicht erscheint)
                    await page.wait_for_selector(cookie_button_selector, state='visible', timeout=10000)
                    # Klicke den Button, um Cookies zu akzeptieren
                    await page.locator(cookie_button_selector).click()
                    print("Cookie-Banner akzeptiert/geschlossen.")
                    # Warte auf die Schließung des Banners und die Netzwerkruhe der Seite
                    # Manchmal verschwindet der Banner nicht sofort visuell
                    await page.wait_for_load_state('networkidle', timeout=10000)
                    # Optional: Zusätzliche kurze Pause für UI-Stabilisierung
                    await page.wait_for_timeout(500) 
                except Exception as cookie_error:
                    print(f"Cookie-Banner nicht gefunden oder Klick fehlgeschlagen (eventuell schon geschlossen oder nicht vorhanden): {cookie_error}")
            # --- ENDE DES COOKIE-BANNER CODES ---


            current_url = page.url
            # <--- WICHTIG: await vor page.content ---
            current_html = await page.content()
            
            print(f"Analysiere Suchergebnisseite: {current_url}")
            step_results = await analyze_with_gemini(current_html, current_url, "Suchergebnisseite", interaction_history)
            all_analysis_results.append({
                "step": 1,
                "description": "Suchergebnisseite",
                "url": current_url,
                "violations": step_results
            })
            interaction_history.append({"url": current_url, "action": "Navigiert zu Suchergebnis"})
       


            # Klicke auf den ersten Artikel in den Suchergebnissen
            if selectors.get("search_result_item_selector"):
                print(f"Klicke auf den ersten Artikel (Selektor: {selectors['search_result_item_selector']})...")
                # <--- WICHTIG: await vor page.wait_for_selector ---
                await page.wait_for_selector(selectors["search_result_item_selector"], timeout=5000)
                # <--- WICHTIG: await vor page.locator().first.click ---
                await page.locator(selectors["search_result_item_selector"]).first.click()
                print("Warte auf Navigation zur Produktdetailseite...")
                # <--- WICHTIG: await vor page.wait_for_load_state ---
                await page.wait_for_load_state("networkidle")
                
                # --- Webseite 2: Produktdetailseite (nach Klick auf Artikel) ---
                current_url = page.url
                # <--- WICHTIG: await vor page.content ---
                current_html = await page.content()

                print(f"\n--- Schritt 2: Produktdetailseite (nach Klick auf Artikel) ---")
               

                # Farbe und Größe auswählen, Artikel in den Warenkorb legen
                print("Führe Interaktionen auf Produktdetailseite aus...")
                
        
                if selectors.get("color_selector"):
                    print(f"  Wähle Farbe (Selektor: {selectors['color_selector']})...")
                    # <--- WICHTIG: await vor page.locator().click ---
                    await page.locator(selectors["color_selector"]).click()
                    # <--- WICHTIG: await vor page.wait_for_timeout ---
                    await page.wait_for_timeout(500)
                    interaction_history.append({"url": current_url, "action": "Farbe gewählt"})

                # if selectors.get("size_selector"): # Nur noch Prüfung auf Existenz des Selektors
                #     print(f"  Wähle Größe (Selektor: {selectors['size_selector']})...")
                #     # Direkter Klick auf das Element, das vom Selektor identifiziert wird
                #     await page.locator(selectors["size_selector"]).click() 
                #     await page.wait_for_timeout(500)
                #     interaction_history.append({"url": current_url, "action": f"Größe gewählt: Selektor {selectors['size_selector']}"})


                print(f"Analysiere Produktdetailseite: {current_url}")
                step_results = await analyze_with_gemini(current_html, current_url, "Produktdetailseite", interaction_history)
                all_analysis_results.append({
                    "step": 2,
                    "description": "Produktdetailseite",
                    "url": current_url,
                    "violations": step_results
                })
                interaction_history.append({"url": current_url, "action": "Artikel aus Suchergebnis gewählt"})

                if selectors.get("add_to_cart_button_selector"):
                    print("  Klicke 'In den Warenkorb'...")
                    add_to_cart_button = page.locator(selectors["add_to_cart_button_selector"])
                    # <--- WICHTIG: await vor add_to_cart_button.wait_for ---
                    await add_to_cart_button.wait_for(state="visible", timeout=10000)
                    #await add_to_cart_button.wait_for(state="enabled", timeout=5000)
                    # <--- WICHTIG: await vor add_to_cart_button.click ---
                    await add_to_cart_button.click()
                    
                    print("  Warte auf Warenkorb-Bestätigungsdialog...")
                    if selectors.get("dialog_to_cart_button_selector"):
                        # <--- WICHTIG: await vor page.wait_for_selector ---
                        await page.wait_for_selector(selectors["dialog_to_cart_button_selector"], state="visible", timeout=10000)
                        print("   -> Warenkorb-Bestätigungsdialog erkannt.")
                        
                        # --- Webseite 3: Warenkorb-Seite (nach Klick im Dialog) ---
                        print("  Klicke 'Zum Warenkorb' im Dialog...")
                        # <--- WICHTIG: await vor page.locator().click ---
                        await page.locator(selectors["dialog_to_cart_button_selector"]).click()
                        print("Warte auf Navigation zur Warenkorbseite...")
                        # <--- WICHTIG: await vor page.wait_for_load_state ---
                        await page.wait_for_load_state("networkidle")
                        
                        current_url = page.url
                        # <--- WICHTIG: await vor page.content ---
                        current_html = await page.content()

                        print(f"\n--- Schritt 3: Warenkorb-Seite ---")
                        print(f"Analysiere Warenkorbseite: {current_url}")
                        step_results = await analyze_with_gemini(current_html, current_url, "Warenkorbseite (nach Artikel-Hinzufügung)", interaction_history)
                        all_analysis_results.append({
                            "step": 3,
                            "description": "Warenkorbseite",
                            "url": current_url,
                            "violations": step_results
                        })
                        interaction_history.append({"url": current_url, "action": "Artikel in Warenkorb gelegt und zum Warenkorb navigiert"})

                    else:
                        print("   -> Selektor für 'Zum Warenkorb'-Dialogbutton fehlt. Kann nicht zum Warenkorb navigieren.")
                else:
                    print("  Selektor für 'In den Warenkorb'-Button fehlt. Überspringe Warenkorb-Interaktion.")
            else:
                print("Selektor für Suchergebnis-Artikel fehlt. Überspringe Produktdetailseite und Warenkorb.")

        except Exception as e:
            print(f"Ein schwerwiegender Fehler ist aufgetreten: {e}")
            # <--- WICHTIG: await vor page.screenshot ---
            await page.screenshot(path=f"error_workflow_{datetime.now().strftime('%H%M%S')}.png")
        finally:
            if browser:
                # <--- WICHTIG: await vor browser.close ---
                await browser.close()

    return all_analysis_results

# --- Hauptausführung ---
if __name__ == "__main__":
    import asyncio
    
    # ... (Ihre Selektoren etc.) ...
    
    # Die Ausführung erfolgt hier über asyncio.run(), was die async-Funktion startet.
    final_report = asyncio.run(run_shopping_workflow_and_analyze(SEARCH_URL_TSHIRT, SELECTORS))

    if final_report:
        with open(OUTPUT_REPORT_FILE, "w", encoding="utf-8") as f:
            json.dump(final_report, f, indent=4, ensure_ascii=False)
        print(f"\n--- Gesamter WCAG-Analysebericht für den Workflow in '{OUTPUT_REPORT_FILE}' gespeichert. ---")
    else:
        print("\n--- Workflow-Analyse konnte nicht erfolgreich abgeschlossen werden. ---")