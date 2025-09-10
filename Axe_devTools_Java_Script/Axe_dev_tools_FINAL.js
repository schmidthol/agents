// axe-scanner-workflow.js
// Aufruf des Programms mit node axe-dev-tool.js 

const { chromium } = require('playwright');
const axe = require('axe-core');
const fs = require('fs'); // Für Dateisystemoperationen (JSON speichern)

// --- Konfiguration ---
// Ausgabe-Dateiname für den gesamten Bericht
const OUTPUT_REPORT_FILE = `results/wcag_workflow_report_${new Date().toISOString().replace(/:/g, '-')}.json`;

// Basis-URLs und Startseite für die Simulation
const BASE_URL = "https://www.otto.de";
const SEARCH_URL_TSHIRT = `${BASE_URL}/suche/t-shirt`; // Beispiel-Such-URL für T-Shirts

// --- SPEZIFISCHE AXE-CORE REGELN ZUR PRÜFUNG ---
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
];

// --- WICHTIG: SELEKTOREN ANPASSEN ---
// Diese Selektoren MÜSSEN Sie mit den Entwickler-Tools (F12) auf otto.de finden und anpassen.
// Otto.de verwendet dynamische Selektoren, diese können sich ändern!
const SELECTORS = {


    // 1. Suchergebnisseite
    "search_result_item_selector": 'article[data-id="S0O1G0UW"]', // Link zum ersten Produktbild/Artikel

    // 2. Produktdetailseite
    "size_selector": 'div.pl_selectiontile-text100.js_pdp_dimension-selection__scrollable-tile:has(input[value="XXL"])', 
    // Selektor für die XXL-Größenkachel
    "color_selector": 'img.pdp_dimension-selection__color-tile-image[alt="grau"]', // Selektor für den 'anthrazit'-Farb-Radio-Button
    "add_to_cart_button_selector": 'button.button--variant-primary[type="submit"]', // Button "In den Warenkorb"
    
    "pdp_continue_shopping_button_selector": 'oc-button-v1[data-qa="continueShopping"]',

    // 3. Warenkorb-Bestätigungsdialog (nach "In den Warenkorb" klicken)
    //oc-button-v1[data-qa="goToBasket"]:has-text("Zum Warenkorb")
    //oc-button-v1[data-qa="goToBasket"]
    //button[data-oc-floating-focus-v1-target="true"]:has-text("In den Warenkorb")
    "dialog_to_cart_button_selector": 'oc-button-v1[data-qa="goToBasket"]', // Button "Zum Warenkorb"
    
   
    // Hilfs-Selektoren für Wartestrategien
    "cart_page_url_substring": "/warenkorb" // Substring, der in der Warenkorb-URL vorkommen sollte
};

// --- Funktion zur WCAG-Analyse mit axe-core ---
// Diese Funktion ist analog zur analyzeAccessibility aus Ihrem ursprünglichen Skript
async function runAxeAnalysisOnPage(page, stepDescription) {
    console.log(`Führe axe-core Analyse aus für: ${stepDescription}...`);
    
    // Optionen für axe-core: Nur die spezifischen Regeln ausführen
    const axeOptions = {
        runOnly: {
            type: 'rule',
            values: AXE_RULES_TO_CHECK  //Config OPtions Dokumentation: https://github.com/dequelabs/axe-core/blob/master/doc/API.md
        }
    };

    // Führe axe-core innerhalb des Seitenkontextes aus
    // Der globale 'axe'-Objekt ist jetzt im JS-Kontext der Seite verfügbar
    const axeResults = await page.evaluate(async (options) => {
        // 'document' ist der HTML-Dokumentknoten der Seite
        // Die axe.min.js wurde bereits in die Seite injiziert (siehe unten)
        return await axe.run(document, options);
    }, axeOptions);

    return {
        violations: axeResults.violations || [],
        passes: axeResults.passes || [],            //Passes, incomplete, inapplicable icht unbedingt nötig, da nur violations geprüft werden sollen
        incomplete: axeResults.incomplete || [],
        inapplicable: axeResults.inapplicable || []
    };
}

