import json
import re
from bs4 import BeautifulSoup
import difflib # Für String-Ähnlichkeitsvergleiche

# --- Konfiguration ---
AXE_REPORT_PATH = "axe.json"      # Beispiel: Bericht vom JS-axe-scanner
AI_AGENT_REPORT_PATH = "agent.json" # Beispiel: Bericht vom Python-AI-Agenten


# --- Mapping von Axe-Core Rule IDs zu WCAG Erfolgskriterien ---
AXE_RULE_TO_WCAG_MAP = {
    "aria-alt": ["2.4.4 Linkzweck (Im Kontext)", "4.1.2 Name, Rolle, Wert"],
    "button-name": ["4.1.2 Name, Rolle, Wert"],
    "document-title": ["2.4.2 Seite mit Titel"],
    "image-alt": ["1.1.1 Nicht-Text-Inhalt"],
    "input-button-name": ["4.1.2 Name, Rolle, Wert"],
    "input-image-alt": ["1.1.1 Nicht-Text-Inhalt", "4.1.2 Name, Rolle, Wert"],
    "label": ["1.3.1 Info und Beziehungen", "3.3.2 Beschriftungen oder Anweisungen", "4.1.2 Name, Rolle, Wert"],
    "link-name": ["2.4.4 Linkzweck (Im Kontext)", "4.1.2 Name, Rolle, Wert"],
    "object-alt": ["1.1.1 Nicht-Text-Inhalt"],
    "role-img": ["1.1.1 Nicht-Text-Inhalt"],
    "select-name": ["4.1.2 Name, Rolle, Wert"],
    "svg-img-alt": ["1.1.1 Nicht-Text-Inhalt"],
    "autocomplete-valid": ["1.3.5 Bestimmung des Eingabezwecks"],
    "empty-heading": ["1.3.1 Info und Beziehungen"],
    "heading-order": ["1.3.1 Info und Beziehungen", "2.4.6 Überschriften und Beschriftungen"],
    "empty-table-header": ["1.1.1 Nicht-Text-Inhalt"],
    "image-redundant-alt": ["1.1.1 Nicht-Text-Inhalt"]
}

# --- Hilfsfunktion zur Normalisierung von WCAG-Kriteriumsstrings ---
def normalize_wcag_criterion(criterion_str: str) -> str:
    return re.sub(r'\s*\([A|AA]+\)$', '', criterion_str).strip()

# --- VERBESSERT: Hilfsfunktion zur Normalisierung von CSS-Selektoren ---
def normalize_selector(selector: str) -> str:
    """Bereinigt einen CSS-Selektor und normalisiert ihn."""
    if isinstance(selector, list) and selector:
        selector = selector[0] # Nimm den ersten Selektor, wenn es eine Liste ist
    elif not isinstance(selector, str):
        return ""
    selector = selector.replace('\\:', ':') # Entferne Escape für Colons (z.B. bei xlink:href)
    return re.sub(r'\s+', ' ', selector).strip().lower()

# --- NEU: Hilfsfunktion, um verschiedene Formen eines Selektors für den Vergleich zu erzeugen ---
def _get_selector_comparison_forms(selector: str) -> list[str]:
    """
    Erzeugt eine Liste von Selector-Formen für einen flexibleren Vergleich.
    Beispiel: ".container > button" -> [".container > button", "button"]
    """
    forms = [selector] # Immer den vollen Selektor
    
    # Füge den letzten Teil des Selektors nach dem letzten '>' hinzu
    if '>' in selector:
        last_part = selector.split('>')[-1].strip()
        forms.append(last_part)
    
    # Füge den Teil des Selektors nach dem letzten Leerzeichen (Descendant-Kombinator) hinzu
    if ' ' in selector:
        last_word_selector = selector.split(' ')[-1].strip()
        forms.append(last_word_selector)

    # Entferne Duplikate und gib zurück
    return list(set(forms))

