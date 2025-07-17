import json
import re
from bs4 import BeautifulSoup # Stellen Sie sicher, dass beautifulsoup4 installiert ist (pip install beautifulsoup4)
import difflib # Für potenzielle Fuzzy-Matches, wenn nötig

# --- Konfiguration ---
AXE_REPORT_PATH = "axe.json"      # Beispiel: Bericht vom JS-axe-scanner
AI_AGENT_REPORT_PATH = "agent2.json" # Beispiel: Bericht vom Python-AI-Agenten


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

# --- Hilfsfunktion zur Normalisierung von CSS-Selektoren ---
def normalize_selector(selector: str) -> str:
    if not isinstance(selector, str):
        if isinstance(selector, list) and selector:
            selector = selector[0]
        else:
            return ""
    selector = selector.replace('\\:', ':')
    parts = selector.split('>')
    last_part = parts[-1].strip()
    return re.sub(r'\s+', ' ', last_part).strip().lower()

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
        
        # Nehmen das erste Tag im Snippet, falls es mehrere gibt (z.B. bei Leerzeichen am Anfang)
        first_tag = soup.find()

        if not first_tag: # Wenn das Snippet keinen gültigen HTML-Tag enthält (z.B. nur Text)
            return re.sub(r'\s+', ' ', html_str).strip().lower() # Nur Whitespace normalisieren

        # Liste der Attribute, die ignoriert/entfernt werden sollen, da sie oft dynamisch, intern oder für den Vergleich irrelevant sind.
        # DIESE LISTE KANN JE NACH SPEZIFISCHER WEBSITE OPTIMIERT WERDEN!
        attributes_to_remove_from_comparison = [
            'id',               # IDs sind oft dynamisch
            'style',            # Inline-Stile oft dynamisch
            'tabindex',         # Zustand kann sich ändern
            'data-initialized', # Initialisierungsflag
            'data-loadurl',     # URL für dynamisches Laden
            'data-preload',
            'data-loaded',
            'data-href',        # Kann sich bei relativen Pfaden ändern
            'data-funder-legal-name',
            'data-advertiser-legal-name',
            'data-origin',
            'data-amount-colors',
            'data-sheet-id',
            'data-sheet-url',
            'data-sheet-title',
            'data-sheet-tracking-object',
            'data-sheet-menu-content',
            'data-select-mode',
            'data-login-state',
            'data-loggedin',
            'data-nav-initialized',
            'data-nav-track',
            'data-nav-testing',
            'data-nav-tracking-click-breadcrumb-headline',
            'data-ts-labels',
            'data-ts-move',
            'data-tracking-feature-id',
            'data-producttile-tracking',
            'data-qa-id',       # Spezifische QA-IDs können auch dynamisch sein
            'checked',          # Zustand eines Radio-Buttons/Checkbox
            'selected',         # Zustand eines Select-Elements
            'disabled',         # Zustand eines Elements
            'maxlength',        # oft konstant, aber kann variieren
            'value',            # Wert von Input-Feldern kann sich ändern, außer bei festen Werten (wie 'XXL')
                                # Hier entfernen wir es, um den Fokus auf die Struktur zu legen.
            'size',             # Größe eines Custom Elements
            'hidden'            # Zustand (sichtbar/unsichtbar)
        ]
        # Regex für Svelte- oder andere JS-Framework-spezifische Hash-Klassen (z.B. 'svelte-xxxxxx')
        SVELTE_CLASS_REGEX = r'svelte-[a-zA-Z0-9]+'

        # Kanonische Attribute sammeln
        canonical_attrs = {}
        for attr_name, attr_value in first_tag.attrs.items():
            attr_name_lower = attr_name.lower()

            if attr_name_lower in attributes_to_remove_from_comparison:
                continue
            
            # Spezielle Behandlung für 'class'-Attribut
            if attr_name_lower == 'class':
                # Entferne Svelte-Hashes und sortiere Klassennamen
                class_values = [cls for cls in str(attr_value).split() if not re.match(SVELTE_CLASS_REGEX, cls)]
                if class_values:
                    canonical_attrs[attr_name_lower] = ' '.join(sorted(class_values))
                continue

            # Alle anderen Attribute (außer den zu entfernenden) werden beibehalten
            # Wichtig: attr_value könnte ein String oder eine Liste (für multi-value attrs) sein
            if isinstance(attr_value, list):
                canonical_attrs[attr_name_lower] = ' '.join(sorted([str(v).strip() for v in attr_value]))
            else:
                canonical_attrs[attr_name_lower] = str(attr_value).strip()

        # Sortiere verbleibende Attribute für konsistente String-Repräsentation
        sorted_attr_strings = []
        for k, v in sorted(canonical_attrs.items()):
            # Escape Anführungszeichen innerhalb des Attributwerts, falls vorhanden
            v_escaped = v.replace('"', '\\"')
            sorted_attr_strings.append(f'{k}="{v_escaped}"')
        
        # Holen Sie den Tag-Namen und den inneren Text
        tag_name = first_tag.name.lower()
        
        # Behandeln Sie den inneren Text. Ignoriere Inhalt von SVG-Elementen oder <slot> für den Vergleich.
        inner_text_content = ""
        # Prüfe, ob das Tag ein SVG ist oder einen Slot enthält (um dynamischen/unrelevanten Text zu ignorieren)
        if tag_name == 'svg' or first_tag.find('slot'): 
            inner_text_content = "<slot_or_svg_content>" # Platzhalter für Inhalt von SVG/Slot
        else:
            inner_text_content = re.sub(r'\s+', ' ', first_tag.get_text(strip=True)).strip()
        

        # Baue die kanonische Tag-String-Repräsentation
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
        # Fallback: Nur Whitespace normalisieren, wenn Parsen fehlschlägt
        return re.sub(r'\s+', ' ', html_str).strip().lower()

