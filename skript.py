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
            
            # 1. Hledání Jména - zkusíme hlavní h1 nadpis, případně title stránky
            h1_tag = soup.find('h1')
            if h1_tag:
                # Očistíme případné obecné texty z nadpisu
                jmeno_text = h1_tag.text.strip()
                if jmeno_text and "Detail" not in jmeno_text and "galerie" not in jmeno_text.lower():
                    detaily["jmeno"] = jmeno_text
            
            # Pokud h1 selhalo nebo obsahuje obecný text, zkusíme najít meta tagy nebo název v záhlaví
            if detaily["jmeno"] == "Nezadáno":
                meta_title = soup.find('title')
                if meta_title:
                    detaily["jmeno"] = meta_title.text.split('|')[0].strip()

            # 2. Hledání IČO
            for element in soup.find_all(string=re.compile(r'IČO|Ičo|Identifikační')):
                text = element.strip()
                match = re.search(r'\d{6,10}', text)
                if match:
                    detaily["ico"] = match.group(0)
                    break

            # 3. Hledání Telefonu
            for t in soup.find_all('a', href=re.compile(r'^tel:')):
                tel_text = t.text.strip()
                href_text = t['href'].replace("tel:", "").strip()
                # Vezmeme text nebo číslo z odkazu, pokud to není ústředna ministerstva
                final_tel = tel_text if tel_text else href_text
                if final_tel and not final_tel.replace(" ", "").startswith('+420224'):
                    detaily["telefon"] = final_tel
                    break
            
            # 4. Hledání Emailu
            for m in soup.find_all('a', href=re.compile(r'^mailto:')):
                mail_text = m.text.strip()
                href_text = m['href'].replace("mailto:", "").strip()
                final_mail = mail_text if mail_text else href_text
                if final_mail and "mk.gov.cz" not in final_mail and "kreativnicesko" not in final_mail:
                    detaily["email"] = final_mail
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
        
        # Najdeme všechny odkazy vedoucí na karty profilů
        for o in soup.find_all('a', href=True):
            href = o['href']
            if "/galerie-kreativcu/" in href or re.search(r'[a-f0-9]{8}-[a-f0-9]{4}', href):
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

    # Vezmeme prvních 10 profilů pro ostrý test správnosti kontaktů
    test_odkazy = vsechny_odkazy[:10]
    novi_kreativci = []
    
    print("=== KROK 2: Stahuji detaily profilů ===")
    for url in test_odkazy:
        print(f"Skenuji: {url}")
        detaily = stahni_detaily_profilu(session, url)
        
        # Pojistka: Pokud by jméno stále bylo "Nezadáno", zkusíme ho vytáhnout z konce URL adresy
        if detaily["jmeno"] == "Nezadáno" or detaily["jmeno"] == "Detail kreativce":
            detaily["jmeno"] = "Kreativec (Ověřit na webu)"

        novi_kreativci.append({
            "jmeno": detaily["jmeno"],
            "url
