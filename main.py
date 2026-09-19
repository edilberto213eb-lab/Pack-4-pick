import os, requests
from datetime import datetime

TG_TOKEN = os.getenv("TG_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
API_FOOTBALL_KEY = os.getenv("API_SPORTS_KEY")

def enviar(msg):
    requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
                  json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"})

texto = f"🔥 *PACK 5 DEPORTES - {datetime.now().strftime('%Y-%m-%d')}*\n\n"

# 1. FUTBOL (con tu clave)
try:
    hoy = datetime.now().strftime('%Y-%m-%d')
    url_fut = f"https://apiv3.apifootball.com/?action=get_events&from={hoy}&to={hoy}&APIkey={API_FOOTBALL_KEY}"
    r = requests.get(url_fut, timeout=15).json()
    if r and len(r) > 0:
        p = r[0]
        texto += f"⚽ FÚTBOL: {p['match_hometeam_name']} vs {p['match_awayteam_name']} - BTTS SI @1.85\n"
    else:
        texto += f"⚽ FÚTBOL: Flamengo vs Palmeiras - BTTS SI @1.85\n"
except:
    texto += f"⚽ FÚTBOL: Flamengo vs Palmeiras - BTTS SI @1.85\n"

# 2. OTROS DEPORTES CON ESPN (GRATIS, SIN CLAVE)
deportes = {
    "🏈 NFL": "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard",
    "🏀 NBA": "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard",
    "🏒 NHL": "https://site.api.espn.com/apis/site/v2/sports/hockey/nhl/scoreboard",
    "⚾ MLB": "https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard"
}

for nombre, url in deportes.items():
    try:
        data = requests.get(url, timeout=10).json()
        juego = data['events'][0] if data['events'] else None
        if juego:
            home = juego['competitions'][0]['competitors'][0]['team']['displayName']
            away = juego['competitions'][0]['competitors'][1]['team']['displayName']
            texto += f"{nombre}: {away} vs {home} - Over @1.90\n"
        else:
            texto += f"{nombre}: No hay juegos hoy - Over @1.90\n"
    except:
        texto += f"{nombre}: Juego destacado - Over @1.90\n"

enviar(texto)
print(texto)
