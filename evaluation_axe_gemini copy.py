import json
import re
from bs4 import BeautifulSoup # pip install beautifulsoup4

# --- Konfiguration ---
# Pfade zu den JSON-Berichten der beiden Tools
# Bitte passen Sie diese Pfade an Ihre tatsächlichen Dateinamen an!
AXE_REPORT_PATH = "axe.json"      # Beispiel: Bericht vom JS-axe-scanner
AI_AGENT_REPORT_PATH = "agent.json" # Beispiel: Bericht vom Python-AI-Agenten


# --- Mapping von Axe-Core Rule IDs zu WCAG Erfolgskriterien (Basis für den Vergleich) ---
# Dieses Mapping ist entscheidend für den Abgleich zwischen Axe-IDs und WCAG-Kriterien.
AXE_RULE_TO_WCAG_MAP = {
    "aria-alt": ["2.4.4 Linkzweck (Im Kontext)", "4.1.2 Name, Rolle, Wert"], # Ihre spezifische Regel
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

# --- Hilfsfunktion zur Normalisierung von HTML-Ausschnitten ---
def normalize_html_snippet(html_str: str) -> str:
    """
    Normalisiert einen HTML-Ausschnitt für den Vergleich.
    Entfernt irrelevante Attribute, sortiert die verbleibenden Attribute und normalisiert Whitespace.
    """
    if not isinstance(html_str, str):
        return ""

    try:
        # Parsen des HTML-Ausschnitts mit BeautifulSoup
        soup = BeautifulSoup(html_str, 'html.parser')
        
        # Nehmen das erste Tag im Snippet, da axe-core und der AI-Agent oft einzelne Element-Snippets liefern
        target_tag = soup.find()

        if not target_tag: # Wenn es nur Text ist oder ungültiges HTML ohne Tag
            return re.sub(r'\s+', ' ', html_str).strip().lower() # Nur Whitespace normalisieren

        # Attribute, die in der Regel dynamisch, intern oder für den semantischen Vergleich irrelevant sind
        # (Dies ist eine heuristische Liste, die für otto.de angepasst wurde und ggf. weitere Tuning benötigt)
        attributes_to_remove = [
            'id', 'style', 'tabindex', 'data-initialized', 'data-loadurl', 'data-preload',
            'data-href', 'data-funder-legal-name', 'data-advertiser-legal-name', 'data-origin',
            'data-amount-colors', 'data-sheet-id', 'data-sheet-url', 'data-sheet-title',
            'data-sheet-tracking-object', 'data-sheet-menu-content', 'data-select-mode',
            'data-login-state', 'data-loggedin', 'data-nav-initialized', 'data-nav-track',
            'data-nav-testing', 'data-nav-tracking-click-breadcrumb-headline', 'data-ts-labels',
            'data-ts-move', 'data-tracking-feature-id', 'data-producttile-tracking',
            'data-qa-id', # 'data-qa' ohne ID-Suffix wird beibehalten, da es oft ein guter Selektor ist
            'checked', 'selected', 'value', 'type', 'name', # Diese sind funktional, aber können dynamische Zustände sein. Vorsicht beim Entfernen!
                                                            # Entferne sie, um den Vergleich auf die Struktur zu fokussieren.
            'size' # Custom element attribute like size="100"
        ]
        # Regex für Svelte-spezifische Hashes in Klassennamen (z.B. svelte-xxxxxx)
        SVELTE_CLASS_REGEX = r'svelte-[a-zA-Z0-9]+'

        # Bereinige und sortiere Attribute
        cleaned_attrs = {}
        for attr_name, attr_value in target_tag.attrs.items():
            attr_name_lower = attr_name.lower()

            # Entferne Attribute aus der Blacklist
            if attr_name_lower in attributes_to_remove:
                continue
            
            # Spezielle Behandlung für 'class'-Attribut
            if attr_name_lower == 'class':
                # Entferne Svelte-Hashes und sortiere Klassennamen
                class_values = [cls for cls in str(attr_value).split() if not re.match(SVELTE_CLASS_REGEX, cls)]
                if class_values: # Füge nur hinzu, wenn Klassen übrig bleiben
                    cleaned_attrs[attr_name_lower] = ' '.join(sorted(class_values))
                continue # Weiter zum nächsten Attribut

            # Standard-Attribute behalten, Wert normalisieren
            cleaned_attrs[attr_name_lower] = str(attr_value).strip()

        # Erstelle eine sortierte Attributs-Liste für die kanonische String-Repräsentation
        sorted_attr_strings = []
        for k, v in sorted(cleaned_attrs.items()):
            if v: # Füge nur Attribute mit Wert hinzu (z.B. wenn class leer nach Filterung)
                sorted_attr_strings.append(f'{k}="{v}"')
        
        # Holen Sie den Textinhalt des Tags und normalisieren Sie ihn
        # Bei <slot> Tags ist der Textinhalt nicht direkt im Snippet, nur der Slot selbst
        inner_text = target_tag.get_text(strip=True)
        inner_text = re.sub(r'\s+', ' ', inner_text).strip() # Normalisiere Whitespace im Text

        # Baue die normalisierte Tag-String-Repräsentation
        normalized_tag_str = f"<{target_tag.name}"
        if sorted_attr_strings:
            normalized_tag_str += " " + " ".join(sorted_attr_strings)
        normalized_tag_str += ">"

        if inner_text:
            normalized_tag_str += inner_text
        elif target_tag.contents and any(c.name == 'slot' for c in target_tag.contents if c.name): # Prüfe auf <slot> Kinder
             normalized_tag_str += "<slot>" # Repräsentiere Slot-Inhalt einfach als "<slot>"
        
        normalized_tag_str += f"</{target_tag.name}>"

        return normalized_tag_str.lower()

    except Exception as e:
        # Im Fehlerfall (z.B. ungültiges HTML), gib den Original-HTML-String normalisiert zurück
        print(f"Warnung: Fehler beim Normalisieren des HTML-Ausschnitts '{html_str[:50]}...': {e}")
        return re.sub(r'\s+', ' ', html_str).strip().lower() # Fallback

# --- Hilfsfunktion zur Normalisierung von CSS-Selektoren ---
def normalize_selector(selector: str) -> str:
    """Bereinigt einen CSS-Selektor für den Vergleich."""
    if isinstance(selector, list):
        # Wenn target ein Array von Selektoren ist (wie bei axe-core), nimm den ersten
        selector = selector[0] if selector else ""
    # Entferne unnötige Leerzeichen und konvertiere zu Kleinbuchstaben für bessere Vergleichbarkeit
    # Entferne escapes für z.B. xlink:href
    selector = selector.replace('\\:', ':') # Entferne Escape für Colons
    return re.sub(r'\s+', ' ', selector).strip().lower()

# --- Hauptfunktion zum Laden und Vergleichen der Berichte ---
def compare_wcag_violations(axe_report_path: str, ai_agent_report_path: str):
    # ... (Rest des Codes wie in der vorherigen Antwort) ...
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
    for step_report in axe_raw_data: # Iterate directly over the list of steps
        url = step_report.get('url')
        if not url: continue 

        for violation in step_report.get('violations', []):
            axe_rule_id = violation.get('id')
            wcag_criteria_list = AXE_RULE_TO_WCAG_MAP.get(axe_rule_id, [])
            
            if not wcag_criteria_list:
                # print(f"Warnung: Axe-Core Regel '{axe_rule_id}' nicht in AXE_RULE_TO_WCAG_MAP gefunden. Ignoriere.")
                continue 
            
            nodes = violation.get('nodes', [])
            if not nodes: continue 
            
            for node in nodes:
                selector = normalize_selector(node.get('target', [''])[0])
                html_snippet = normalize_html_snippet(node.get('html', '')) # <-- NEU: HTML-Schnipsel normalisieren

                if not selector and not html_snippet: continue # Wenn beides leer ist, überspringe

                for wcag_criterion_raw in wcag_criteria_list:
                    wcag_criterion_cleaned = normalize_wcag_criterion(wcag_criterion_raw)
                    unique_id = (url, wcag_criterion_cleaned, selector, html_snippet) # <-- NEU: HTML-Schnipsel in ID
                    axe_violations_set.add(unique_id)
                    axe_violation_details[unique_id] = {
                        "tool": "Axe-Core",
                        "rule_id": axe_rule_id,
                        "description": violation.get('description'),
                        "html": node.get('html'), # Original-HTML für Ausgabe
                        "target": node.get('target', [])
                    }
    
    # 3. AI-Agent-Ergebnisse verarbeiten
    for step_report in ai_agent_raw_data: # Iterate directly over the list of steps
        url = step_report.get('url')
        if not url: continue

        for violation in step_report.get('violations', []):
            wcag_criterion_raw = violation.get('Verletztes WCAG_kriterium', '')
            wcag_criterion_cleaned = normalize_wcag_criterion(wcag_criterion_raw)
            selector = normalize_selector(violation.get('CSS-Selektor', ''))
            html_snippet = normalize_html_snippet(violation.get('Html Ausschnitt auf der Webseite', '')) # <-- NEU: HTML-Schnipsel normalisieren

            if not wcag_criterion_cleaned or (not selector and not html_snippet): continue # Wenn kein Kriterium oder beide leer sind

            unique_id = (url, wcag_criterion_cleaned, selector, html_snippet) # <-- NEU: HTML-Schnipsel in ID
            ai_violations_set.add(unique_id)
            ai_violation_details[unique_id] = {
                "tool": "AI-Agent",
                "wcag_kriterium": wcag_criterion_raw,
                "beschreibung": violation.get('Beschreibung der Verletzung'),
                "html_ausschnitt": violation.get('Html Ausschnitt auf der Webseite'), # Original-HTML für Ausgabe
                "selektor": violation.get('CSS-Selektor'),
                "vorschlag": violation.get('Änderungsvorschlag'),
                "funktion_rolle": violation.get('Funktion/Rolle des Elements im Kontext der Webseite ')
            }

    # 4. Vergleich durchführen (bleibt gleich, da Sets genutzt werden)
    common_violations = axe_violations_set.intersection(ai_violations_set)
    axe_only_violations = axe_violations_set.difference(ai_violations_set)
    ai_only_violations = ai_violations_set.difference(axe_violations_set)

    # --- Ausgabe der Ergebnisse ---
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
        print(f"  HTML (norm.): {violation_id[3][:100]}...") # Angezeigtes HTML-Snippet gekürzt
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