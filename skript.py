import requests
from bs4 import BeautifulSoup
import json
import time
import re

WEBHOOK_URL = "https://script.google.com/macros/s/AKfycbwqPEgxOUJXZTvdgM01g9_nWYkKRCHCOnFLk9VMNTWZSTtcoPNCO0lTT2XJM68YUbFQkg/exec"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "cs-CZ,cs;q=0.9"
}

def stahni_detaily_profilu(session, url_profilu):
    detaily = {"jmeno": "Nezadáno", "ico": "Nezadáno", "telefon": "Nezadáno", "email": "Nezadáno"}
    try:
        res = session.get(url_profilu, headers=HEADERS, timeout=10)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            
            # 1. Jméno (Ošetřeno proti chybám)
            try:
                h1_tag = soup.find('h1')
                if h1_tag:
                    jmeno_text = h1_tag.text.strip()
                    if jmeno_text and "Detail" not in jmeno_text and "galerie" not in jmeno_text.lower():
                        detaily["jmeno"] = jmeno_text
            except:
                pass
            
            # Záložní plán pro jméno z Title
            if detaily["jmeno"] == "Nezadáno":
                try:
                    meta_title = soup.find('title')
                    if meta_title and meta_title.text:
                        detaily["jmeno"] = meta_title.text.split('|')[0].strip()
                except:
                    pass

            # 2. IČO (Ošetřeno proti chybám)
            try:
                for element in soup.find_all(string=re.compile(r'IČO|Ičo|Identifikační')):
                    text = str(element).strip()
                    match = re.search(r'\d{6,10}', text)
                    if match:
                        detaily["ico"] = match.group(0)
                        break
            except:
                pass

            # 3. Telefon (Ošetřeno proti chybám)
            try:
                for t in soup.find_all('a', href=re.compile(r'^tel:')):
                    tel_text = t.text.strip()
                    if tel_text and not tel_text.replace(" ", "").startswith('+420224'):
                        detaily["telefon"] = tel_text
                        break
            except:
                pass
            
            # 4. Email (Ošetřeno proti chybám)
            try:
                for m in soup.find_all('a', href=re.compile(r'^mailto:')):
                    mail_text = m.text.strip()
                    if mail_text and "mk.gov.cz" not in mail_text and "kreativnicesko" not in mail_text:
                        detaily["email"] = mail_text
                        break
            except:
                pass
    except Exception as e:
        print(f"Chyba spojení u detailu {url_profilu}: {e}")
        
    return detaily

def hlavni_funkce():
    session = requests.Session()
    vsechny_odkazy = []
    
    print("=== KROK 1: Načítám hlavní stránku ===")
    url_stranky = "https://www.kreativnicesko.cz/cs/galerie-kreativcu?page=1"
    
    try:
        res = session.get(url_stranky, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        for o in soup.find_all('a', href=True):
            href = o['href']
            if "/cs/galerie-kreativcu/" in href or re.search(r'[a-f0-9]{8}-[a-f0-9]{4}', href):
                plna_url = href if href.startswith('http') else "https://www.kreativnicesko.cz" + href
                if plna_url not in vsechny_odkazy and not plna_url.endswith('galerie-kreativcu'):
                    vsechny_odkazy.append(plna_url)
    except Exception as e:
        print(f"Chyba načítání webu: {e}")
        return

    print(f"Nalezeno {len(vsechny_odkazy)} profilů ke zpracování.")
    if not vsechny_odkazy:
        print("Seznam odkazů je prázdný, končím.")
        return

    # Pro test vezmeme 10 profilů z první stránky
    test_odkazy = vsechny_odkazy[:10]
    novi_
