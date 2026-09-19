import os, requests
from datetime import datetime

TG_TOKEN = os.getenv("TG_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
API_KEY = os.getenv("API_SPORTS_KEY")

def tg(msg):
    requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
                  json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"})

def get_espn_juegos(path):
    try:
        r = requests.get(f"https://site.api.espn.com/apis/site/v2/sports/{path}/scoreboard", timeout=10).json()
        eventos = r.get('events', [])
        if not eventos:
            return [] # Si no hay juegos, devuelve vacio
        lista = []
        for ev in eventos[:3]:
            c = ev['competitions'][0]['competitors']
            home = c[0]['team']['abbreviation']
            away = c[1]['team']['abbreviation']
            lista.append(f"{away} vs {home}")
        return lista
    except:
        return []

hoy = datetime.now().strftime('%d/%m')
hoy_api = datetime.now().strftime('%Y-%m-%d')

# FUTBOL (siempre hay)
try:
    data = requests.get(f"https://apiv3.apifootball.com/?action=get_events&from={hoy_api}&to={hoy_api}&APIkey={API_KEY}", timeout=15).json()
    futbol = [f"{p['match_hometeam_name']} vs {p['match_awayteam_name']}" for p in data[:4]]
except:
    futbol = []

nfl = get_espn_juegos("football/nfl")
mlb = get_espn_juegos("baseball/mlb")
nhl = get_espn_juegos("hockey/nhl")
nba = get_espn_juegos("basketball/nba") # En septiembre viene vacio

# Log para ver que hay hoy
print(f"FUT: {len(futbol)} NFL:{len(nfl)} MLB:{len(mlb)} NHL:{len(nhl)} NBA:{len(nba)}")

msg = f"🔥 PACK 4 PICKS - {hoy} - CUOTA 3.0\n\n"

# 1. MINI BTTS (solo futbol)
if len(futbol) >= 2:
    msg += f"1) MINI BTTS @3.18\n"
    msg += f"- {futbol[0]} BTTS SI @1.72\n"
    msg += f"- {futbol[1]} BTTS SI @1.85\n\n"
else:
    msg += f"1) MINI BTTS @3.18\n- Flamengo vs Palmeiras BTTS SI @1.72\n- Boca vs River BTTS SI @1.85\n\n"

# 2. COMBI MIXTA - Solo con ligas que tengan juegos HOY
msg += "2) COMBI MIXTA @3.42\n"
if mlb and nfl:
    msg += f"- {mlb[0]} {mlb[0].split(' vs ')[0]} ML @1.8\n"
    msg += f"- {nfl[0]} Over 45.5 @1.9\n\n"
elif mlb:
    msg += f"- {mlb[0]} Over 8.5 @1.9\n"
    msg += f"- {mlb[1] if len(mlb)>1 else futbol[2]} Over 8.5 @1.8\n\n"
elif nfl:
    msg += f"- {nfl[0]} Over 45.5 @1.9\n"
    msg += f"- {futbol[2]} BTTS SI @1.8\n\n"
else:
    msg += f"- {futbol[2]} BTTS SI @1.9\n"
    msg += f"- {futbol[3] if len(futbol)>3 else 'Libertad vs Cerro'} Over 2.5 @1.8\n\n"

# 3 y 4
msg += f"3) FIJA 1.80\n- {futbol[2] if len(futbol)>2 else nfl[0] if nfl else 'Real Madrid vs Barcelona'} Local Gana @1.82\n\n"
msg += f"4) VALUE 2.0+\n- {mlb[0] if mlb else futbol[3] if len(futbol)>3 else 'Inter Miami vs Orlando'} Over @2.2 - Bullpen cansado\n"

tg(msg)
print(msg)
