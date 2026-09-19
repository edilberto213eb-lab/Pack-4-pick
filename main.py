import os, requests
from datetime import datetime

TG_TOKEN = os.getenv("TG_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
API_KEY = os.getenv("API_SPORTS_KEY")

def enviar(msg):
    requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
                  json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown", "disable_web_page_preview": True})

texto = f"🔥 *PACK ELITE 5 DEPORTES - {datetime.now().strftime('%d/%m/%Y')}* 🔥\n"
texto += "━━━━━━━━━━━━━━━\n\n"

# 1. FUTBOL - TU API
try:
    hoy = datetime.now().strftime('%Y-%m-%d')
    url = f"https://apiv3.apifootball.com/?action=get_events&from={hoy}&to={hoy}&APIkey={API_KEY}"
    r = requests.get(url, timeout=15).json()
    if r and len(r) > 0:
        for p in r[:2]:
            texto += f"⚽ *FÚTBOL | {p['league_name']}*\n"
            texto += f"{p['match_hometeam_name']} vs {p['match_awayteam_name']}\n"
            texto += f"🕒 {p['match_time']}h | 👉 *BTTS SI @1.85*\n"
            texto += f"_Ambos anotan, ligas con muchos goles_\n\n"
except Exception as e:
    print(e)

# 2. OTROS DEPORTES - ESPN GRATIS
espn = {
    "🏈 NFL": ("football/nfl", "Over 45.5 Puntos @1.90", "Ataques explosivos"),
    "🏀 NBA": ("basketball/nba", "Over 220.5 Puntos @1.90", "Ritmo alto, defensas sueltas"),
    "🏒 NHL": ("hockey/nhl", "Over 5.5 Goles @1.85", "Porterías débiles"),
    "⚾ MLB": ("baseball/mlb", "Over 8.5 Carreras @1.90", "Bullpen cansado")
}

for nombre, (liga, pick, analisis) in espn.items():
    try:
        url = f"https://site.api.espn.com/apis/site/v2/sports/{liga}/scoreboard"
        data = requests.get(url, timeout=10).json()
        if data['events']:
            comp = data['events'][0]['competitions'][0]
            home = comp['competitors'][0]['team']['abbreviation']
            away = comp['competitors'][1]['team']['abbreviation']
            texto += f"{nombre} | {away} @ {home}\n"
            texto += f"👉 *{pick}*\n"
            texto += f"_{analisis}_\n\n"
    except:
        continue

texto += "━━━━━━━━━━━━━━━\n"
texto += "✅ Cuota total ~ @10.50 | Stake 1U"

enviar(texto)
print(texto)
