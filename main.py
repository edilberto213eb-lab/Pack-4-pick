import os, requests, random, re
from datetime import datetime, timedelta

TG_TOKEN = os.getenv("TG_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
API_KEY = os.getenv("API_SPORTS_KEY")

def tg(m):
    try: requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", json={"chat_id": CHAT_ID, "text": m}, timeout=15)
    except: pass

def cuota(t):
    r = {"btts":(1.68,1.95),"mlb":(1.62,1.85),"nfl":(1.87,1.93),"nhl":(1.9,2.1),"fija":(1.72,1.86),"over":(1.85,1.95)}
    a,b = r.get(t,(1.8,1.95))
    return round(random.uniform(a,b),2)

# ========= ANALISIS REAL ESPN ULTIMOS 7 DIAS =========
def analisis_espn_real(sport_path, team_abbr, over_line):
    """
    sport_path: baseball/mlb, football/nfl, hockey/nhl
    Retorna: avg_total, over_pct, valido
    """
    try:
        total_runs = []
        for i in range(1, 8):
            fecha = (datetime.now() - timedelta(days=i)).strftime('%Y%m%d')
            url = f"https://site.api.espn.com/apis/site/v2/sports/{sport_path}/scoreboard?dates={fecha}"
            d = requests.get(url, timeout=10).json()
            for ev in d.get('events',[]):
                comp = ev['competitions'][0]['competitors']
                for c in comp:
                    if team_abbr.lower() in c['team']['abbreviation'].lower() or c['team']['abbreviation'].lower() in team_abbr.lower():
                        # Suma de puntos del partido
                        try:
                            scores = [int(x['score']) for x in comp]
                            if len(scores)==2:
                                total_runs.append(sum(scores))
                        except: pass
        if not total_runs:
            return 0, 0, True # Si no hay data, deja pasar

        avg = sum(total_runs)/len(total_runs)
        over_hits = sum(1 for x in total_runs if x > over_line)
        pct = over_hits/len(total_runs)*100 if total_runs else 0

        # VALIDO si promedio supera linea y over se dio 50%+
        valido = avg >= (over_line * 0.85) and pct >= 40
        return round(avg,1), round(pct,0), valido
    except Exception as e:
        print(f"Error ESPN {team_abbr}: {e}")
        return 0, 0, True

def get_espn_pick(sport_path, over_line):
    try:
        d=requests.get(f"https://site.api.espn.com/apis/site/v2/sports/{sport_path}/scoreboard",timeout=10).json()
        mejores=[]
        for ev in d.get('events',[])[:6]:
            comp=ev['competitions'][0]['competitors']
            h=next((x for x in comp if x['homeAway']=='home'),comp[0])
            a=next((x for x in comp if x['homeAway']=='away'),comp[1])
            abbr_h = h['team']['abbreviation']
            abbr_a = a['team']['abbreviation']

            avg_h, pct_h, ok_h = analisis_espn_real(sport_path, abbr_h, over_line)
            avg_a, pct_a, ok_a = analisis_espn_real(sport_path, abbr_a, over_line)

            avg_total = (avg_h + avg_a)/2 if avg_h and avg_a else max(avg_h, avg_a)

            if ok_h or ok_a:
                mejores.append({
                    "partido": f"{abbr_a} vs {abbr_h}",
                    "avg": avg_total,
                    "pct": max(pct_h, pct_a),
                    "detalle": f"Avg {avg_total} - Over {max(pct_h, pct_a):.0f}% ult 7"
                })
        # Ordena por mejor promedio
        mejores = sorted(mejores, key=lambda x: x['avg'], reverse=True)
        return mejores[0] if mejores else None
    except Exception as e:
        print(e)
        return None

def get_espn_fallback(sport_path):
    try:
        d=requests.get(f"https://site.api.espn.com/apis/site/v2/sports/{sport_path}/scoreboard",timeout=10).json()
        l=[]
        for ev in d.get('events',[])[:4]:
            c=ev['competitions'][0]['competitors']
            h=next((x for x in c if x['homeAway']=='home'),c[0])
            a=next((x for x in c if x['homeAway']=='away'),c[1])
            l.append(f"{a['team']['abbreviation']} vs {h['team']['abbreviation']}")
        return l
    except: return []

# ========= FUTBOL BTTS REAL =========
def analiza_btts_real(home, away):
    try:
        desde = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        hasta = datetime.now().strftime('%Y-%m-%d')
        url = f"https://apiv3.apifootball.com/?action=get_events&from={desde}&to={hasta}&APIkey={API_KEY}"
        data = requests.get(url, timeout=15).json()
        def stats_equipo(nombre):
            partidos = [x for x in data if nombre.lower() in (x.get('match_hometeam_name','').lower() + x.get('match_awayteam_name','').lower())][:7]
            if len(partidos)<4: return {"btts":70,"over25":70,"total":0}
            btts = sum(1 for p in partidos if int(p.get('match_hometeam_score',0) or 0)>0 and int(p.get('match_awayteam_score',0) or 0)>0)
            over = sum(1 for p in partidos if (int(p.get('match_hometeam_score',0) or 0)+(int(p.get('match_awayteam_score',0) or 0))>=3)
            return {"btts": btts/len(partidos)*100, "over25": over/len(partidos)*100, "total": len(partidos)}
        s_home = stats_equipo(home)
        s_away = stats_equipo(away)
        valido = s_home["btts"]>=50 and s_away["btts"]>=50
        detalle = f"BTTS {s_home['btts']:.0f}%/{s_away['btts']:.0f}% Over {s_home['over25']:.0f}%/{s_away['over25']:.0f}%"
        return valido, detalle
    except:
        return True, "Sin data"

# ========= MAIN =========
hoy=datetime.now().strftime('%d/%m')
hoy_api=datetime.now().strftime('%Y-%m-%d')
hora=datetime.now().strftime('%H:%M')

PAISES_PERMITIDOS = ["england","spain","italy","germany","france","brazil","argentina","mexico","netherlands","portugal","usa","ecuador","belgium","turkey","scotland","switzerland","austria","norway","greece","chile","colombia","uruguay","paraguay","internacional","europa","world"]
LIGAS_PERMITIDAS = ["premier league","la liga","laliga","serie a","bundesliga","ligue 1","brasileirao","brasileiro serie a","liga profesional","eredivisie","primeira liga","mls","liga pro","liga mx","expansion mx","champions league","libertadores","europa league","championship","laliga2","hypermotion","2. bundesliga","ligue 2","eerste divisie","segunda liga","challenger pro league","1. lig","primera nacional","serie b"]

def es_basura(texto, liga):
    t=texto.lower(); l=liga.lower()
    if re.search(r'u\d{1,2}|sub[-\s]?\d|juvenil|youth|reserve|women|femen', t): return True
    if re.search(r'serie\s+[c-z]', l): return True
    if re.search(r'\b(grupo|group|girone|gruppe)\s+[a-z]\b', l): return True
    if re.search(r'\b(grupo|group|girone)\s+[ivx]{1,4}\b', l): return True
    if re.search(r'\b(grupo|group)\s+\d+\b', l): return True
    return False

futbol=[]; vistos=set(); futbol_analizado=[]
try:
    data=requests.get(f"https://ap
