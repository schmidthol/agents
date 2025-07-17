from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from agent_program import wcag_analyst_agent
import os
import json

output_filename = "wcag_analysis_results.json"
output_directory = "output_directory"
output_filepath = os.path.join(output_directory, output_filename)




def simulate_shopping_and_analyze(product_url: str, interaction_selectors: dict):
    """
    Simuliert den Einkaufsprozess auf einer Webseite und führt danach eine Barrierefreiheitsanalyse durch.

    Args:
        product_url (str): Die URL der Produktseite.
        interaction_selectors (dict): Ein Dictionary mit CSS-Selektoren für die Interaktionen.
                                      Keys: 'size_selector', 'size_value', 'color_selector', 'add_to_cart_button_selector', 'cart_confirmation_selector'.
    Returns:
        dict: Ergebnisse der Barrierefreiheitsanalyse nach der Warenkorb-Interaktion.
    """
    analysis_results = {}
    with sync_playwright() as p:
        # Browser starten (headless=False für visuelles Debugging)
        browser = p.chromium.launch(headless=False, slow_mo=50) # slow_mo verlangsamt Ausführung für bessere Sichtbarkeit
        page = browser.new_page()
        
        try:
            print(f"1. Navigiere zu Produktseite: {product_url}")
            page.goto(product_url, wait_until="networkidle") # Warten, bis Seite geladen und Netzwerk ruhig ist
            
            # --- Artikeloptionen auswählen (falls Selektoren gegeben) ---
            if interaction_selectors.get("size_selector") and interaction_selectors.get("size_value"):
                print(f"2. Wähle Größe '{interaction_selectors['size_value']}'...")
                # Prüfen, ob der Selektor ein <select>-Element ist
                if page.locator(interaction_selectors["size_selector"]).element_handle().tag_name() == 'select':
                    page.select_option(interaction_selectors["size_selector"], value=interaction_selectors["size_value"])
                else: # Ansonsten annehmen, es ist ein Klick-Element (z.B. Button)
                    page.locator(interaction_selectors["size_selector"], has_text=interaction_selectors["size_value"]).click()
                page.wait_for_timeout(2000) # Kurze Wartezeit, um UI-Updates zu ermöglichen

            if interaction_selectors.get("color_selector") and interaction_selectors.get("color_value"):
                print(f"3. Wähle Farbe '{interaction_selectors['color_value']}'...")
                # Beispiel: Klick auf einen Button/Radio-Element, das die Farbe repräsentiert
                page.locator(interaction_selectors["color_selector"], has_text=interaction_selectors["color_value"]).click()
                page.wait_for_timeout(500) # Kurze Wartezeit

            # --- Artikel in den Warenkorb legen ---
            if interaction_selectors.get("add_to_cart_button_selector"):
                print("4. Klicke 'In den Warenkorb'...")
                add_to_cart_button = page.locator(interaction_selectors["add_to_cart_button_selector"])
                
                # Sicherstellen, dass der Button sichtbar und anklickbar ist
                add_to_cart_button.wait_for(state="visible", timeout=10000)
                add_to_cart_button.wait_for(state="enabled", timeout=10000)
                add_to_cart_button.click()
                
                # --- Auf die Aktualisierung der Seite warten ---
                print("5. Warte auf Warenkorb-Update/Bestätigung...")
                if interaction_selectors.get("cart_confirmation_selector"):
                    # Warte auf ein Element, das die Bestätigung anzeigt (z.B. Popup, Warenkorb-Zähler)
                    page.wait_for_selector(interaction_selectors["cart_confirmation_selector"], state="visible", timeout=15000)
                    print("   -> Warenkorb-Bestätigungselement erkannt.")
                elif interaction_selectors.get("cart_page_url_substring"):
                    # Warte auf eine Weiterleitung zur Warenkorb-Seite
                    page.wait_for_url(interaction_selectors["cart_page_url_substring"], timeout=15000)
                    print(f"   -> Weitergeleitet zur Warenkorb-Seite: {page.url}")
                else:
                    # Allgemeine Wartezeit, wenn keine spezifischen Indikatoren bekannt sind
                    page.wait_for_load_state("networkidle", timeout=15000)
                    print("   -> Allgemeine Netzwerkruhe nach 'In den Warenkorb'-Klick.")
                
                # --- HTML/Accessibility Tree des aktualisierten Zustands extrahieren ---
                print("6. Extrahiere HTML und führe Barrierefreiheitsanalyse durch (nach Interaktion)...")
                analysis_results = wcag_analyst_agent(page)
                
            else:
                print("Selektor für 'In den Warenkorb'-Button nicht angegeben. Überspringe Warenkorb-Interaktion.")

        except Exception as e:
            print(f"Ein Fehler ist während der Einkaufssimulation aufgetreten: {e}")
            page.screenshot(path="error_shopping_screenshot.png") # Screenshot bei Fehler
        finally:
            if browser:
                browser.close()
    
    return analysis_results