# --- VERBESSERT: Hilfsfunktion zur Normalisierung von HTML-Ausschnitten ---
def normalize_html_snippet_for_comparison(html_str: str) -> str:
    """
    Normalisiert einen HTML-Ausschnitt für den Vergleich.
    Entfernt irrelevante/dynamische Attribute, sortiert die verbleibenden und normalisiert Whitespace.
    Ziel ist es, eine kanonische Form zu erhalten, die Vergleiche ermöglicht.
    """
    if not isinstance(html_str, str):
        return ""

    try:
        soup = BeautifulSoup(html_str, 'html.parser')
        
        first_tag = soup.find()

        if not first_tag:
            return re.sub(r'\s+', ' ', html_str).strip().lower()

        attributes_to_remove_from_comparison = [
            'id', 'style', 'tabindex', 'data-initialized', 'data-loadurl', 'data-preload',
            'data-href', 'data-funder-legal-name', 'data-advertiser-legal-name', 'data-origin',
            'data-amount-colors', 'data-sheet-id', 'data-sheet-url', 'data-sheet-title',
            'data-sheet-tracking-object', 'data-sheet-menu-content', 'data-select-mode',
            'data-login-state', 'data-loggedin', 'data-nav-initialized', 'data-nav-track',
            'data-nav-testing', 'data-nav-tracking-click-breadcrumb-headline', 'data-ts-labels',
            'data-ts-move', 'data-tracking-feature-id', 'data-producttile-tracking',
            'data-qa-id', 'checked', 'selected', 'disabled', 'value', 'type', 'name', 'size',
            'class' # Entfernen wir hier komplett, um nur auf Attribute und Inhalt zu fokussieren,
                    # da Klassen dynamisch und sehr variabel sein können.
        ]
        # Svelte-Hashes wurden hier irrelevant, da 'class' entfernt wird
        
        canonical_attrs = {}
        for attr_name, attr_value in first_tag.attrs.items():
            attr_name_lower = attr_name.lower()

            if attr_name_lower in attributes_to_remove_from_comparison:
                continue
            
            if isinstance(attr_value, list):
                canonical_attrs[attr_name_lower] = ' '.join(sorted([str(v).strip() for v in attr_value]))
            else:
                canonical_attrs[attr_name_lower] = str(attr_value).strip()

        sorted_attr_strings = []
        for k, v in sorted(canonical_attrs.items()):
            if v:
                v_escaped = v.replace('"', '\\"')
                sorted_attr_strings.append(f'{k}="{v_escaped}"')
        
        tag_name = first_tag.name.lower()
        inner_text_content = ""
        if tag_name == 'svg' or first_tag.find('slot'):
            inner_text_content = "<slot_or_svg_content>"
        else:
            inner_text_content = re.sub(r'\s+', ' ', first_tag.get_text(strip=True)).strip()
        
        normalized_tag_str = f"<{tag_name}"
        if sorted_attr_strings:
            normalized_tag_str += " " + " ".join(sorted_attr_strings)
        normalized_tag_str += ">"

        if inner_text_content:
            normalized_tag_str += inner_text_content
        
        normalized_tag_str += f"</{tag_name}>"

        return normalized_tag_str.lower()

    except Exception as e:
        print(f"Warnung: Fehler beim Normalisieren des HTML-Ausschnitts '{html_str[:50]}...': {e}")
        return re.sub(r'\s+', ' ', html_str).strip().lower()