// --- Haupt-Simulations-Workflow ---
async function runShoppingWorkflowAndAnalyze() {
    const allAnalysisResults = []; // Sammelt Ergebnisse für alle Seiten
    let browser;
    let page;    // <--- WICHTIG: Page-Variable hier initialisieren

    
    try {
        browser = await chromium.launch({ headless: false, slowMo: 50 }); // headless: true für Produktion
        const page = await browser.newPage();
        
        // --- Globale axe-core Injektion für alle Seiten ---
        // Dies muss nur einmal pro Page-Objekt gemacht werden.
        // Die axe.min.js muss auf jeder neuen Seite, zu der navigiert wird, injiziert werden,
        // da page.goto() den Seitenkontext zurücksetzt.
        const injectAxe = async () => {
            await page.addScriptTag({ path: require.resolve('axe-core/axe.min.js') });
            // console.log("axe-core injected.");
        };

        // --- SCHRITT 1: Suchergebnisseite ---
        console.log("\n--- SCHRITT 1: Suchergebnisseite ---");
        await page.goto(SEARCH_URL_TSHIRT, { waitUntil: "networkidle" });
        await injectAxe(); // Axe-core nach Navigation injizieren

        
        // --- ZUSÄTZLICHER SCHRITT: Cookie-Banner akzeptieren/schließen ---
        const cookieAcceptButtonSelector = '#onetrust-accept-btn-handler';
        console.log("Versuche, Cookie-Banner zu akzeptieren...");
        try {
            // Warte kurz, falls der Banner nicht sofort da ist
            await page.waitForSelector(cookieAcceptButtonSelector, { state: 'visible', timeout: 5000 });
            // Klicke den Button, um Cookies zu akzeptieren
            await page.locator(cookieAcceptButtonSelector).click();
            console.log("Cookie-Banner akzeptiert.");
            // Warte auf die Schließung des Banners und die Netzwerkruhe
            await page.waitForLoadState('networkidle', { timeout: 10000 });
            await page.waitForTimeout(500); // Zusätzliche kleine Pause
        } catch (cookieError) {
            console.log("Cookie-Banner nicht gefunden oder nicht geklickt (eventuell schon geschlossen oder nicht vorhanden): " + cookieError.message);
            // Dies ist in Ordnung, falls der Banner nicht immer erscheint oder bereits akzeptiert wurde.
        }
        // --- Ende des Cookie-Banner-Schritts ---


        let currentUrl = page.url();
        let currentHtml = await page.content();
        
        console.log(`Analysiere Suchergebnisseite: ${currentUrl}`);
        let axeAnalysis = await runAxeAnalysisOnPage(page, "Suchergebnisseite");
        allAnalysisResults.push({
            step: 1,
            description: "Suchergebnisseite",
            url: currentUrl,
            //html_snapshot: currentHtml, // Optional: Schnappschuss des HTML-Codes
            violations: axeAnalysis.violations
        });

        // Klicke auf den ersten Artikel in den Suchergebnissen
        if (SELECTORS.search_result_item_selector) {
            console.log(`Klicke auf den ersten Artikel (Selektor: ${SELECTORS.search_result_item_selector})...`);
            await page.waitForSelector(SELECTORS.search_result_item_selector, { timeout: 10000 });
            await page.locator(SELECTORS.search_result_item_selector).first().click();
            await page.waitForLoadState("networkidle"); // Warte auf Navigation
            
            // --- SCHRITT 2: Produktdetailseite ---
            await injectAxe(); // Axe-core nach erneuter Navigation injizieren

            currentUrl = page.url();
            currentHtml = await page.content();

            console.log(`\n--- SCHRITT 2: Produktdetailseite (nach Klick auf Artikel) ---`);
            console.log(`Analysiere Produktdetailseite: ${currentUrl}`);
            axeAnalysis = await runAxeAnalysisOnPage(page, "Produktdetailseite");
            allAnalysisResults.push({
                step: 2,
                description: "Produktdetailseite",
                url: currentUrl,
                //html_snapshot: currentHtml,
                violations: axeAnalysis.violations
            });

            // Farbe und Größe auswählen, Artikel in den Warenkorb legen
            console.log("Führe Interaktionen auf Produktdetailseite aus...");
            if (SELECTORS.size_selector) {
                console.log(`  Wähle Größe (Selektor: ${SELECTORS.size_selector})...`);
                await page.locator(SELECTORS.size_selector).click();
                await page.waitForTimeout(500); // Kurze Wartezeit für UI-Update
            }
            
            if (SELECTORS.color_selector) {
                console.log(`  Wähle Farbe (Selektor: ${SELECTORS.color_selector})...`);
                await page.locator(SELECTORS.color_selector).click();
                await page.waitForTimeout(500); // Kurze Wartezeit
            }
            
            if (SELECTORS.add_to_cart_button_selector) {
                console.log("  Klicke 'In den Warenkorb'...");
                const addToCartButton = page.locator(SELECTORS.add_to_cart_button_selector);
                await addToCartButton.waitFor({ state: "visible", timeout: 10000 });
                await addToCartButton.click();
                
                // Warte auf den Dialog
                console.log("  Warte auf Warenkorb-Bestätigungsdialog...");
                if (SELECTORS.dialog_to_cart_button_selector) {
                    await page.waitForSelector(SELECTORS.dialog_to_cart_button_selector, { state: "visible", timeout: 15000 });
                    console.log("   -> Warenkorb-Bestätigungsdialog erkannt.");
                    
                    //console.log("  Klicke 'Weiter einkaufen' (auf Produktdetailseite)...");
                    //const pdpContinueShoppingButton = page.locator(SELECTORS.pdp_continue_shopping_button_selector);
                   // await pdpContinueShoppingButton.waitFor({ state: "visible", timeout: 10000 });
                   // await pdpContinueShoppingButton.click();

                    //console.log("  Warte auf Seitenaktualisierung nach 'Weiter einkaufen' auf PDP...");
                    await page.waitForLoadState("networkidle"); 

                    // --- SCHRITT 3: Warenkorb-Seite ---
                    console.log("  Klicke 'Zum Warenkorb'...");
                    await page.locator(SELECTORS.dialog_to_cart_button_selector).click();
                    await page.waitForLoadState("networkidle"); // Warte auf Navigation
                    
                    await injectAxe(); // Axe-core nach erneuter Navigation injizieren

                    currentUrl = page.url();
                    currentHtml = await page.content();

                    console.log(`\n--- SCHRITT 3: Warenkorb-Seite ---`);
                    console.log(`Analysiere Warenkorbseite: ${currentUrl}`);
                    axeAnalysis = await runAxeAnalysisOnPage(page, "Warenkorbseite");
                    allAnalysisResults.push({
                        step: 3,
                        description: "Warenkorbseite",
                        url: currentUrl,
                        //html_snapshot: currentHtml,
                        violations: axeAnalysis.violations
                    });

                } else {
                    console.log("   -> Selektor für 'Zum Warenkorb'-Dialogbutton fehlt. Kann nicht zum Warenkorb navigieren.");
                }
            } else {
                console.log("  Selektor für 'In den Warenkorb'-Button fehlt. Überspringe Warenkorb-Interaktion.");
            }

        } else {
            console.log("Selektor für Suchergebnis-Artikel fehlt. Überspringe Produktdetailseite und Warenkorb.");
        }

    } catch (error) {
        console.error(`Ein schwerwiegender Fehler ist aufgetreten: ${error.message}`);
        if (page) await page.screenshot({ path: `error_workflow_${Date.now()}.png` });
    } finally {
        if (browser) {
            await browser.close();
        }
    }
    
    return allAnalysisResults;
}

// --- Hauptausführung ---
(async () => {
    console.log("--- Starte Shopping-Workflow und Analyse ---");
    const finalReport = await runShoppingWorkflowAndAnalyze();

    // Speichern des gesamten Berichts in eine JSON-Datei
    if (finalReport.length > 0) {
        fs.writeFileSync(OUTPUT_REPORT_FILE, JSON.stringify(finalReport, null, 4), 'utf-8');
        console.log(`\n--- Gesamter WCAG-Analysebericht für den Workflow in '${OUTPUT_REPORT_FILE}' gespeichert. ---`);
    } else {
        console.log("\n--- Workflow-Analyse konnte nicht erfolgreich abgeschlossen werden oder fand keine Ergebnisse. ---");
    }
    console.log("\nAlle Testläufe abgeschlossen.");
})();