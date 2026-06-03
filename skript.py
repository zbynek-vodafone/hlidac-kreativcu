import requests
from bs4 import BeautifulSoup
import json
import time
import re

WEBHOOK_URL = "https://script.google.com/macros/s/AKfycbwqPEgxOUJXZTvdgM01g9_nWYkKRCHCOnFLk9VMNTWZSTtcoPNCO0lTT2XJM68YUbFQkg/exec"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "cs-CZ,cs;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Cache-Control": "max-age=0"
}

def stahni_vsechny_kreativce():
    vsechny_profily = []
    session = requests.Session()
    
    try:
        session.get("https://www.kreativnicesko.cz/", headers=HEADERS, timeout=15)
        time.sleep(2)
    except Exception as e:
        print(f"Varování při inicializaci session: {e}")

    stranka = 1
    print("=== START: Stahování dat z webu Kreativní Česko ===")
    
    while True:
        url_stranky = f"https://www.kreativnicesko.cz/cs/galerie-kreativcu?page={stranka}"
        print(f"Skenuji stránku {stranka}...")
        try:
            res = session.get(url_stranky, headers=HEADERS, timeout=15)
            if res.status_code != 200:
                print(f"Web vrátil kód {res.status_code}, končím skenování.")
                break
                
            soup = BeautifulSoup(res.text, 'html.parser')
            vsechny_odkazy = soup.find_all('a', href=True)
            odkazy_na_profily = []
            
            for o in vsechny_odkazy:
                href = o['href']
                if re.search(r'[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}', href):
                    if href not in odkazy_na_profily:
                        odkazy_na_profily.append(href)
            
            print(f"Na stránce {stranka} nalezeno {len(odkazy_na_profily)} profilů.")
            
            if not odkazy_na_profily:
                print("Žádné další profily s ID kódem nenalezeny.")
                break
                
            for odkaz in odkazy_na_profily:
                if not odkaz.startswith('http'):
                    odkaz = "https://www.kreativnicesko.cz" + odkaz
                vsechny_profily.append({"url": odkaz})
                
            time.sleep(2)
            stranka += 1
            if stranka > 3: # Test na první 3 stránky
                break
        except Exception as e:
            print(f"Chyba při skenování galerie: {e}")
            break
            
    unikatni_profily = {p['url']: p for p in vsechny_profily}.values()
    print(f"=== KONEC: Celkem načteno {len(unikatni_profily)} unikátních profilů ===")
    return list(unikatni_profily)

def stahni_detaily_profilu(session, url_profilu):
    detaily = {"jmeno": "Nezadáno", "ico": "Nezadáno", "telefon": "Nezadáno", "email": "Nezadáno"}
    try:
        res = session.get(url_profilu, headers=HEADERS, timeout=10)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            
            h1_tag = soup.find('h1')
            if h1_tag:
                jmeno_text = h1_tag.text.strip()
                if jmeno_text and "Detail" not in jmeno_text and "galerie" not in jmeno_text.lower():
                    detaily