# --- Rest des Skripts (process_report, compare_wcag_violations, if __name__ == "__main__":) bleiben unverändert ---
# ... (Der Rest des Codes ist identisch zur vorherigen Antwort) ...

# Hauptfunktion zum Laden und Vergleichen der Berichte
def compare_wcag_violations(axe_report_path: str, ai_agent_report_path: str):
    # ... (Code wie in der vorherigen Antwort) ...
    # Code ist identisch zur vorherigen Antwort, nur die normalize_html_snippet Funktion ist neu/geändert.

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

    # Sets für die eindeutigen Verletzungs-IDs
    # Format der ID: (URL, WCAG_KRITERIUM, NORMALISIERTER_CSS_SELEKTOR, NORMALISIERTER_HTML_SCHNIPSEL)
    axe_violations_set = set()
    ai_violations_set = set()

    # Gesammelte Details für die Ausgabe
    axe_violation_details = {}  # {id: violation_obj}
    ai_violation_details = {}   # {id: violation_obj}

    # 2. Axe-Core-Ergebnisse verarbeiten
    for step_report in axe_raw_data:
        url = step_report.get('url')
        if not url: continue 

        for violation in step_report.get('violations', []):
            axe_rule_id = violation.get('id')
            wcag_criteria_list = AXE_RULE_TO_WCAG_MAP.get(axe_rule_id, [])
            
            if not wcag_criteria_list:
                continue 
            
            nodes = violation.get('nodes', [])
            if not nodes: continue 
            
            for node in nodes:
                selector = normalize_selector(node.get('target', [''])[0])
                html_snippet = normalize_html_snippet_for_comparison(node.get('html', '')) # <-- NUTZT DIE VERBESSERTE NORMALISIERUNG

                if not selector and not html_snippet: continue 

                for wcag_criterion_raw in wcag_criteria_list:
                    wcag_criterion_cleaned = normalize_wcag_criterion(wcag_criterion_raw)
                    unique_id = (url, wcag_criterion_cleaned, selector, html_snippet)
                    axe_violations_set.add(unique_id)
                    axe_violation_details[unique_id] = {
                        "tool": "Axe-Core",
                        "rule_id": axe_rule_id,
                        "description": violation.get('description'),
                        "html": node.get('html'), 
                        "target": node.get('target', []),
                        "impact": violation.get('impact')
                    }
    
    # 3. AI-Agent-Ergebnisse verarbeiten
    for step_report in ai_agent_raw_data:
        url = step_report.get('url')
        if not url: continue

        for violation in step_report.get('violations', []):
            wcag_criterion_raw = violation.get('Verletztes WCAG_kriterium', '')
            wcag_criterion_cleaned = normalize_wcag_criterion(wcag_criterion_raw)
            selector = normalize_selector(violation.get('CSS-Selektor', ''))
            html_snippet = normalize_html_snippet_for_comparison(violation.get('Html Ausschnitt auf der Webseite', '')) # <-- NUTZT DIE VERBESSERTE NORMALISIERUNG

            if not wcag_criterion_cleaned or (not selector and not html_snippet): continue 

            unique_id = (url, wcag_criterion_cleaned, selector, html_snippet)
            ai_violations_set.add(unique_id)
            ai_violation_details[unique_id] = {
                "tool": "AI-Agent",
                "wcag_kriterium": wcag_criterion_raw,
                "beschreibung": violation.get('Beschreibung der Verletzung'),
                "html_ausschnitt": violation.get('Html Ausschnitt auf der Webseite'), 
                "selektor": violation.get('CSS-Selektor'),
                "vorschlag": violation.get('Änderungsvorschlag'),
                "funktion_rolle": violation.get('Funktion/Rolle des Elements im Kontext der Webseite ')
            }

    # ... (Rest der Vergleichs- und Ausgabe-Logik ist unverändert) ...
    common_violations = axe_violations_set.intersection(ai_violations_set)
    axe_only_violations = axe_violations_set.difference(ai_violations_set)
    ai_only_violations = ai_violations_set.difference(axe_violations_set)

    print("\n\n--- Vergleichsergebnisse ---")
    print(f"Gesamtzahl der eindeutigen Verletzungen von Axe-Core: {len(axe_violations_set)}")
    print(f"Gesamtzahl der eindeutigen Verletzungen vom AI-Agenten: {len(ai_violations_set)}")
    print(f"--------------------------------------------------")

    print(f"\n--- Verletzungen, die von BEIDEN Tools erkannt wurden ({len(common_violations)}) ---")
    if not common_violations:
        print("Keine gemeinsamen Verletzungen gefunden.")
    for i, violation_id in enumerate(common_violations):
        axe_detail = axe_violation_details.get(violation_id, {})
        ai_detail = ai_violation_details.get(violation_id, {})
        print(f"\n[{i+1}] Gemeinsame Verletzung:")
        print(f"  URL: {violation_id[0]}")
        print(f"  WCAG Kriterium: {violation_id[1]}")
        print(f"  Selektor (norm.): {violation_id[2]}")
        print(f"  HTML (norm.): {violation_id[3][:100]}...") # Angezeigtes HTML-Schnipsel gekürzt
        print(f"  ----------------------------------------")
        print(f"  Axe-Core Details: (Regel ID: {axe_detail.get('rule_id')}, Beschreibung: {axe_detail.get('description')[:100]}...)")
        print(f"    Original-HTML: {axe_detail.get('html', '')[:100]}...")
        print(f"  AI-Agent Details: (Beschreibung: {ai_detail.get('beschreibung')[:100]}..., Vorschlag: {ai_detail.get('vorschlag', '')[:100]}...)")
        print(f"    Original-HTML: {ai_detail.get('html_ausschnitt', '')[:100]}...")
        print("---")

    print(f"\n--- Verletzungen, die NUR von Axe-Core erkannt wurden ({len(axe_only_violations)}) ---")
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
        print(f"  Original-HTML: {axe_detail.get('html', '')[:100]}...")
        print("---")

    print(f"\n--- Verletzungen, die NUR vom AI-Agenten erkannt wurden ({len(ai_only_violations)}) ---")
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
        print(f"  Original-HTML: {ai_detail.get('html_ausschnitt', '')[:100]}...")
        print("---")

# --- Ausführung des Vergleichs ---
if __name__ == "__main__":
    compare_wcag_violations(AXE_REPORT_PATH, AI_AGENT_REPORT_PATH)