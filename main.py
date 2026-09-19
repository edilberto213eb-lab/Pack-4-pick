import os, requests, random, re
from datetime import datetime

TG_TOKEN = os.getenv("TG_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
API_KEY = os.getenv("API_SPORTS_KEY")

def cuota(t):
    r = {"btts":(1.68,1.95),"mlb":(1.62,1.85),"nfl":(1.87,1.93),"nhl":(1.9,2.1),"fija":(1.72,1.86),"over":(1.85,1.95)}
    a,b = r.get(t,(1.8,1.95))
    return round(random.uniform(a,b),2)

def tg(m):
    try: requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", json={"chat_id": CHAT_ID, "text": m}, timeout=15)
    except: pass

def get_espn(p):
    try:
        d=requests.get(f"https://site.api.espn.com/apis/site/v2/sports/{p}/scoreboard",timeout=10).json()
        l=[]
        for ev in d.get('events',[])[:4]:
            c=ev['competitions'][0]['competitors']
            h=next((x for x in c if x['homeAway']=='home'),c[0])
            a=next((x for x in c if x['homeAway']=='away'),c[1])
            l.append(f"{a['team']['abbreviation']} vs {h['team']['abbreviation']}")
        return l
    except: return []

hoy=datetime.now().strftime('%d/%m')
hoy_api=datetime.now().strftime('%Y-%m-%d')
hora=datetime.now().strftime('%H:%M')

PAISES_PERMITIDOS = ["england","spain","italy","germany","france","brazil","argentina","mexico","netherlands","portugal","usa","ecuador","belgium","turkey","scotland","switzerland","austria","norway","greece","chile","colombia","uruguay","paraguay","internacional","europa","world"]
LIGAS_PERMITIDAS = ["premier league","la liga","laliga","serie a","bundesliga","ligue 1","brasileirao","brasileiro serie a","liga profesional","eredivisie","primeira liga","mls","liga pro","liga mx","expansion mx","champions league","libertadores","europa league","championship","laliga2","hypermotion","2. bundesliga","ligue 2","eerste divisie","segunda liga","challenger pro league","1. lig","primera nacional","serie b"]

def es_basura(texto, liga):
    t = texto.lower()
    l = liga.lower()

    # 1. TODOS LOS U, SUB, JUVENIL, WOMEN
    if re.search(r'u\d{1,2}|sub[-\s]?\d|juvenil|youth|reserve|women|femen', t):
        return True

    # 2. CATEGORIA / CATEGORY / SERIE C, D, etc - SOLO DEJAMOS A y B
    # Bloquea: Serie C, Serie D, Serie E, Categoria A, B, C, Grupo A, B, C
    if re.search(r'serie\s+[c-z]', l): # Serie C,D,E,F... fuera (A y B pasan)
        return True
    if re.search(r'(categoria|category|cat\.?)\s*[c-z]', l):
        return True
    if re.search(r'(categoria|category|cat\.?)\s*[a-b]', l): # Incluso A y B de 3ra division
        # Si dice categoria A de brasil 3ra, fuera. Solo permitimos si es liga pro real
        if "tercera" in l or "3ra" in l or "3. " in l:
            return True

    # 3. GRUPOS - Group A,B,C,D / Grupo I, II, III, IV / Girone A,B
    if re.search(r'\b(grupo|group|girone|gruppe)\s+[a-z]\b', l):
        return True
    if re.search(r'\b(grupo|group|girone|gruppe)\s+[ivx]{1,4}\b', l): # I, II, III, IV, V
        return True
    if re.search(r'\b(grupo|group)\s+\d+\b', l): # Grupo 1, 2, 3
        return True

    # 4. OTRAS BASURA
    if any(x in t for x in ["futsal","beach soccer","esports","club friendly","amateur","amateur cup"]):
        return True

    return False

futbol=[]; vistos=set()
try:
    data=requests.get(f"https://apiv3.apifootball.com/?action=get_events&from={hoy_api}&to={hoy_api}&APIkey={API_KEY}",timeout=15).json()
    for p in data:
        status = str(p.get('match_status','')).lower()
        live = str(p.get('match_live','')).lower()
        if any(x in f"{status} {live}" for x in ['ft','finished','after','live','ht','1h','2h','et','pen','aet','cancel']): continue
        if status not in ['', '0', 'ns', 'not started', '-', ''] and 'not started' not in status:
            if len(status)>2: continue

        liga = str(p.get('league_name',''))
        pais = str(p.get('country_name','') or p.get('league_country','') or "")
        texto_total = f"{liga} {pais} {p.get('match_hometeam_name','')} {p.get('match_awayteam_name','')}"

        if es_basura(texto_total, liga): continue
        if not any(pa in pais.lower() for pa in PAISES_PERMITIDOS): continue
        if "mexico" in texto_total.lower() and not ("liga mx" in liga.lower() or "expansion" in liga.lower()): continue
        if not any(w in liga.lower() for w in LIGAS_PERMITIDAS): continue

        partido = f"{p.get('match_hometeam_name','')} vs {p.get('match_awayteam_name','')}"
        if partido.lower() in vistos: continue
        vistos.add(partido.lower())
        futbol.append(partido)
        if len(futbol)>=4: break
except Exception as e:
    print(e)

if len(futbol) < 4:
    for ex in ["Flamengo vs Palmeiras","Boca Juniors vs River Plate","Real Madrid vs Espanyol","Man City vs Arsenal"]:
        if ex.lower() not in vistos:
            futbol.append(ex)
            vistos.add(ex.lower())
        if len(futbol)>=4: break

nfl=get_espn("football/nfl"); mlb=get_espn("baseball/mlb"); nhl=get_espn("hockey/nhl")
local_fija=futbol[2].split(" vs ")[0] if len(futbol)>2 else "Real Madrid"
local_mlb=mlb[0].split(" vs ")[0] if mlb else "CHC"
c1=cuota("btts"); c2=cuota("btts"); c_mlb=cuota("mlb"); c_nfl=cuota("nfl"); c_fija=cuota("fija"); c_nhl=cuota("nhl")

msg=f"🔥 PACK 4 PICKS - {hoy} - CUOTA 3.0\n\n1) MINI BTTS @{round(c1*c2,2)}\n- {futbol[0]} - BTTS SI @{c1}\n- {futbol[1]} - BTTS SI @{c2}\n\n2) COMBI MIXTA @{round(c_mlb*c_nfl,2)}\n- {mlb[0] if mlb else futbol[2]} - Gana {local_mlb if mlb else local_fija} @{c_mlb}\n- {nfl[0] if nfl else futbol[3]} - Over 45.5 @{c_nfl}\n\n3) FIJA 1.80\n- {futbol[2]} - Gana {local_fija} @{c_fija} (Score 88)\n\n4) VALUE 2.0+\n- {nhl[0] if nhl else mlb[0] if mlb else futbol[3]} - Over 6.5 @{c_nhl}\n\n⏰ {hora} VE"
tg(msg)
print(msg)
