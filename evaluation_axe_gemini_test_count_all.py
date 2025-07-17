import json
import re
from bs4 import BeautifulSoup
import difflib

# --- Konfiguration ---
# Pfade zu den JSON-Berichten der beiden Tools
AXE_REPORT_PATH = "axe.json"
AI_AGENT_REPORT_PATH = "agent.json"


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
    """Entfernt Konformitätsstufen und unnötige Leerzeichen für den Vergleich."""
    return re.sub(r'\s*\([A|AA]+\)$', '', criterion_str).strip()

# --- Hilfsfunktion zur Normalisierung von CSS-Selektoren ---
def normalize_selector(selector: str) -> str:
    """
    Bereinigt einen CSS-Selektor für den Vergleich und extrahiert den letzten Teil nach dem '>' Kombinator.
    """
    if not isinstance(selector, str):
        if isinstance(selector, list) and selector:
            selector = selector[0]
        else:
            return ""
    selector = selector.replace('\\:', ':')
    parts = selector.split('>')
    last_part = parts[-1].strip()
    return re.sub(r'\s+', ' ', last_part).strip().lower()

# --- NEU: Hilfsfunktion, um verschiedene Formen eines Selektors für den Vergleich zu erzeugen ---
def _get_selector_comparison_forms(selector: str) -> list[str]:
    """
    Erzeugt eine Liste von Selector-Formen für einen flexibleren Vergleich.
    """
    forms = [selector]
    if '>' in selector:
        forms.append(selector.split('>')[-1].strip())
    if ' ' in selector: # Descendant combinator
        forms.append(selector.split(' ')[-1].strip())
    return list(set(forms))

