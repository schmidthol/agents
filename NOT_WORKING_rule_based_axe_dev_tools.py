# Vorbereitung:
# virtuelles environment erstellen und darin die folgenden Befehle ausführen
# pip install playwright 
# python3 -m pip install -U axe-playwright-python
# python3 -m playwright install --with-deps
# Siehe https://github.com/pamelafox/axe-playwright-python

import json
from playwright.sync_api import sync_playwright, Playwright
from axe_devtools_api import Axe



def analyze_accessibility_with_axe(url: str, axe_options: dict = None, output_file: str = None) -> dict:
    """
    Führt eine Barrierefreiheitsanalyse einer Webseite mit axe-core über Playwright aus
    und gibt die Ergebnisse zurück.

    Args:
        url (str): Die URL der zu untersuchenden Webseite.
        axe_options (dict, optional): Optionen, die an axe-core übergeben werden.
                                      Z.B. {'runOnly': {'type': 'tag', 'values': ['wcag2a']}}.
                                      Defaults to None (führt alle Standardregeln aus).
        output_file (str, optional): Dateiname, unter dem der vollständige Bericht
                                     im JSON-Format gespeichert werden soll. Defaults to None.

    Returns:
        dict: Ein Dictionary, das die Rohdaten der axe-core-Analyse enthält.
    """
    print(f"Starte Barrierefreiheitsanalyse für: {url}")
    results = {}
    
    with sync_playwright() as p: #Kontextmanager ruft synchrone Playwright Sitzung auf
        browser = p.chromium.launch(headless=True) # Setze headless=False für sichtbares Browserfenster
        page = browser.new_page()
        
        try:
            print(f"Navigiere zu {url}...")
            page.goto(url, wait_until="networkidle")
            
            print("Führe axe-core Analyse mit spezifischen Optionen aus...")
            # Führe axe-core aus mit den übergebenen Optionen
            axe_results = axe_playwright.run(page, options=axe_options) 
            
            results = {
                "url": url,
                "violations": axe_results.response('violations', []),
                "passes": axe_results.response('passes', []),
                "incomplete": axe_results.response('incomplete', []),
                "inapplicable": axe_results.response('inapplicable', [])
            }
            
            print(f"Analyse abgeschlossen für {url}.")
            
            # --- Ergebnisse im Terminal anzeigen ---
            if results["violations"]:
                print(f"\n--- Gefundene WCAG-Verletzungen ({len(results['violations'])}) ---")
                for i, violation in enumerate(results["violations"]):
                    print(f"\nVerletzung {i+1}:")
                    print(f"  ID: {violation.get('id')}")
                    print(f"  Beschreibung: {violation.get('description')}")
                    print(f"  Hilfe: {violation.get('help')}")
                    print(f"  Hilfe-URL: {violation.get('helpUrl')}")
                    print(f"  Auswirkung: {violation.get('impact')}")
                    
                    nodes_affected = violation.get('nodes', [])
                    print(f"  Betroffene Elemente ({len(nodes_affected)}):")
                    for j, node in enumerate(nodes_affected[:min(len(nodes_affected), 3)]):
                        print(f"    - HTML: {node.get('html', '')[:100]}...")
                        print(f"      Selektor: {node.get('target', 'N/A')}")
            else:
                print("\nKeine WCAG-Verletzungen durch axe-core gefunden mit den gewählten Optionen.")
            
            # --- Optional: Gesamten Bericht in JSON-Datei speichern ---
            if output_file:
                with open(output_file, "w", encoding="utf-8") as f:
                    json.dump(results, f, indent=4, ensure_ascii=False)
                print(f"\nVollständiger Bericht in '{output_file}' gespeichert.")
            
        except Exception as e:
            print(f"Ein Fehler ist während der Analyse aufgetreten: {e}")
        finally:
            browser.close()
            
    return results

# --- Beispiel-Nutzung ---
if __name__ == "__main__":
    test_url = "https://www.w3.org/WAI/demos/bad/before/home.html" # Eine Seite mit vielen Problemen



    # --- Option 2: Nur WCAG 2 Level AA ---
    print("\n--- TEST: Nur WCAG 2 Level AA Regeln ---")
    options_wcag2aa = {
        'runOnly': {
            'type': 'tag',
            'values': ['wcag2aa']
        }
    }
    analyze_accessibility_with_axe(test_url, axe_options=options_wcag2aa, output_file="report_wcag2aa.json")

"""
    # --- Option 1: Nur WCAG 2 Level A (abdeckt 1.3.1) ---
    print("\n--- TEST: Nur WCAG 2 Level A Regeln (einschließlich 1.3.1 Aspekte) ---")
    options_wcag2a = {
        'runOnly': {
            'type': 'tag',
            'values': ['cat.semantics']
        }
    }
    analyze_accessibility_with_axe(test_url, axe_options=options_wcag2a, output_file="report_wcag2a.json")


    # --- Option 3: Spezifische Regeln (z.B. Farbkontrast und Formular-Label) ---
    print("\n--- TEST: Nur spezifische Regeln (Farbkontrast, Formular-Label) ---")
    options_specific_rules = {
        'runOnly': {
            'type': 'rule',
            'values': ['color-contrast', 'label'] # 'label' ist eine Regel, die 1.3.1 tangiert
        }
    }
    analyze_accessibility_with_axe(test_url, axe_options=options_specific_rules, output_file="report_specific_rules.json")
"""

    # --- Option 4: Ohne spezifische Optionen (standardmäßig alle Regeln) ---
    # print("\n--- TEST: Alle Standardregeln ---")
    # analyze_accessibility_with_axe(test_url, output_file="report_all_rules.json")