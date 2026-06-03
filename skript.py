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
                # Hledáme unikátní kód ID v adrese (UUID formát)
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
                
            time.sleep(1)
            stranka += 1
            if stranka > 45: # Projdeme kompletně celý web
                break
        except Exception as e:
            print(f"Chyba při skenování galerie: {e}")
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
            
            # 1. Jméno z H1
            h1_tag = soup.find('h1')
            if h1_tag:
                detaily["jmeno"] = h1_tag.text.strip()
            
            # 2. Bezpečné hledání IČO přes texty na stránce
            for element in soup.find_all(string=re.compile(r'IČO|Ičo')):
                text = element.strip()
                match = re.search(r'\d{6,10}', text)
                if match:
                    detaily["ico"] = match.group(0)
                    break
            
            # 3. Telefon
            for t in soup.find_all('a', href=re.compile(r'^tel:')):
                tel_text = t.text.strip()
                if tel_text and not tel_text.replace(" ", "").startswith('+4202'):
                    detaily["telefon"] = tel_text
                    break
            
            # 4. Email
            for m in soup.find_all('a', href=re.compile(r'^mailto:')):
                mail_text = m.text.strip()
                if mail_text and "mk.gov.cz" not in mail_text and "kreativnicesko" not in mail_text:
                    detaily["email"] = mail_text
                    break
    except Exception as e:
        print(f"Chyba detailu u {url_profilu}: {e} (profil přeskočen)")
    return detaily

def hlavni_funkce():
    session = requests.Session()
    stare_urls = []
    
    print("Ptám se Google tabulky na historii...")
    try:
        res_urls = session.post(WEBHOOK_URL, json={"akce": "get_urls"}, timeout=15)
        stare_urls = res_urls.json().get("urls", [])
        print(f"V Google tabulce je uloženo {len(stare_urls)} odkazů.")
    except:
        print("Historii se z tabulky nepodařilo načíst, jedeme od nuly.")

    aktualni_seznam = stahni_vsechny_kreativce()
    if not aktualni_seznam:
        print("Žádná data nebyla stažena.")
        return

    novi_kreativci = []
    for k in aktualni_seznam:
        if k["url"] not in stare_urls:
            try:
                print(f"Stahuji kontakt pro profil: {k['url']}")
                detaily = stahni_detaily_profilu(session, k["url"])
                novi_kreativci.append({
                    "jmeno": detaily["jmeno"],
                    "url": k["url"],
                    "ico": detaily["ico"],
                    "telefon": detaily["telefon"],
                    "email": detaily["email"]
                })
                time.sleep(0.5)
            except Exception as e:
                print(f"Chyba při zpracování profilu {k['url']}: {e}")
                continue

    if novi_kreativci:
        print(f"Odesílám {len(novi_kreativci)} nováčků do Google Sheets...")
        velikost_bloku = 20
        for i in range(0, len(novi_kreativci), velikost_bloku):
            blok = novi_kreativci
