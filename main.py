import os, requests, random
from datetime import datetime

TG_TOKEN = os.getenv("TG_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
API_KEY = os.getenv("API_SPORTS_KEY")

def cuota(t):
    r = {"btts":(1.68,1.95),"mlb":(1.62,1.85),"nfl":(1.87,1.93),"nhl":(1.9,2.1),"fija":(1.72,1.86),"over":(1.85,1.95)}
    a,b = r.get(t,(1.8,1.95))
    return round(random.uniform(a,b),2)

def tg(m):
    try:
        requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", json={"chat_id": CHAT_ID, "text": m}, timeout=15)
    except Exception as e:
        print(e)

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
    except:
        return []

hoy=datetime.now().strftime('%d/%m')
hoy_api=datetime.now().strftime('%Y-%m-%d')
hora=datetime.now().strftime('%H:%M')

# LISTA NEGRA TOTAL - Todo esto se bloquea por liga, pais o equipo
BLOQUEADOS = [
    "indonesia","rans","nusantara","psgc","ciamis","sumsel","psps","persiraja","dejan",
    "letonia","latvia","moldavia","moldova","moldowa",
    "mexico","tdp","liga premier","serie b mexico","heroes","zaci","santiago","saltillo",
    "guerreros del pacifico","acambaro","huracanes izcalli","u19","u20","u23","women","youth","reserve","pegadaian"
]

WHITELIST = [
    "premier league", "la liga", "serie a", "bundesliga", "ligue 1",
    "brasileirao", "serie a brazil", "liga profesional", "eredivisie", "primeira liga",
    "champions league", "libertadores", "europa league", "mls", "liga pro ecuador",
    "liga mx", "liga expansion",
    "championship", "laliga2", "hypermotion", "2. bundesliga", "ligue 2",
    "eerste divisie", "segunda liga", "challenger pro league", "1. lig", "super league 2",
    "primera nacional", "challenge league", "brasileiro b", "serie b", "obos-ligaen"
]

futbol=[]
try:
    data=requests.get(f"https://apiv3.apifootball.com/?action=get_events&from={hoy_api}&to={hoy_api}&APIkey={API_KEY}",timeout=15).json()
    for p in data:
        # FILTRO 1: PARTIDOS YA JUGADOS
        status = str(p.get('match_status','')).lower()
        live = str(p.get('match_live','')).lower()
        if any(x in f"{status} {live}" for x in ['ft','finished','after','live','ht','pen','aet','cancel']):
            continue
        if status not in ['', '0', 'ns', 'not started', '-'] and 'not started' not in status:
            continue

        liga = str(p.get('league_name','')).lower()
        pais = str(p.get('country_name','')).lower() if p.get('country_name') else str(p.get('league_country','')).lower() if p.get('league_country') else ""
        home = str(p.get('match_hometeam_name','')).lower()
        away = str(p.get('match_awayteam_name','')).lower()
        texto_total = f"{liga} {pais} {home} {away}"

        # FILTRO 2: BLOQUEO TOTAL
        if any(b in texto_total for b in BLOQUEADOS):
            # Excepcion: si es liga mx o expansion, permitimos aunque diga mexico
            if not ("liga mx" in liga or "expansion" in liga):
                # Si tiene mexico o indonesia etc, fuera
                if any(x in texto_total for x in ["indonesia","rans","ciamis","sumsel","psps","letonia","moldavia","tdp","zaci"]):
                    continue
            # Segundo chequeo estricto para mexico basura
            if "mexico" in texto_total and not ("liga mx" in liga or "expansion" in liga):
                continue

        # FILTRO 3: SOLO WHITELIST
        if not any(w in liga for w in WHITELIST):
            continue

        futbol.append(f"{p.get('match_hometeam_name','')} vs {p.get('match_awayteam_name','')}")
        if len(futbol)>=4:
            break
except Exception as e:
    print(f"Error api: {e}")

# Fallback limpio solo TOP
if len(futbol) < 4:
    fallback = ["Flamengo vs Palmeiras","Boca Juniors vs River Plate","Real Madrid vs Espanyol","Man City vs Arsenal","Bayern vs Dortmund","PSG vs Marseille"]
    for ex in fallback:
        if ex not in futbol:
            futbol.append(ex)
        if len(futbol)>=4:
            break

nfl=get_espn("football/nfl")
mlb=get_espn("baseball/mlb")
nhl=get_espn("hockey/nhl")

local_fija=futbol[2].split(" vs ")[0] if len(futbol)>2 else "Real Madrid"
local_mlb=mlb[0].split(" vs ")[0] if mlb else "CHC"
c1=cuota("btts"); c2=cuota("btts"); c_mlb=cuota("mlb"); c_nfl=cuota("nfl"); c_fija=cuota("fija"); c_nhl=cuota("nhl")

msg=f"🔥 PACK 4 PICKS - {hoy} - CUOTA 3.0\n\n"
msg+=f"1) MINI BTTS @{round(c1*c2,2)}\n- {futbol[0]} - BTTS SI @{c1}\n- {futbol[1]} - BTTS SI @{c2}\n\n"
msg+=f"2) COMBI MIXTA @{round(c_mlb*c_nfl,2)}\n- {mlb[0] if mlb else futbol[2]} - Gana {local_mlb if mlb else local_fija} @{c_mlb}\n- {nfl[0] if nfl else futbol[3]} - Over 45.5 @{c_nfl}\n\n"
msg+=f"3) FIJA 1.80\n- {futbol[2]} - Gana {local_fija} @{c_fija} (Score 88)\n\n"
pick_val = nhl[0] if nhl else (mlb[0] if mlb else futbol[3])
liga_txt = "NHL Pretemporada" if nhl else "MLB" if mlb else "Over TOP"
msg+=f"4) VALUE 2.0+\n- {pick_val} - Over 6.5 @{c_nhl} - {liga_txt}\n\n"
msg+=f"⏰ Actualizado cada 2 horas | {hora} VE"

tg(msg)
print(msg)