# --- NEU: Funktion zum umfassenden Vergleich zweier Verletzungen ---
def _are_violations_similar(axe_viol_detail: dict, ai_viol_detail: dict, selector_similarity_threshold: float = 0.8, html_similarity_threshold: float = 0.9):
    """
    Bestimmt, ob zwei Verletzungen (eine von Axe, eine vom AI-Agenten) als identisch betrachtet werden können.
    Nutzt mehrere Kriterien und Fuzzy-Matching.
    """
    # 1. URLs müssen übereinstimmen
    if axe_viol_detail.get('url') != ai_viol_detail.get('url'):
        return False
    
    # 2. WCAG-Kriterium muss übereinstimmen (nach Normalisierung)
    axe_wcag = normalize_wcag_criterion(axe_viol_detail.get('wcag_kriterium', ''))
    ai_wcag = normalize_wcag_criterion(ai_viol_detail.get('wcag_kriterium', ''))
    if axe_wcag != ai_wcag:
        return False

    # 3. HTML-Ausschnitt-Vergleich (primär)
    axe_html_norm = normalize_html_snippet_for_comparison(axe_viol_detail.get('html', ''))
    ai_html_norm = normalize_html_snippet_for_comparison(ai_viol_detail.get('html_ausschnitt', ''))
    
    html_similarity = difflib.SequenceMatcher(None, axe_html_norm, ai_html_norm).ratio()
    if html_similarity >= html_similarity_threshold:
        return True # Direkte Übereinstimmung durch HTML-Snippet

    # 4. CSS-Selektor-Vergleich (sekundär, wenn HTML-Match nicht stark genug)
    axe_selector_norm = normalize_selector(axe_viol_detail.get('target', [''])[0])
    ai_selector_norm = normalize_selector(ai_viol_detail.get('selektor', ''))

    # Erzeuge alle Vergleichsformen für beide Selektoren
    axe_selector_forms = _get_selector_comparison_forms(axe_selector_norm)
    ai_selector_forms = _get_selector_comparison_forms(ai_selector_norm)

    # Prüfe auf Substring-Übereinstimmung zwischen allen Formen
    for axe_form in axe_selector_forms:
        for ai_form in ai_selector_forms:
            if axe_form in ai_form or ai_form in axe_form:
                # Optional: Schauen, ob die Selektoren eine minimale Ähnlichkeit haben
                if difflib.SequenceMatcher(None, axe_form, ai_form).ratio() >= selector_similarity_threshold:
                    return True # Gefunden durch Selektor-Substring-Match

    return False # Keine ausreichende Ähnlichkeit gefunden

# --- Hauptfunktion zum Laden und Vergleichen der Berichte ---
def process_report(report_data: list, tool_name: str, map_axe_rules: bool = False):
    """
    Verarbeitet die Rohdaten eines Berichts und generiert eine Liste von detaillierten Verletzungs-Objekten.
    """
    violations_list = []
    
    for step_report in report_data:
        url = step_report.get('url')
        if not url: continue 

        for violation in step_report.get('violations', []):
            if map_axe_rules: # Für Axe-Core-Berichte
                axe_rule_id = violation.get('id')
                wcag_criteria_list = AXE_RULE_TO_WCAG_MAP.get(axe_rule_id, [])
                
                if not wcag_criteria_list:
                    continue 
                
                nodes = violation.get('nodes', [])
                if not nodes: continue 
                
                for node in nodes:
                    node_selector = normalize_selector(node.get('target', [''])[0])
                    node_html_snippet = normalize_html_snippet_for_comparison(node.get('html', ''))

                    # DIESE ZEILE WIRD KORRIGIERT:
                    # Statt 'selector' und 'html_snippet' müssen 'node_selector' und 'node_html_snippet' verwendet werden.
                    if not node_selector and not node_html_snippet: continue 

                    for wcag_criterion_raw in wcag_criteria_list:
                        wcag_criterion_cleaned = normalize_wcag_criterion(wcag_criterion_raw)
                        
                        details = {
                            "tool": tool_name,
                            "url": url,
                            "wcag_kriterium": wcag_criterion_cleaned,
                            "rule_id": axe_rule_id,
                            "description": violation.get('description'),
                            "html": node.get('html'),
                            "html_normalized": node_html_snippet,
                            "selector": node.get('target', []),
                            "selector_normalized": node_selector,
                            "impact": violation.get('impact')
                        }
                        violations_list.append(details)
            else: # Für AI-Agent-Berichte
                # Die Variablen hier heißen schon 'selector' und 'html_snippet', also ist die Prüfung dort korrekt.
                wcag_criterion_raw = violation.get('Verletztes WCAG_kriterium', '')
                wcag_criterion_cleaned = normalize_wcag_criterion(wcag_criterion_raw)
                selector = normalize_selector(violation.get('CSS-Selektor', ''))
                html_snippet = normalize_html_snippet_for_comparison(violation.get('Html Ausschnitt auf der Webseite', ''))

                if not wcag_criterion_cleaned or (not selector and not html_snippet): continue 
                
                details = {
                    "tool": tool_name,
                    "url": url,
                    "wcag_kriterium": wcag_criterion_cleaned,
                    "beschreibung": violation.get('Beschreibung der Verletzung'),
                    "html_ausschnitt": violation.get('Html Ausschnitt auf der Webseite'), 
                    "html_normalized": html_snippet,
                    "selektor": violation.get('CSS-Selektor'),
                    "selector_normalized": selector,
                    "vorschlag": violation.get('Änderungsvorschlag'),
                    "funktion_rolle": violation.get('Funktion/Rolle des Elements im Kontext der Webseite ')
                }
                violations_list.append(details)
                
    return violations_list