# --- VERBESSERT: Hilfsfunktion zur Normalisierung von HTML-Ausschnitten ---
def normalize_html_snippet_for_comparison(html_str: str) -> str:
    """
    Normalisiert einen HTML-Ausschnitt für den Vergleich.
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
            'data-qa-id', 
            'checked', 'selected', 'value', 'type', 'name', 
            'size' 
        ]
        SVELTE_CLASS_REGEX = r'svelte-[a-zA-Z0-9]+'

        canonical_attrs = {}
        for attr_name, attr_value in first_tag.attrs.items():
            attr_name_lower = attr_name.lower()

            if attr_name_lower in attributes_to_remove_from_comparison:
                continue
            
            if attr_name_lower == 'class':
                class_values = [cls for cls in str(attr_value).split() if not re.match(SVELTE_CLASS_REGEX, cls)]
                if class_values:
                    canonical_attrs[attr_name_lower] = ' '.join(sorted(class_values))
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
    axe_wcag = axe_viol_detail.get('wcag_kriterium')
    ai_wcag = ai_viol_detail.get('wcag_kriterium')
    if axe_wcag != ai_wcag:
        return False

    # 3. HTML-Ausschnitt-Vergleich (primär)
    axe_html_norm = axe_viol_detail.get('html_normalized')
    ai_html_norm = ai_viol_detail.get('html_normalized')
    
    html_similarity = difflib.SequenceMatcher(None, axe_html_norm, ai_html_norm).ratio()
    if html_similarity >= html_similarity_threshold:
        return True

    # 4. CSS-Selektor-Vergleich (sekundär, wenn HTML-Match nicht stark genug)
    axe_selector_norm = axe_viol_detail.get('selector_normalized')
    ai_selector_norm = ai_viol_detail.get('selector_normalized')

    axe_selector_forms = _get_selector_comparison_forms(axe_selector_norm)
    ai_selector_forms = _get_selector_comparison_forms(ai_selector_norm)

    for axe_form in axe_selector_forms:
        for ai_form in ai_selector_forms:
            if axe_form in ai_form or ai_form in axe_form:
                if difflib.SequenceMatcher(None, axe_form, ai_form).ratio() >= selector_similarity_threshold:
                    return True

    return False

# --- Hauptfunktion zum Laden und Vergleichen der Berichte ---
def process_report(report_data: list, tool_name: str, map_axe_rules: bool = False):
    """
    Verarbeitet die Rohdaten eines Berichts und generiert eine Liste von detaillierten Verletzungs-Objekten.
    Zählt auch die Gesamtanzahl der gemeldeten Instanzen.
    """
    violations_list = []
    total_reported_instances = 0
    
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
                
                for node in nodes: # Jedes Node ist eine separate Instanz von Axe-Core
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
                            "impact": violation.get('impact'),
                            "num_instances_reported": 1 # Axe zählt pro Node als 1 Instanz
                        }
                        violations_list.append(details)
                        total_reported_instances += 1

            else: # Für AI-Agent-Berichte
                wcag_criterion_raw = violation.get('Verletztes WCAG_kriterium', '')
                wcag_criterion_cleaned = normalize_wcag_criterion(wcag_criterion_raw)
                selector = normalize_selector(violation.get('CSS-Selektor', ''))
                html_snippet = normalize_html_snippet_for_comparison(violation.get('Html Ausschnitt auf der Webseite', ''))

                if not wcag_criterion_cleaned or (not selector and not html_snippet): continue 
                
                num_instances_raw = violation.get('Anzahl der Verletzungen', '1')
                num_instances_parsed = 1
                if isinstance(num_instances_raw, str):
                    if num_instances_raw.lower() == "mehrere":
                        num_instances_parsed = 2
                    else:
                        try:
                            num_instances_parsed = int(num_instances_raw)
                        except ValueError:
                            num_instances_parsed = 1
                elif isinstance(num_instances_raw, (int, float)):
                    num_instances_parsed = int(num_instances_raw)

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
                    "funktion_rolle": violation.get('Funktion/Rolle des Elements im Kontext der Webseite '),
                    "num_instances_reported": num_instances_parsed
                }
                violations_list.append(details)
                total_reported_instances += num_instances_parsed
                
    return violations_list, total_reported_instances

def compare_wcag_violations_main(axe_report_path: str, ai_agent_report_path: str):
    print("Starte Vergleich der WCAG-Verletzungen...")
    
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

    print("Verarbeite Axe-Core-Bericht...")
    axe_violations_list, total_axe_reported_instances = process_report(axe_raw_data, "Axe-Core", map_axe_rules=True)
    print(f"Axe-Core hat {len(axe_violations_list)} eindeutige Verletzungsinstanzen gefunden.")

    print("\nVerarbeite AI-Agent-Bericht...")
    ai_violations_list, total_ai_reported_instances = process_report(ai_agent_raw_data, "AI-Agent")
    print(f"AI-Agent hat {len(ai_violations_list)} eindeutige Verletzungsinstanzen gefunden.")

    common_violations = []
    axe_only_violations = []
    ai_only_violations = []

    matched_ai_indices = [False] * len(ai_violations_list)

    for axe_viol in axe_violations_list:
        found_match = False
        for i, ai_viol in enumerate(ai_violations_list):
            if not matched_ai_indices[i] and \
               _are_violations_similar(axe_viol, ai_viol, selector_similarity_threshold=0.8, html_similarity_threshold=0.9):
                
                common_violations.append({
                    "axe_detail": axe_viol,
                    "ai_detail": ai_viol
                })
                matched_ai_indices[i] = True
                found_match = True
                break
        
        if not found_match:
            axe_only_violations.append(axe_viol)

    for i, ai_viol in enumerate(ai_violations_list):
        if not matched_ai_indices[i]:
            ai_only_violations.append(ai_viol)

    print("\n\n--- Vergleichsergebnisse ---")
    print(f"Gesamtzahl der eindeutigen Verletzungsinstanzen von Axe-Core: {total_axe_reported_instances}")
    print(f"Gesamtzahl der eindeutigen Verletzungsinstanzen vom AI-Agenten: {total_ai_reported_instances}")
    print(f"--------------------------------------------------")
    print(f"Anzahl der gemeinsamen Verletzungs-Typen (nach unserer Ähnlichkeitslogik): {len(common_violations)}")
    
    total_ai_common_instances = sum(match_pair['ai_detail'].get('num_instances_reported', 1) for match_pair in common_violations)
    print(f"Summe der Instanzen für gemeinsame Verletzungen (vom AI-Agenten gemeldet): {total_ai_common_instances}")


    print(f"\n--- Verletzungen, die von BEIDEN Tools erkannt wurden ({len(common_violations)} Typen) ---")
    if not common_violations:
        print("Keine gemeinsamen Verletzungen gefunden.")
    for i, match_pair in enumerate(common_violations):
        print(f"\n[{i+1}] Gemeinsame Verletzung:")
        print(f"  URL: {match_pair['axe_detail']['url']}")
        print(f"  WCAG Kriterium: {match_pair['axe_detail']['wcag_kriterium']}")
        print(f"  Selektor (norm.): {match_pair['axe_detail']['selector_normalized']}")
        print(f"  HTML (norm.): {match_pair['axe_detail']['html_normalized'][:100]}...")
        print(f"  ----------------------------------------")
        print(f"  Axe-Core Details: (Regel ID: {axe_detail.get('rule_id')}, Beschreibung: {axe_detail.get('description')[:100]}...)")
        print(f"    Original-HTML: {axe_detail.get('html', '')[:100]}...")
        print(f"  AI-Agent Details: (Beschreibung: {ai_detail.get('beschreibung')[:100]}..., Vorschlag: {ai_detail.get('vorschlag', '')[:100]}...)")
        print(f"    Original-HTML: {ai_detail.get('html_ausschnitt', '')[:100]}...")
        print("---")

    print(f"\n--- Verletzungen, die NUR von Axe-Core erkannt wurden ({len(axe_only_violations)} Typen) ---")
    if not axe_only_violations:
        print("Keine einzigartigen Verletzungen von Axe-Core gefunden.")
    for i, violation_id in enumerate(axe_only_violations):
        axe_detail = axe_violation_details.get(violation_id, {})
        print(f"\n[{i+1}] Nur Axe-Core:")
        print(f"  URL: {violation_id[0]}")
        print(f"  WCAG Kriterium: {violation_id[1]}")
        print(f"  Selektor (norm.): {violation_id[2]}")
        print(f"  HTML (norm.): {violation_id[3][:100]}...")
        print(f"  Regel ID: {axe_detail.get('rule_id')}")
        print(f"  Beschreibung: {axe_detail.get('description')}")
        print(f"  Anzahl Instanzen (Axe): {violation_id[4] if len(violation_id) > 4 else 'N/A'}") # Needs adjustment if num_instances is in tuple
        print(f"  Original-HTML: {violation_id[5] if len(violation_id) > 5 else axe_detail.get('html', '')[:100]}...") # Needs adjustment
        print("---")

    print(f"\n--- Verletzungen, die NUR vom AI-Agenten erkannt wurden ({len(ai_only_violations)} Typen) ---")
    if not ai_only_violations:
        print("Keine einzigartigen Verletzungen vom AI-Agenten gefunden.")
    for i, violation_id in enumerate(ai_only_violations):
        ai_detail = ai_violation_details.get(violation_id, {})
        print(f"\n[{i+1}] Nur AI-Agent:")
        print(f"  URL: {violation_id[0]}")
        print(f"  WCAG Kriterium: {violation_id[1]}")
        print(f"  Selektor (norm.): {violation_id[2]}")
        print(f"  HTML (norm.): {violation_id[3][:100]}...")
        print(f"  Beschreibung: {ai_detail.get('beschreibung')}")
        print(f"  Vorschlag: {ai_detail.get('vorschlag', '')[:100]}...")
        print(f"  Funktion/Rolle: {ai_detail.get('funktion_rolle', '')}")
        print(f"  Anzahl Instanzen (AI): {violation_id[4] if len(violation_id) > 4 else 'N/A'}") # Needs adjustment
        print(f"  Original-HTML: {violation_id[5] if len(violation_id) > 5 else ai_detail.get('html_ausschnitt', '')[:100]}...") # Needs adjustment
        print("---")

# --- Ausführung des Vergleichs ---
compare_wcag_violations_main(AXE_REPORT_PATH, AI_AGENT_REPORT_PATH)
#The script execution failed with a `ModuleNotFoundError: No module named 'bs4'`. This indicates that the `beautifulsoup4` library is not installed in the Python environment where the script is being executed.
