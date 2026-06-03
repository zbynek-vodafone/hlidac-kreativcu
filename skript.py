import requests
from bs4 import BeautifulSoup
import json
import time

WEBHOOK_URL = "https://script.google.com/macros/s/AKfycbwfdf_2DB1GdVwPwWt5-a32AtAVruBmnlkYAuT2jvrCqKth4XeUn3FtYfOkBHvGrOWl2Q/exec"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def nacti_stare_z_google():
    try:
        res = requests.get(WEBHOOK_URL, timeout=15)
        if res.status_code == 200:
            return set(res.json().get("urls", []))
    except Exception as e:
        print(f"Nepodařilo se nacíst historii z Google Sheets: {e}")
    return set()

def stahni_vsechny_kreativce():
    vsechny_profily = []
    stranka = 1
    print("Skenuji web Kreativní Česko...")
    
    while True:
        url_stranky = f"https://www.kreativnicesko.cz/cs/galerie-kreativcu?page={stranka}"
        try:
            res = requests.get(url_stranky, headers=HEADERS, timeout=15)
            if res.status_code != 200:
                break
                
            soup = BeautifulSoup(res.text, 'html.parser')
            profily = soup.find_all('div', class_='c-gallery-grid__item')
            
            if not profily:
                break
                
            for profil in profily:
                try:
                    odkaz_tag = profil.find('a', class_='c-card-creative')
                    if not odkaz_tag:
                        continue
                    jmeno = odkaz_tag.find('h3', class_='c-card-creative__title').text.strip()
                    odkaz = odkaz_tag['href']
                    if not odkaz.startswith('http'):
                        odkaz = "https://www.kreativnicesko.cz" + odkaz
                        
                    vsechny_profily.append({"jmeno": jmeno, "url": odkaz})
                except:
                    continue
            time.sleep(0.5)
            stranka += 1
            if stranka > 30: # Bezpečnostní limit stránek
                break
        except:
            break
            
    return vsechny_profily

def stahni_detaily_profilu(url_profilu):
    detaily = {"ico": "Nezadáno", "telefon": "Nezadáno", "email": "Nezadáno"}
    try:
        res = requests.get(url_profilu, headers=HEADERS, timeout=10)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            ico_label = soup.find(text=lambda t: t and "IČO" in t)
            if ico_label:
                detaily["ico"] = ico_label.find_next().text.strip()
            tel_tag = soup.find('a', href=lambda href: href and href.startswith('tel:'))
            if tel_tag:
                detaily["telefon"] = tel_tag.text.strip()
            mail_tag = soup.find('a', href=lambda href: href and href.startswith('mailto:'))
            if mail_tag:
                detaily["email"] = mail_tag.text.strip()
    except:
        pass
    return detaily

def hlavni_funkce():
    stare_url = nacti_stare_z_google()
    aktualni_seznam = stahni_vsechny_kreativce()
    
    if not aktualni_seznam:
        print("Žádná data z webu.")
        return

    novi_kreativci = []
    for k in aktualni_seznam:
        # Porovnáváme přímo proti odkazům staženým z tvé Google tabulky
        if k["url"] not in stare_url:
            print(f"Nový profil: {k['jmeno']}")
            detaily = stahni_detaily_profilu(k["url"])
            novi_kreativci.append({
                "jmeno": k["jmeno"],
                "url": k["url"],
                "ico": detaily["ico"],
                "telefon": detaily["telefon"],
                "email": detaily["email"]
            })

    if novi_kreativci:
        print(f"Odesílám {len(novi_kreativci)} kontaktů do Google Sheets...")
        try:
            requests.post(WEBHOOK_URL, json={"novacci": novi_kreativci}, timeout=15)
        except Exception as e:
            print(f"Chyba odesílání: {e}")
    else:
        print("Žádní noví kreativci.")

if __name__ == "__main__":
    hlavni_funkce()
