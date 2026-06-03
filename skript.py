import requests
from bs4 import BeautifulSoup
import json
import time

# Tvá aktuální ověřená adresa Google Web App
WEBHOOK_URL = "https://script.google.com/macros/s/AKfycbwqPEgxOUJXZTvdgM01g9_nWYkKRCHCOnFLk9VMNTWZSTtcoPNCO0lTT2XJM68YUbFQkg/exec"

# Silnější maskování robota, aby nás web neblokoval
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "cs-CZ,cs;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Cache-Control": "max-age=0"
}

def stahni_vsechny_kreativce():
    vsechny_profily = []
    session = requests.Session() # Použijeme session pro zachování cookies
    
    # Nejprve navštívíme hlavní stranu, abychom dostali cookies
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
                print(f"Web vrátil chybový kód {res.status_code}, končím.")
                break
                
            soup = BeautifulSoup(res.text, 'html.parser')
            
            # Hledáme karty kreativců podle jejich odkazu
            profily = soup.find_all('a', class_='c-card-creative')
            print(f"Na stránce {stranka} nalezeno {len(profily)} profilů.")
            
            if not profily:
                print("Žádné další profily nenalezeny nebo nás web zablokoval.")
                break
                
            for odkaz_tag in profily:
                try:
                    titulek_tag = odkaz_tag.find('h3', class_='c-card-creative__title')
                    if not titulek_tag:
                        continue
                    jmeno = titulek_tag.text.strip()
                    odkaz = odkaz_tag['href']
                    if not odkaz.startswith('http'):
                        odkaz = "https://www.kreativnicesko.cz" + odkaz
                    vsechny_profily.append({"jmeno": jmeno, "url": odkaz})
                except Exception as e:
                    print(f"Chyba karty: {e}")
                    continue
            time.sleep(2) # Bezpečné zpoždění mezi stránkami
            stranka += 1
            if stranka > 3: # Pro první test zkontrolujeme jen první 3 stránky dat
                break
        except Exception as e:
            print(f"Chyba sítě při stahování webu: {e}")
            break
            
    print(f"=== KONEC: Celkem načteno {len(vsechny_profily)} profilů ===")
    return vsechny_profily

def stahni_detaily_profilu(session, url_profilu):
    detaily = {"ico": "Nezadáno", "telefon": "Nezadáno", "email": "Nezadáno"}
    try:
        res = session.get(url_profilu, headers=HEADERS, timeout=10)
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
    session = requests.Session()
    stare_urls = []
    
    print("Ptám se Google tabulky na historii...")
    try:
        res_urls = session.post(WEBHOOK_URL, json={"akce": "get_urls"}, timeout=15)
        print(f"Odezva od Google na historii: {res_urls.text[:100]}")
        stare_urls = res_urls.json().get("urls", [])
        print(f"V Google tabulce je uloženo {len(stare_urls)} odkazů.")
    except Exception as e:
        print(f"Nepodařilo se načíst historii z Google Sheets: {e}")

    aktualni_seznam = stahni_vsechny_kreativce()
    if not aktualni_seznam:
        print("Žádná data z webu nebyla stažena. Končím.")
        return

    novi_kreativci = []
    for k in aktualni_seznam:
        if k["url"] not in stare_urls:
            print(f"Nový profil: {k['jmeno']}. Stahuji kontakt...")
            detaily = stahni_detaily_profilu(session, k["url"])
            novi_kreativci.append({
                "jmeno": k["jmeno"],
                "url": k["url"],
                "ico": detaily["ico"],
                "telefon": detaily["telefon"],
                "email": detaily["email"]
            })
            time.sleep(1) # Krátká pauza mezi profily, abychom web nepřetížili

    if novi_kreativci:
        print(f"Odesílám {len(novi_kreativci)} nováčků do Google Sheets...")
        try:
            odezva = session.post(WEBHOOK_URL, json={"novacci": novi_kreativci}, timeout=15)
            print(f"Výsledek zápisu: {odezva.text}")
        except Exception as e:
            print(f"Chyba odesílání: {e}")
    else:
        print("Dnes žádní noví kreativci k odeslání.")

if __name__ == "__main__":
    hlavni_funkce()
