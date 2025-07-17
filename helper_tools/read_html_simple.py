import requests
from bs4 import BeautifulSoup

#Methode funktioniert nicht, da das Skript standardmäßig einen 
#generischen User-Agent (z.B. python-requests/2.X.X), der leicht als Bot identifiziert werden kann.

def read_html_from_url(url: str) -> str:
    """
    Liest den kompletten HTML-Code von einer gegebenen URL und entfernt Skript- und Style-Tags.
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'en-US,en;q=0.9,de-DE;q=0.8,de;q=0.7',
        'Referer': 'https://www.google.com/', # Manchmal hilft es, einen Referer zu setzen
        'DNT': '1', # Do Not Track Header
        'Upgrade-Insecure-Requests': '1'
    }
    try:
        response = requests.get(url, timeout=20)
        response.raise_for_status() # Löst einen HTTPError für schlechte Antworten (4xx oder 5xx) aus

        soup = BeautifulSoup(response.text, 'html.parser')

        # Skript- und Style-Tags entfernen, da sie oft nicht direkt für die semantische Analyse relevant sind
        for script in soup(["script", "style"]):
            script.extract()

        return str(soup)
    except requests.exceptions.RequestException as e:
        return f"Fehler beim Abrufen der URL: {e}"
    except Exception as e:
        return f"Ein unerwarteter Fehler ist aufgetreten: {e}"
    
print(read_html_from_url("http://www.zalando.de/pier-one-2-pack-hemd-blackwhite-pi922d0cs-q11.html"))