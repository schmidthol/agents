import json
import os

# --- Konfiguration ---
AI_AGENT_REPORT_PATH = "agent.json" # <--- Stellen Sie sicher, dass dies der korrekte Dateiname ist

# --- Hilfsfunktion zum Parsen der "Anzahl der Verletzungen" ---
def parse_num_violations(num_str_raw) -> int:
    """
    Parst den Wert der 'Anzahl der Verletzungen'.
    Zählt 'Mehrere' als 2.
    Zählt numerische Strings als Integer.
    Zählt alle anderen (inkl. fehlende) als 1.
    """
    if isinstance(num_str_raw, (int, float)):
        return int(num_str_raw) # Direkt als Integer nehmen

    if isinstance(num_str_raw, str):
        num_str_lower = num_str_raw.lower().strip()
        if num_str_lower == "mehrere":
            return 2 # Wie gewünscht: "Mehrere" wird als 2 gezählt
        try:
            return int(num_str_lower) # Versuch, in Integer zu konvertieren
        except ValueError:
            return 1 # Fallback für nicht-numerische Strings
    
    return 1 # Fallback für den Fall, dass der Wert None oder ein unerwarteter Typ ist

# --- Hauptlogik des Skripts ---
if __name__ == "__main__":
    total_violations_count = 0

    # 1. JSON-Datei laden
    if not os.path.exists(AI_AGENT_REPORT_PATH):
        print(f"Fehler: Die Datei '{AI_AGENT_REPORT_PATH}' wurde nicht gefunden.")
        print("Bitte stellen Sie sicher, dass die Datei im selben Verzeichnis wie das Skript liegt.")
        exit()

    try:
        with open(AI_AGENT_REPORT_PATH, 'r', encoding='utf-8') as f:
            ai_agent_data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Fehler: Ungültiges JSON-Format in '{AI_AGENT_REPORT_PATH}': {e}")
        exit()
    except Exception as e:
        print(f"Ein unerwarteter Fehler ist beim Lesen der Datei aufgetreten: {e}")
        exit()

    # 2. Iteriere durch die Verletzungen und summiere die Anzahlen
    if not isinstance(ai_agent_data, list):
        print("Fehler: Das Hauptobjekt der JSON-Datei ist keine Liste von Schritten.")
        exit()

    for step_report in ai_agent_data:
        if 'violations' in step_report and isinstance(step_report['violations'], list):
            for violation in step_report['violations']:
                # 'get' mit Standardwert '1', falls der Schlüssel fehlt
                num_violations_raw = violation.get('Anzahl der Verletzungen', '1')
                total_violations_count += parse_num_violations(num_violations_raw)

    # 3. Ergebnis ausgeben
    print(f"Gesamtzahl der Verletzungen (mit 'Mehrere' als 2 gezählt) in '{AI_AGENT_REPORT_PATH}': {total_violations_count}")