import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

#@tool
def read_dynamic_html_from_url(url: str) -> str:
     """
     Liest den kompletten HTML-Code von einer dynamisch gerenderten URL (mit JS).
     """
     chrome_options = Options()
     chrome_options.add_argument("--headless")  #Headless-Modus für Serverumgebungen
     chrome_options.add_argument("--no-sandbox")
     chrome_options.add_argument("--disable-dev-shm-usage")

     service = Service(ChromeDriverManager().install())
     driver = webdriver.Chrome(service=service, options=chrome_options)

     try:
         driver.get(url)
         html_content = driver.page_source
          #Hier könntest du auch BeautifulSoup verwenden, um den HTML-Code zu bereinigen
         return html_content
     finally:
         driver.quit()


print(read_dynamic_html_from_url("https://www.zalando.de/pier-one-2-pack-hemd-blackwhite-pi922d0cs-q11.html"))