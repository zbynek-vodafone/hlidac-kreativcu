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
                print(f"Web vrátil kód {res.status_code}")
                break
                
            soup = BeautifulSoup(res.text, 'html.parser')
            
            # Najdeme VŠECHNY odkazy na webu a vyfiltrujeme ty, které vedou na profil umělce
            vsechny_odkazy = soup.find_all('a', href=True)
            odkazy_na_profily = []
            
            for o in vsechny_odkazy:
                href = o['href']
                # Hledáme odkazy, které v sobě mají typickou adresu profilu kreativce
                if "/kreativec/" in href or "/galerie-kreativcu/" in href or "creative" in str(o.get('class', '')):
                    if href not in odkazy_na_profily and not href.endswith('galerie-kreativcu'):
                        odkazy_na_profily.append(href)
            
            print(f"Na stránce {stranka} nalezeno {len(odkazy_na_profily)} potenciálních profilů.")
            
            # Pokud nic nenajdeme přes specifické filtry, zkusíme najít jakoukoli kartu
            if not odkazy_na_profily:
                profily_zaloha = soup.find_all('div', class_=re.compile("creative|item|card"))
                print(f"Záložní hledání našlo {len(profily_zaloha)} prvků.")
                break
                
            for odkaz in odkazy_na_profily:
                if not odkaz.startswith('http'):
                    odkaz = "https://www.kreativnicesko.cz" + odkaz
                
                # Zkusíme vytáhnout nějaké jméno, nebo použijeme text odkazu
                jmeno = "Kreativec"
                vsechny_profily.append({"jmeno": jmeno, "url": odkaz})
                
            time.sleep(2)
            stranka += 1
            if stranka > 2: # Pro rychlé ověření nám stačí projít 2 stránky
                break
        except Exception as e:
            print(f"Chyba: {e}")
            break
            
    # Odstraníme duplicity
    unikatni_profily = {p['url']: p for p in vsechny_profily}.values()
    print(f"=== KONEC: Celkem nalezeno {len(unikatni_profily)} unikátních profilů ===")
    return list(unikatni_profily)

def stahni_detaily_profilu(session, url_profilu):
    detaily = {"ico": "Nezadáno", "telefon": "Nezadáno", "email": "Nezadáno"}
    try:
        res = session.get(url_profilu, headers=HEADERS, timeout=10)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            
            # Hledání IČO
            for text in soup.stripped_strings:
                if "IČO" in text or "Ičo" in text:
                    # Zkusíme vzít text následující za ním
                    detaily["ico"] = text.replace("IČO:", "").replace("IČO", "").strip()
                    break
            
            # Hledání telefonu a mailu
            tel_tag = soup.find('a', href=re.compile(r'^tel:'))
            if tel_tag: detaily["telefon"] = tel_tag.text.strip()
            
            mail_tag = soup.find('a', href=re.compile(r'^mailto:'))
            if mail_tag: detaily["email"] = mail_tag.text.strip()
            
            # Pokus o získání skutečného jména z nadpisu stránky (h1)
            h1_tag = soup.find('h1')
            if h1_tag: detaily["jmeno"] = h1_tag.text.strip()
    except:
        pass
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
        print("Historii se nepodařilo načíst, jedeme od nuly.")

    aktualni_seznam = stahni_vsechny_kreativce()
    if not aktualni_seznam:
        print("Žádná data nebyla stažena.")
        return

    novi_kreativci = []
    for k in aktualni_seznam:
        if k["url"] not in stare_urls:
            print(f"Zpracovávám profil: {k['url']}")
            detaily = stahni_detaily_profilu(session, k["url"])
            novi_kreativci.append({
                "jmeno": detaily.get("jmeno", "Kreativec"),
                "url": k["url"],
                "ico": detaily["ico"],
                "telefon": detaily["telefon"],
                "email": detaily["email"]
            })
            time.sleep(1)

    if novi_kreativci:
        print(f"Odesílám {len(novi_kreativci)} profilů do Google Sheets...")
        try:
            odezva = session.post(WEBHOOK_URL, json={"novacci": novi_kreativci}, timeout=15)
            print(f"Výsledek zápisu: {odezva.text}")
        except Exception as e:
            print(f"Chyba odesílání: {e}")
    else:
        print("Žádná nová data k odeslání.")

if __name__ == "__main__":
    hlavni_funkce()
