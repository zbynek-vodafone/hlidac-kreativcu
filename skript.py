import requests
from bs4 import BeautifulSoup
import json
import os
import time

# Tvůj vygenerovaný odkaz do Google Sheets
WEBHOOK_URL = "https://script.google.com/macros/s/AKfycbwfdf_2DB1GdVwPwWt5-a32AtAVruBmnlkYAuT2jvrCqKth4XeUn3FtYfOkBHvGrOWl2Q/exec"

# Maskování za reálný prohlížeč, aby nás web neblokoval
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "cs,en-US;q=0.7,en;q=0.3"
}

DATA_FILE = "stary_seznam.json"

def stahni_vsechny_kreativce():
    vsechny_profily = []
    stranka = 1
    
    print("Spouštím stahování dat z webu Kreativní Česko...")
    
    while True:
        # Web používá parametr ?page=1, ?page=2 atd.
        url_stranky = f"https://www.kreativnicesko.cz/cs/galerie-kreativcu?page={stranka}"
        print(f"Skenuji stránku {stranka}...")
        
        try:
            res = requests.get(url_stranky, headers=HEADERS, timeout=15)
            if res.status_code != 200:
                print(f"Konec stránkování nebo chyba přístupu (Status: {res.status_code})")
                break
                
            soup = BeautifulSoup(res.text, 'html.parser')
            
            # Hledáme hlavní kontejnery jednotlivých kreativců
            # Třída 'c-gallery-grid__item' odpovídá struktuře webu pro jednotlivé karty
            profily = soup.find_all('div', class_='c-gallery-grid__item')
            
            # Pokud na stránce nic není, ukončíme cyklus
            if not profily:
                print("Na této stránce již nejsou žádné profily. Končím skenování.")
                break
                
            for profil in profily:
                try:
                    # Hledání jména a odkazu
                    odkaz_tag = profil.find('a', class_='c-card-creative')
                    if not odkaz_tag:
                        continue
                        
                    jmeno = odkaz_tag.find('h3', class_='c-card-creative__title').text.strip()
                    odkaz = odkaz_tag['href']
                    if not odkaz.startswith('http'):
                        odkaz = "https://www.kreativnicesko.cz" + odkaz
                        
                    # Uložíme základní data. Detaily jako IČO, telefon a e-mail 
                    # vytáhneme v dalším kroku přímo z detailu profilu
                    vsechny_profily.append({
                        "jmeno": jmeno,
                        "url": odkaz
                    })
                except Exception as e:
                    print(f"Chyba při parsování karty na stránce {stranka}: {e}")
                    
            # Krátká pauza, abychom web nepřetížili a nechovali se agresivně
            time.sleep(1)
            stranka += 1
            
            # Pojistka proti nekonečnému cyklu (skenujeme max 30 stránek)
            if stranka > 30:
                break
                
        except Exception as e:
            print(f"Chyba sítě při stahování stránky {stranka}: {e}")
            break
            
    return vsechny_profily

def stahni_detaily_profilu(url_profilu):
    """Navštíví detail profilu a vytáhne IČO, telefon a e-mail"""
    detaily = {"ico": "Nezadáno", "telefon": "Nezadáno", "email": "Nezadáno"}
    try:
        res = requests.get(url_profilu, headers=HEADERS, timeout=10)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            
            # Vyhledání IČO podle textového štítku
            ico_label = soup.find(text=lambda t: t and "IČO" in t)
            if ico_label:
                # Najdeme hodnotu vedle nebo pod štítkem
                detaily["ico"] = ico_label.find_next().text.strip()
            
            # Vyhledání telefonu (odkaz začínající na tel:)
            tel_tag = soup.find('a', href=lambda href: href and href.startswith('tel:'))
            if tel_tag:
                detaily["telefon"] = tel_tag.text.strip()
                
            # Vyhledání e-mailu (odkaz začínající na mailto:)
            mail_tag = soup.find('a', href=lambda href: href and href.startswith('mailto:'))
            if mail_tag:
                detaily["email"] = mail_tag.text.strip()
    except Exception as e:
        print(f"Nepodařilo se stáhnout detaily pro {url_profilu}: {e}")
        
    return detaily

def hlavni_funkce():
    aktualni_seznam = stahni_vsechny_kreativce()
    if not aktualni_seznam:
        print("Nepodařilo se stáhnout žádná data z webu.")
        return

    # Načtení historie z minulého běhu
    stary_seznam = {}
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            stary_seznam = json.load(f)

    novi_kreativci = []
    
    # Porovnání: Je profil v našem starém seznamu?
    for k in aktualni_seznam:
        if k["url"] not in stary_seznam:
            print(f"Nalezen nový profil: {k['jmeno']}. Stahuji kontaktní údaje...")
            # Pokud je nový, jdeme na jeho profil pro IČO, mail a telefon
            detaily = stahni_detaily_profilu(k["url"])
            
            plny_profil = {
                "jmeno": k["jmeno"],
                "url": k["url"],
                "ico": detaily["ico"],
                "telefon": detaily["telefon"],
                "email": detaily["email"]
            }
            novi_kreativci.append(plny_profil)
            # Přidáme do databáze, abychom ho příště nehlásili jako nového
            stary_seznam[k["url"]] = k["jmeno"]

    # Pokud máme nováčky, pošleme je rovnou do Google Sheets
    if novi_kreativci:
        print(f"Celkem nalezeno {len(novi_kreativci)} nových kontaktů. Odesílám do Google Sheets...")
        poslat_do_google_sheets(novi_kreativci)
    else:
        print("Dnes nepřibyl žádný nový kreativec.")

    # Uložíme aktualizovanou databázi pro zítřejší kontrolu
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(stary_seznam, f, ensure_ascii=False, indent=4)

def poslat_do_google_sheets(data):
    try:
        res = requests.post(WEBHOOK_URL, json={"novacci": data}, timeout=15)
        print(f"Odezva z Google Sheets: {res.text}")
    except Exception as e:
        print(f"Chyba při odesílání do Google Sheets: {e}")

if __name__ == "__main__":
    hlavni_funkce()
