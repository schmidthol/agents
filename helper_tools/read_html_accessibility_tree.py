

# tools/web_reader_tool.py
# Wichtig: Nutze jetzt die async_api
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

async def read_dynamic_html_from_url(url: str) -> str:
    """
    Liest den kompletten HTML-Code von einer dynamisch gerenderten URL (mit JS)
    unter Verwendung eines Headless-Browsers (Playwright Async API).
    """
    try:
        # 1. async_playwright() statt sync_playwright() und async with verwenden
        async with async_playwright() as p:
            # 2. 'await' vor allen Playwright-Methoden hinzufügen
            browser = await p.chromium.launch(headless=True) # Setze headless=False zum Debuggen
            page = await browser.new_page()

            # 3. 'await' auch hier
            # wait_until="networkidle" ist oft gut, um sicherzustellen, dass JS geladen ist
            await page.goto(url, wait_until="networkidle")
            
            # Manchmal muss man eine kurze Pause einlegen, damit alles rendert
            # await page.wait_for_timeout(2000) # Warte 2 Sekunden, optional, je nach Seite

            html_content = await page.content() # Auch hier 'await'

            soup = BeautifulSoup(html_content, 'html.parser')
            # Skript- und Style-Tags entfernen
            for script in soup(["script", "style"]):
                script.extract()

            return str(soup)
    except Exception as e:
        # Erfasse hier spezifischere Playwright-Fehler, falls nötig
        return f"Fehler beim Abrufen der URL mit Playwright: {e}"
    # 4. browser.close() sollte auch await haben und im finally Block sein
    finally:
        if 'browser' in locals() and browser: # Überprüfen, ob Browser-Objekt erstellt wurde
            await browser.close()

# WICHTIG: Du musst Playwright installieren und die Browser-Treiber herunterladen:
# pip install playwright
# playwright install


#print(read_dynamic_html_from_url("https://www.zalando.de/pier-one-2-pack-hemd-blackwhite-pi922d0cs-q11.html"))
#print(read_dynamic_html_from_url("https://www.otto.de/p/tom-tailor-denim-straight-jeans-barrel-mom-vintage-1-tlg-weiteres-detail-C1473510499/#variationId=1473510500"))