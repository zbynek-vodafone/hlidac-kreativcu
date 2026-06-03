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
                break
                
            soup = BeautifulSoup(res.text, 'html.parser')
            vsechny_odkazy = soup.find_all('a', href=True)
            odkazy_na_profily = []
            
            for o in vsechny_odkazy:
                href = o['href']
                if "/cs/galerie-kreativcu/" in href and len(href.split('/')) > 4:
                    if href not in odkazy_na_profily:
                        odkazy_na_profily.append(href)
            
            if not odkazy_na_profily:
                print("Žádné další profily na této stránce.")
                break
                
            for odkaz in odkazy_na_profily:
                if not odkaz.startswith('http'):
                    odkaz = "https://www.kreativnicesko.cz" + odkaz
                vsechny_profily.append({"url": odkaz})
                
            time.sleep(1.5)
            stranka += 1
            if stranka > 45: # Pojistka pro projití celého webu
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
            
            # 1. Získání skutečného Jména kreativce
            h1_tag = soup.find('h1')
            if h1_tag:
                detaily["jmeno"] = h1_tag.text.strip()
            
            # 2. Získání IČO (hledáme čisté číslo za textem IČO)
            for text in soup.stripped_strings:
                if "IČO" in text or "Ičo" in text:
                    match = re.search(r'\d+', text)
                    if match:
                        detaily["ico"] = match.group(0)
                        break
                    else:
                        # Pokud je číslo v dalším elementu
                        rodic = soup.find(text=text)
                        if rodic:
                            sourozenec = rodic.find_next()
                            if sourozenec:
                                match_sub = re.search(r'\d+', sourozenec.text)
                                if match_sub:
                                    detaily["ico"] = match_sub.group(0)
                                    break

            # 3. Získání TELEFONU (přeskakujeme systémové odkazy)
            tel_tags = soup.find_all('a', href=re.compile(r'^tel:'))
            for t in tel_tags:
                tel_text = t.text.strip()
                if tel_text and not tel_text.startswith('+4202'): # Ignorujeme linky ministerstva
                    detaily["telefon"] = tel_text
                    break
            
            # 4. Získání EMAILU (přeskakujeme ministerstvo kultury)
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
            print(f"Stahuji kontakt pro profil: {k['url']}")
            detaily = stahni_detaily_profilu(session, k["url"])
            
            # Zapíšeme pouze pokud jsme našli alespoň reálné jméno
            novi_kreativci.append({
                "jmeno": detaily["jmeno"],
                "url": k["url"],
                "ico": detaily["ico"],
                "telefon": detaily["telefon"],
                "email": detaily["email"]
            })
            time.sleep(1)

    if novi_kreativci:
        print(f"Odesílám {len(novi_kreativci)} nováčků do Google Sheets...")
        # Rozdělíme odesílání po blocích (max 20 najednou), aby Google neshodil spojení pro timeout
        velikost_bloku = 20
        for i in range(0, len(novi_kreativci), velikost_bloku):
            blok = novi_kreativci[i:i+velikost_bloku]
            try:
                odezva = session.post(WEBHOOK_URL, json={"novacci": blok}, timeout=15)
                print(f"Blok {i//velikost_bloku + 1}: {odezva.text}")
            except Exception as e:
                print(f"Chyba odesílání bloku: {e}")
            time.sleep(1)
    else:
        print("Žádná nová data k odeslání.")

if __name__ == "__main__":
    hlavni_funkce()