def compare_wcag_violations_main(axe_report_path: str, ai_agent_report_path: str):
    print("Starte Vergleich der WCAG-Verletzungen...")
    
    # 1. Berichte laden
    try:
        with open(axe_report_path, 'r', encoding='utf-8') as f:
            axe_raw_data = json.load(f)
        with open(ai_agent_report_path, 'r', encoding='utf-8') as f:
            ai_agent_raw_data = json.load(f)
    except FileNotFoundError as e:
        print(f"Fehler: Berichtdatei nicht gefunden: {e}")
        return
    except json.JSONDecodeError as e:
        print(f"Fehler: JSON-Parsing-Fehler in Berichtdatei: {e}")
        return

    # 2. Berichte verarbeiten (jetzt als Listen von detaillierten Objekten)
    print("Verarbeite Axe-Core-Bericht...")
    axe_violations_list = process_report(axe_raw_data, "Axe-Core", map_axe_rules=True)
    print(f"Axe-Core hat {len(axe_violations_list)} potenzielle Verletzungsinstanzen gefunden.")

    print("\nVerarbeite AI-Agent-Bericht...")
    ai_violations_list = process_report(ai_agent_raw_data, "AI-Agent")
    print(f"AI-Agent hat {len(ai_violations_list)} potenzielle Verletzungsinstanzen gefunden.")


    # 3. Iterativer Vergleich, um Übereinstimmungen zu finden
    common_violations = []
    axe_only_violations = []
    ai_only_violations = []

    # Verfolge, welche AI-Verletzungen bereits abgeglichen wurden
    matched_ai_indices = [False] * len(ai_violations_list)

    # Iteriere durch Axe-Violations und suche nach einer passenden AI-Violation
    for axe_viol in axe_violations_list:
        found_match = False
        for i, ai_viol in enumerate(ai_violations_list):
            if not matched_ai_indices[i] and \
               _are_violations_similar(axe_viol, ai_viol, selector_similarity_threshold=0.8, html_similarity_threshold=0.9):
                
                common_violations.append({
                    "axe_detail": axe_viol,
                    "ai_detail": ai_viol
                })
                matched_ai_indices[i] = True # Markiere als abgeglichen
                found_match = True
                break # Nur ein Match pro Axe-Violation (nehme den ersten besten)
        
        if not found_match:
            axe_only_violations.append(axe_viol)

    # Die verbleibenden AI-Verletzungen sind einzigartig für den AI-Agenten
    for i, ai_viol in enumerate(ai_violations_list):
        if not matched_ai_indices[i]:
            ai_only_violations.append(ai_viol)

    # --- Ausgabe der Ergebnisse ---
    print("\n\n--- Vergleichsergebnisse ---")
    print(f"Gesamtzahl der einzigartigen Verletzungsinstanzen von Axe-Core: {len(axe_violations_list)}")
    print(f"Gesamtzahl der einzigartigen Verletzungsinstanzen vom AI-Agenten: {len(ai_violations_list)}")
    print(f"--------------------------------------------------")

    print(f"\n--- Verletzungen, die von BEIDEN Tools erkannt wurden ({len(common_violations)}) ---")
    if not common_violations:
        print("Keine gemeinsamen Verletzungen gefunden.")
    for i, match_pair in enumerate(common_violations):
        print(f"\n[{i+1}] Gemeinsame Verletzung:")
        print(f"  URL: {match_pair['axe_detail']['url']}")
        print(f"  WCAG Kriterium: {match_pair['axe_detail']['wcag_kriterium']}")
        print(f"  Selektor (Axe, norm.): {match_pair['axe_detail']['selector_normalized']}")
        print(f"  HTML (Axe, norm.): {match_pair['axe_detail']['html_normalized'][:100]}...")
        print(f"  ----------------------------------------")
        print(f"  Axe-Core Details: (Regel ID: {match_pair['axe_detail']['rule_id']}, Beschreibung: {match_pair['axe_detail']['description']})")
        print(f"    Original-HTML: {match_pair['axe_detail']['html'][:100]}...")
        print(f"  AI-Agent Details: (Beschreibung: {match_pair['ai_detail']['beschreibung']}, Vorschlag: {match_pair['ai_detail']['vorschlag']})")
        print(f"    Original-HTML: {match_pair['ai_detail']['html_ausschnitt'][:100]}...")
        print("---")

    print(f"\n--- Verletzungen, die NUR von Axe-Core erkannt wurden ({len(axe_only_violations)}) ---")
    if not axe_only_violations:
        print("Keine einzigartigen Verletzungen von Axe-Core gefunden.")
    for i, violation in enumerate(axe_only_violations):
        print(f"\n[{i+1}] Nur Axe-Core:")
        print(f"  URL: {violation['url']}")
        print(f"  WCAG Kriterium: {violation['wcag_kriterium']}")
        print(f"  Selektor (norm.): {violation['selector_normalized']}")
        print(f"  HTML (norm.): {violation['html_normalized'][:100]}...")
        print(f"  Regel ID: {violation.get('rule_id')}")
        print(f"  Beschreibung: {violation.get('description')}")
        print(f"  Original-HTML: {violation.get('html', '')[:100]}...")
        print("---")

    print(f"\n--- Verletzungen, die NUR vom AI-Agenten erkannt wurden ({len(ai_only_violations)}) ---")
    if not ai_only_violations:
        print("Keine einzigartigen Verletzungen vom AI-Agenten gefunden.")
    for i, violation in enumerate(ai_only_violations):
        print(f"\n[{i+1}] Nur AI-Agent:")
        print(f"  URL: {violation['url']}")
        print(f"  WCAG Kriterium: {violation['wcag_kriterium']}")
        print(f"  Selektor (norm.): {violation['selector_normalized']}")
        print(f"  HTML (norm.): {violation['html_normalized'][:100]}...")
        print(f"  Beschreibung: {violation.get('beschreibung')}")
        print(f"  Vorschlag: {violation.get('vorschlag', '')[:100]}...")
        print(f"  Funktion/Rolle: {violation.get('funktion_rolle', '')}")
        print(f"  Original-HTML: {violation.get('html_ausschnitt', '')[:100]}...")
        print("---")

# --- Ausführung des Vergleichs ---
if __name__ == "__main__":
    compare_wcag_violations_main(AXE_REPORT_PATH, AI_AGENT_REPORT_PATH)