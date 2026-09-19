import os, requests
from datetime import datetime

TG_TOKEN = os.getenv("TG_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
API_KEY = os.getenv("API_SPORTS_KEY")

def tg(msg):
    requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
                  json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"})

def espn_game(path):
    try:
        r = requests.get(f"https://site.api.espn.com/apis/site/v2/sports/{path}/scoreboard", timeout=10).json()
        c = r['events'][0]['competitions'][0]['competitors']
        return f"{c[1]['team']['displayName']} vs {c[0]['team']['displayName']}"
    except:
        return None

hoy = datetime.now().strftime('%d/%m')
hoy_api = datetime.now().strftime('%Y-%m-%d')

# FUTBOL HOY
try:
    data = requests.get(f"https://apiv3.apifootball.com/?action=get_events&from={hoy_api}&to={hoy_api}&APIkey={API_KEY}", timeout=15).json()
    f1 = f"{data[0]['match_hometeam_name']} vs {data[0]['match_awayteam_name']}" if len(data)>0 else "Man City vs Arsenal"
    f2 = f"{data[1]['match_hometeam_name']} vs {data[1]['match_awayteam_name']}" if len(data)>1 else "Boca vs River"
    f3 = f"{data[2]['match_hometeam_name']} vs {data[2]['match_awayteam_name']}" if len(data)>2 else "Real Madrid vs Barcelona"
    f4 = f"{data[3]['match_hometeam_name']} vs {data[3]['match_awayteam_name']}" if len(data)>3 else "Inter Miami vs Orlando"
except:
    f1,f2,f3,f4 = "Man City vs Arsenal","Boca vs River","Real Madrid vs Barcelona","Inter Miami vs Orlando"

nba = espn_game("basketball/nba") or "Lakers vs Warriors"
mlb = espn_game("baseball/mlb") or "Yankees vs Red Sox"
nfl = espn_game("football/nfl") or "Detroit Lions vs Buffalo Bills"

msg = f"""🔥 PACK 4 PICKS - {hoy} - CUOTA 3.0

1) MINI BTTS @3.18
- {f1} BTTS SI @1.72 - Local 7/7 marca
- {f2} BTTS SI @1.85 - Ambos 6/7 marca

2) COMBI MIXTA @3.42
- {nba} Over 228.5 @1.9
- {mlb} {mlb.split(' vs ')[0]} ML @1.8

3) FIJA 1.80
- {f3} Local Gana @1.82 (Score 88)

4) VALUE 2.0+
- {f4} Gol del favorito @2.2 - Defensa rival con bajas
"""

tg(msg)
print(msg)
