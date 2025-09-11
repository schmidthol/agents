
---------
AI-Agent:
---------

Prompt (Answeisung) des AI-Agenten (inklusive des gescrapten HTML Codes):
prompt_text = f"""
    Analysiere den folgenden HTML-Code einer Webseite auf Verletzungen der WCAG Kriterien, insbesondere in Bezug auf semantisches Verständnis und Kontext.
    Konzentriere dich auf alle folgenden WCAG Erfolgskriterien:
 
    - 1.1.1 Nicht-Text-Inhalt (A)
    - 1.3.1 Info und Beziehungen (A)
    - 1.3.2 Bedeutungstragende Reihenfolge (A)
    - 1.3.5 Bestimmung des Eingabezwecks (AA)
    - 2.4.1 Blöcke umgehen (A)
    - 2.4.4 Linkzweck (Im Kontext) (A)
    - 2.4.6 Überschriften und Beschriftungen (AA)
    - 3.2.3 Konsistente Navigation (A)
    - 3.2.4 Konsistente Identifikation (A)
    - 3.3.2 Beschriftungen oder Anweisungen (AA)
    - 3.3.3 Fehlervorschläge (AA)
    - 3.3.4 Fehlervermeidung (A))
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

Beispiel einer vom AI-Agenten entdeckten Barriere:
    
![AI-Agent Verletzung](https://github.com/user-attachments/assets/41884bf8-3ac2-4cb1-aa49-b7dc78bedb80)



------ ------ ------ ------ ------ ------ ------ ------



------------
axe devTools
------------


Die von den axe devTools geprüften rule-IDS
// Diese Liste von Rule IDs wird bei jeder Analyse verwendet.
const AXE_RULES_TO_CHECK = [
    //'aria-alt',           // Prüft, ob ARIA-Elemente einen zugänglichen Namen haben (ähnlich image-alt)
    'button-name',        // Buttons müssen einen zugänglichen Namen haben
    'document-title',     // Dokument muss einen <title> haben
    'input-button-name',  // Input-Buttons (type="submit", "reset", "button") müssen Namen haben
    'input-image-alt',    // Input-Elemente mit type="image" müssen einen Alt-Text haben
    'label',              // Formularfelder müssen Labels haben
    'link-name',          // Links müssen einen Namen haben
    'object-alt',         // <object>-Elemente müssen einen Alt-Text haben
    'role-img-alt',           // Elemente mit role="img" müssen einen Alt-Text haben
    'select-name',        // <select>-Elemente müssen einen zugänglichen Namen haben
    'svg-img-alt',        // Inline-SVGs, die ein Bild sind, müssen einen Alt-Text haben
    'autocomplete-valid', // autocomplete-Attribute müssen gültige Werte haben
    'empty-heading',      // Überschriften dürfen nicht leer sein
    'heading-order',      // Überschriften-Hierarchie muss korrekt sein
    'empty-table-header', // Tabellenköpfe dürfen nicht leer sein
    'image-redundant-alt' // Alt-Texte dürfen nicht redundant sein



Beispiel einer von den axe devTools entdeckten Barriere:

![axe devTools Verletzung ](https://github.com/user-attachments/assets/54c6fc7a-f645-44b0-bfb7-249c00f8b7a1)



------ ------ ------ ------ ------ ------ ------ ------



------------
Zuordnung der axe devTools rule-IDs zu Erfolgskriterien
------------


Area-alt = 2.4.4, 4.1.2
button-name = 4.1.2
Document-title = 2.4.2
image-alt = 1.1.1
input-button-name = 4.1.2
input-image-alt = 1.1.1, 4.1.2
label = 4.1.2, 3.3.2, 1.3.1
link-name = 2.4.4, 4.1.2
Object-alt = 1.1.1
role-img = 1.1.1
select-name = 4.1.2
svg-img-alt = 1.1.1
Autocomplete-valid = 1.3.5
Emtpy-heading = 1.3.1
Heading-order = 1.3.1, 2.4.6
Empty-table-header = 1.1.1
Image-redundant-alt = none


