import requests
from bs4 import BeautifulSoup
import json
import time
import re

WEBHOOK_URL = "https://script.google.com/macros/s/AKfycbwqPEgxOUJXZTvdgM01g9_nWYkKRCHCOnFLk9VMNTWZSTtcoPNCO0lTT2XJM68YUbFQkg/exec"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "cs-CZ,cs;q=0.9"
}

def stahni_detaily_profilu(session, url_profilu):
    detaily = {"jmeno": "Nezadáno", "ico": "Nezadáno", "telefon": "Nezadáno", "email": "Nezadáno"}
    try:
        res = session.get(url_profilu, headers=HEADERS, timeout=10)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            
            h1_tag = soup.find('h1')
            if h1_tag:
                detaily["jmeno"] = h1_tag.text.strip()
            
            for element in soup.find_all(string=re.compile(r'IČO|Ičo')):
                text = element.strip()
                match = re.search(r'\d{6,10}', text)
                if match:
                    detaily["ico"] = match.group(0)
                    break
            
            for t in soup.find_all('a', href=re.compile(r'^tel:')):
                tel_text = t.text.strip()
                if tel_text and not tel_text.replace(" ", "").startswith('+4202'):
                    detaily["telefon"] = tel_text
                    break
            
            for m in soup.find_all('a', href=re.compile(r'^mailto:')):
                mail_text = m.text.strip()
                if mail_text and "mk.gov.cz" not in mail_text and "kreativnicesko" not in mail_text:
                    detaily["email"] = mail_text
                    break
    except Exception as e:
        print(f"Chyba u detailu {url_profilu}: {e}")
    return detaily

def hlavni_funkce():
    session = requests.Session()
    vsechny_odkazy = []
    
    print("=== KROK 1: Načítám hlavní stránku ===")
    url_stranky = "https://www.kreativnicesko.cz/cs/galerie-kreativcu?page=1"
    
    try:
        res = session.get(url_stranky, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # Najdeme všechny odkazy s ID kódem
        for o in soup.find_all('a', href=True):
            href = o['href']
            if re.search(r'[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}', href):
                plna_url = href if href.startswith('http') else "https://www.kreativnicesko.cz" + href
                if plna_url not in vsechny_odkazy:
                    vsechny_odkazy.append(plna_url)
    except Exception as e:
        print(f"Chyba načítání webu: {e}")
        return

    print(f"Nalezeno {len(vsechny_odkazy)} profilů ke zpracování.")
    if not vsechny_odkazy:
        print("Seznam odkazů je prázdný, končím.")
        return

    # Vezmeme pro rychlý test prvních 10 profilů
    test_odkazy = vsechny_odkazy[:10]
    novi_kreativci = []
    
    print("=== KROK 2: Stahuji detaily profilů ===")
    for url in test_odkazy:
        print(f"Skenuji: {url}")
        detaily = stahni_detaily_profilu(session, url)
        novi_kreativci.append({
            "jmeno": detaily["jmeno"],
            "url": url,
            "ico": detaily["ico"],
            "telefon": detaily["telefon"],
            "email": detaily["email"]
        })
        time.sleep(1)

    print(f"=== KROK 3: Odesílám {len(novi_kreativci)} lidí do Google Sheets ===")
    try:
        odezva = session.post(WEBHOOK_URL, json={"novacci": novi_kreativci}, timeout=15)
        print(f"Odezva z Google tabulky: {odezva.text}")
    except Exception as e:
        print(f"Chyba odesílání: {e}")

if __name__ == "__main__":
    hlavni_funkce()