# --- Beispiel-Nutzung mit Otto.de ---
# HINWEIS: Selektoren für Otto.de sind dynamisch und können sich ändern!
# Sie MÜSSEN die genauen CSS-Selektoren mit den Entwickler-Tools (F12) im Browser finden.

# Beispiel-URL für einen Campingstuhl (Stand heute)
otto_product_url = "https://www.otto.de/p/levis-t-shirt-herren-t-shirt-1er-pack-baumwolle-packung-1er-pack-C1701062902/#variationId=707495593"

# Beispiel-Selektoren (diese MÜSSEN Sie auf der aktuellen otto.de-Seite prüfen und anpassen!)
otto_selectors = {
    # Beispiel für Größen-/Farbwahl (oft Buttons oder Selects). Prüfen Sie HTML der Seite!
    # 'size_selector': 'div[data-qa="size-selector"] button[value="M"]', # Beispiel für einen Button
    # 'size_value': 'M',
    'color_selector': 'input[type="radio"][name="color-input"][value="anthrazit"]', 
    'color_value': 'anthrazit',
    'add_to_cart_button_selector': 'button[data-qa="addToBasket"]', # Schlagwortsuche im HTML Code nach "In den Warenkorb"
    'cart_confirmation_selector': 'div[data-qa="goToBasket"], span[data-qa="header-cart-item-count"]', # Selektor für Warenkorb-Zähler oder Bestätigungs-Popup
    'cart_page_url_substring': '/warenkorb' # Wenn die Seite direkt zum Warenkorb weiterleitet
}











if __name__ == "__main__":
    print("--- Starte Shopping-Simulation und Analyse ---")
    results_after_shopping = simulate_shopping_and_analyze(otto_product_url, otto_selectors)
    
    print("\n--- Analyseergebnisse nach Warenkorb-Interaktion ---")
    # Hier können Sie die Ergebnisse weiterverarbeiten, z.B. speichern oder an Ihren AI-Agenten übergeben.
    # print(json.dumps(results_after_shopping, indent=2))

    try:
      # 1. Den JSON-String in ein Python-Objekt (Liste/Dictionary) parsen
      # json.loads() erwartet einen String als Eingabe
      parsed_json_data = results_after_shopping #json.loads()

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
    
    if results_after_shopping:
        print(f"Anzahl der gefundenen Verletzungen auf der aktualisierten Seite: {len(results_after_shopping)}")
    else:
        print("Keine Analyseergebnisse verfügbar oder ein Fehler ist aufgetreten.")

# WICHTIG: Du musst Playwright installieren und die Browser-Treiber herunterladen:
# pip install playwright
# playwright install


#print(read_dynamic_html_from_url("https://www.zalando.de/pier-one-2-pack-hemd-blackwhite-pi922d0cs-q11.html"))
#print(read_dynamic_html_from_url("https://www.otto.de/p/tom-tailor-denim-straight-jeans-barrel-mom-vintage-1-tlg-weiteres-detail-C1473510499/#variationId=1473510500"))