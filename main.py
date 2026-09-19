import os, requests, random
from datetime import datetime, timedelta

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

def es_liga_valida(liga):
    l = liga.lower()
    # 1. BLOQUEO ABSOLUTO MEXICO MALA
    if "mexico" in l:
        # Solo pasa si es Liga MX o Expansion MX, y NO contiene palabras de 3ra
        if not ("liga mx" in l or "expansion" in l or "ligamx" in l):
            return False
        if any(x in l for x in ["serie b", "premier", "tdp", "segunda division", "tercera", "sub-"]):
            return False

    # 2. Basura general
    if any(x in l for x in ["u19","u20","u23","women","youth","reserve","academy","femenil","womens"]):
        return False

    # 3. WHITELIST - Solo estas 1ra y 2da TOP
    whitelist = [
        "premier league", "la lga", "serie a", "bundesliga", "ligue 1",
        "brasileirao", "liga profesional", "eredivisie", "primeira liga",
        "champions", "libertadores", "europa league", "mls", "liga pro", "liga mx", "expansion",
        # 2das buenas de tu foto
        "championship", "hypermotion", "laliga2", "2. bundesliga", "ligue 2",
        "eerste divisie", "segunda liga", "liga portugal 2", "challenger pro league",
        "1. lig", "2. liga", "super league 2", "primera nacional", "challenge league",
        "brasileiro b", "serie b de brasil", "obos-ligaen", "1. divisjon",
        "serie b" # italiana
    ]
    return any(w in l for w in whitelist)

hoy=datetime.now().strftime('%d/%m')
hoy_api=datetime.now().strftime('%Y-%m-%d')
hora=datetime.now().strftime('%H:%M')

futbol=[]
try:
    data=requests.get(f"https://apiv3.apifootball.com/?action=get_events&from={hoy_api}&to={hoy_api}&APIkey={API_KEY}",timeout=15).json()

    for p in data:
        # FILTRO 1: PARTIDOS YA JUGADOS - STATUS
        status = str(p.get('match_status','')).strip()
        live = str(p.get('match_live','')).lower()
        combo = f"{status} {live}".lower()

        # Si está terminado, en vivo, entretiempo, etc -> FUERA
        if any(x in combo for x in ['ft','finished','after','live','ht','1h','2h','et','pen','aet','award','cancel','postp']):
            continue
        # Solo aceptamos vacio, 0, NS, Not Started
        if status not in ['', '0', 'NS', 'Not Started', '-', 'Not Started '] and len(status) > 0:
            # Si el status no es uno de los buenos, lo bloqueamos
            if status.lower() not in ['ns','not started']:
                continue

        # FILTRO 2: LIGA
        liga = str(p.get('league_name',''))
        if not es_liga_valida(liga):
            continue

        # FILTRO 3: EQUIPOS BASURA POR NOMBRE
        home = p.get('match_hometeam_name','')
        away = p.get('match_awayteam_name','')
        nombre_completo = f"{home} {away}".lower()
        equipos_bloqueados = ['santiago','saltillo','guerreros del pacifico','acambaro','zaci','huracanes izcalli','celaya 2','irapuato ii','heroes']
        if any(e in nombre_completo for e in equipos_bloqueados):
            continue

        futbol.append(f"{home} vs {away}")
        if len(futbol)>=4:
            break

except Exception as e:
    print(f"Error api: {e}")

# Fallback si no hay 4 partidos buenos - solo TOP reales
if len(futbol) < 4:
    extras = ["Flamengo vs Palmeiras","Boca Juniors vs River Plate","Real Madrid vs Espanyol","Man City vs Arsenal","Bayern vs Dortmund"]
    for ex in extras:
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
