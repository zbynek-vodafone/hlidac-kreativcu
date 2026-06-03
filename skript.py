import requests
from bs4 import BeautifulSoup
import json
import time
import re

WEBHOOK_URL = "https://script.google.com/macros/s/AKfycbwqPEgxOUJXZTvdgM01g9_nWYkKRCHCOnFLk9VMNTWZSTtcoPNCO0lTT2XJM68YUbFQkg/exec"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "cs-CZ,cs;q=0.9,en;q=0.8",
    "Connection": "keep-alive"
}

def stahni_vsechny_kreativce():
    vsechny_profily = []
    session = requests.Session()
    
    try:
        session.get("https://www.kreativnicesko.cz/", headers=HEADERS, timeout=15)
    except:
        pass

    stranka = 1
    print("=== START: Stahování dat z webu Kreativní Česko ===")
    
    while True:
        url_stranky = f"https://www.kreativnicesko.cz/cs/galerie-kreativcu?page={stranka}"
        print(f"Skenuji stránku {stranka}...")
        try:
            res = session.get(url_stranky, headers=HEADERS, timeout=15)
            if res.status_code != 200:
                print(f"Web vrátil status kód: {res.status_code}")
                break
                
            soup = BeautifulSoup(res.text, 'html.parser')
            vsechny_odkazy = soup.find_all('a', href=True)
            odkazy_na_profily = []
            
            for o in vsechny_odkazy:
                href = o['href']
                # Hledáme jakýkoliv odkaz, který v sobě má unikátní kód ID (formát UUID: 8-4-4-4-12 znaků)
                # Příklad: /cs/galerie-kreativcu/1dc0d808-457c-4e20-aaed-9eb9ae37957b
                if re.search(r'[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}', href):
                    if href not in odkazy_na_profily:
                        odkazy_na_profily.append(href)
            
            print(f"Na stránce {stranka} nalezeno podle ID filtru {len(odkazy_na_profily)} profilů.")
            
            if not odkazy_na_profily:
                print("Žádné další profily s ID kódem nenalezeny. Končím skenování webu.")
                break
                
            for odkaz in odkazy_na_profily:
                if not odkaz.startswith('http'):
                    odkaz = "https://www.kreativnicesko.cz" + odkaz
                vsechny_profily.append({"url": odkaz})
                
            time.sleep(1.5)
            stranka += 1
            if stranka > 45: # Projdeme kompletně celý web
                break
        except Exception as e:
            print(f"Chyba při skenování: {e}")
            break
            
    unikatni_profily = {p['url']: p for p in vsechny_profily}.values()
    print(f"=== KONEC: Celkem nalezeno {len(unikatni_profily)} unikátních profilů ===")
    return list(unikatni_profily)

def stahni_detaily_profilu(session, url_profilu):
    detaily = {"jmeno": "Nezadáno", "ico": "Nezadáno", "telefon": "Nezadáno", "email": "Nezadáno"}
    try:
        res = session.get(url_profilu, headers=HEADERS, timeout=10)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            
            # 1. Získání skutečného Jména kreativce z nadpisu h1
            h1_tag = soup.find('h1')
            if h1_tag:
                detaily["jmeno"] = h1_tag.text.strip()
            
            # 2. Získání IČO
            for text in soup.stripped_strings:
                if "IČO" in text or "Ičo" in text:
                    match = re.search(r'\d{6,10}', text) # Hledáme číslo o délce typického IČO
                    if match:
                        detaily["ico"] = match.group(0)
                        break
                    else:
                        rodic = soup.find(text=text)
                        if rodic and rodic.find_next():
                            match_sub = re.search(r'\d{6,10}', rodic.find_next().text)
                            if match_sub:
                                detaily["ico"] = match_sub.group(0)
                                break

            # 3. Získání TELEFONU (přeskakujeme pevné linky ministerstva začínající na +4202)
            tel_tags = soup.find_all('a', href=re.compile(r'^tel:'))
            for t in tel_tags:
                tel_text = t.text.strip()
                if tel_text and not tel_text.replace(" ", "").startswith('+4202'):
                    detaily["telefon"] = tel_text
                    break
            
            # 4. Získání EMAILU (přeskakujeme maily ministerstva a webu)
            mail_tags = soup.find_all('a', href=re.compile(r'^mailto:'))
            for m in mail_tags:
                mail_text = m.text.strip()
                if mail_text and "mk.gov.cz" not in mail_text and "kreativnicesko" not in mail_text:
                    detaily["email"] = mail_text
                    break
    except Exception as e:
        print(f"Chyba detailu u {url_profilu}: {e}")
    return detaily

def hlavni_funkce():
    session = requests.
