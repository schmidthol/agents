// axe-scanner.js

const { chromium } = require('playwright'); // Importiere den Browser-Typ (chromium, firefox oder webkit)
const axe = require('axe-core');          // Importiere die axe-core Bibliothek

/**
 * Führt eine Barrierefreiheitsanalyse einer Webseite mit axe-core über Playwright aus.
 * @param {string} url - Die URL der zu untersuchenden Webseite.
 * @param {object} [axeOptions={}] - Optionen, die an axe.run() übergeben werden.
 * Z.B. { runOnly: { type: 'tag', values: ['wcag2a'] } }.
 * @param {string} [outputFileName=null] - Dateiname, unter dem der vollständige Bericht
 * im JSON-Format gespeichert werden soll.
 * @returns {Promise<object>} - Ein Promise, das ein Objekt mit den Analyseergebnissen zurückgibt.
 */
async function analyzeAccessibility(url, axeOptions = {}, outputFileName = null) {
    let browser;
    try {
        console.log(`\nStarte Barrierefreiheitsanalyse für: ${url}`);
        
        // Browser starten (headless: true ist Standard)
        // Setze headless: false, um den Browser während der Ausführung zu sehen (gut zum Debuggen)
        browser = await chromium.launch({ headless: true });
        const page = await browser.newPage();

        // Navigiere zur URL
        console.log(`Navigiere zu ${url}...`);
        await page.goto(url, { waitUntil: 'networkidle' }); // Warte, bis das Netzwerk inaktiv ist

        // --- WICHTIG: axe-core in den Browser-Kontext injizieren ---
        // Dies macht das globale 'axe'-Objekt im JavaScript-Kontext der Webseite verfügbar
        await page.addScriptTag({ path: require.resolve('axe-core/axe.min.js') });
        // require.resolve('axe-core/axe.min.js') findet den Pfad zur lokal installierten axe.min.js

        console.log('Führe axe-core Analyse aus...');
        // --- Führe axe-core innerhalb des Seitenkontextes aus ---
        // Der globale 'axe'-Objekt ist jetzt im JS-Kontext der Seite verfügbar
        const axeResults = await page.evaluate(async (options) => {
            // 'document' ist der HTML-Dokumentknoten der Seite
            return await axe.run(document, options);
        }, axeOptions); // Die 'axeOptions' werden vom Node.js-Kontext in den Browser-Kontext übergeben

        console.log(`Analyse abgeschlossen für ${url}.`);

        const results = {
            url: url,
            violations: axeResults.violations || [],
            passes: axeResults.passes || [],
            incomplete: axeResults.incomplete || [],
            inapplicable: axeResults.inapplicable || []
        };

        // --- Ergebnisse im Terminal anzeigen ---
        if (results.violations.length > 0) {
            console.log(`\n--- Gefundene WCAG-Verletzungen (${results.violations.length}) ---`);
            results.violations.forEach((violation, i) => {
                console.log(`\nVerletzung ${i + 1}:`);
                console.log(`  ID: ${violation.id}`);
                console.log(`  Beschreibung: ${violation.description}`);
                console.log(`  Hilfe: ${violation.help}`);
                console.log(`  Hilfe-URL: ${violation.helpUrl}`);
                console.log(`  Auswirkung: ${violation.impact}`);
                
                const nodesAffected = violation.nodes || [];
                console.log(`  Betroffene Elemente (${nodesAffected.length}):`);
                // Zeigt die HTML-Schnipsel der ersten paar betroffenen Elemente an
                nodesAffected.slice(0, Math.min(nodesAffected.length, 3)).forEach((node, j) => {
                    console.log(`    - HTML: ${node.html.substring(0, 100)}...`);
                    console.log(`      Selektor: ${node.target}`);
                });
            });
        } else {
            console.log('\nKeine WCAG-Verletzungen gefunden durch axe-core mit den gewählten Optionen.');
        }

        // --- Optional: Gesamten Bericht in JSON-Datei speichern ---
        if (outputFileName) {
            const fs = require('fs'); // Node.js 'fs' Modul für Dateisystemoperationen
            fs.writeFileSync(outputFileName, JSON.stringify(results, null, 4), 'utf-8');
            console.log(`\nVollständiger Bericht in '${outputFileName}' gespeichert.`);
        }

        return results;

    } catch (error) {
        console.error(`An error occurred during analysis for ${url}: ${error.message}`);
        return {}; // Im Fehlerfall leeres Objekt zurückgeben
    } finally {
        if (browser) {
            await browser.close(); // Sicherstellen, dass der Browser immer geschlossen wird
        }
    }
}

// --- Beispiel-Nutzung (Hauptausführung) ---
(async () => { // Async IIFE (Immediately Invoked Function Expression)
    const testUrl = "https://www.w3.org/WAI/demos/bad/before/home.html"; // Beispielseite mit bekannten Problemen

    // --- Option 1: Nur WCAG 2 Level A (deckt 1.3.1 Aspekte ab) ---
    console.log('\n--- TESTLAUF: Nur WCAG 2 Level A Regeln (einschließlich 1.3.1 Aspekte) ---');
    const optionsWcag2a = {
        runOnly: {
            type: 'tag',
            values: ['cat.semantics']
        }
    };
    await analyzeAccessibility(testUrl, optionsWcag2a, 'report_wcag2a_js.json');
/*
    // --- Option 2: Spezifische Regeln (z.B. Farbkontrast und Formular-Label) ---
    console.log('\n--- TESTLAUF: Nur spezifische Regeln (Farbkontrast, Formular-Label) ---');
    const optionsSpecificRules = {
        runOnly: {
            type: 'rule',
            values: ['color-contrast', 'label'] // 'label' ist eine Regel, die 1.3.1 tangiert
        }
    };
    await analyzeAccessibility(testUrl, optionsSpecificRules, 'report_specific_rules_js.json');

    // --- Option 3: Alle Standardregeln (ohne spezifische Filterung) ---
    // console.log('\n--- TESTLAUF: Alle Standardregeln ---');
    // await analyzeAccessibility(testUrl, {}, 'report_all_rules_js.json');
*/
    console.log("\nAlle Testläufe abgeschlossen.");
})();