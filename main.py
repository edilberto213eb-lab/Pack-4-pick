import os, requests, random, time
from datetime import datetime

TG_TOKEN = os.getenv("TG_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
API_KEY = os.getenv("API_SPORTS_KEY")

def cuota(tipo):
    rangos = {
        "btts": (1.68, 1.95),
        "mlb": (1.62, 1.85),
        "nfl": (1.87, 1.93),
        "nhl": (1.90, 2.10),
        "fija": (1.72, 1.86),
        "over": (1.85, 1.95)
    }
    a, b = rangos.get(tipo, (1.80, 1.95))
    return round(random.uniform(a, b), 2)

def tg(msg):
    try:
        requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
                      json={"chat_id": CHAT_ID, "text": msg}, timeout=15)
    except Exception as e:
        print(f"Error TG: {e}")

def get_espn_juegos(path):
    try:
        r = requests.get(f"https://site.api.espn.com/apis/site/v2/sports/{path}/scoreboard", timeout=10).json()
        eventos = r.get('events', [])
        lista = []
        for ev in eventos[:4]:
            comp = ev['competitions'][0]['competitors']
            # ESPN a veces invierte local/visita, agarramos team names completos
            home = next((c for c in comp if c['homeAway'] == 'home'), comp[0])
            away = next((c for c in comp if c['homeAway'] == 'away'), comp[1])
            lista.append(f"{away['team']['abbreviation']} vs {home['team']['abbreviation']}")
        return lista
    except:
        return []

def armar_mensaje():
    hoy = datetime.now().strftime('%d/%m')
    hoy_api = datetime.now().strftime('%Y-%m-%d')
    hora = datetime.now().strftime('%H:%M')

    # FUTBOL
    try:
        data = requests.get(f"https://apiv3.apifootball.com/?action=get_events&from={hoy_api}&to={hoy_api}&APIkey={API_KEY}", timeout=15).json()
        futbol = [f"{p['match_hometeam_name']} vs {p['match_awayteam_name']}" for p in data if p.get('match_hometeam_name')][:4]
    except:
        futbol = []

    if not futbol:
        futbol = ["Flamengo vs Palmeiras", "Boca Juniors vs River Plate", "Real Madrid vs Espanyol", "Libertad vs Cerro Porteno"]

    nfl = get_espn_juegos("football/nfl")
    mlb = get_espn_juegos("baseball/mlb")
    nhl = get_espn_juegos("hockey/nhl")
    # NBA en septiembre viene vacio, no lo usamos para no inventar

    print(f"FUT:{len(futbol)} NFL:{len(nfl)} MLB:{len(mlb)} NHL:{len(nhl)}")

    c_btts1 = cuota("btts")
    c_btts2 = cuota("btts")
    total_btts = round(c_btts1 * c_btts2, 2)

    # Mensaje
    msg = f"🔥 PACK 4 PICKS - {hoy} - CUOTA 3.0\n\n"

    # 1) MINI BTTS
    msg += f"1) MINI BTTS @{total_btts}\n"
    msg += f"- {futbol[0]} - BTTS SI @{c_btts1}\n"
    msg += f"- {futbol[1]} - BTTS SI @{c_btts2}\n\n"

    # 2) COMBI MIXTA - Solo con lo que hay HOY
    msg += f"2) COMBI MIXTA\n"
    if mlb and nfl:
        c1 = cuota("mlb")
        c2 = cuota("nfl")
        local_mlb = mlb[0].split(' vs ')[0]
        msg += f"- {mlb[0]} - Gana {local_mlb} @{c1}\n"
        msg += f"- {nfl[0]} - Over 45.5 @{c2} (Total {round(c1*c2,2)})\n\n"
    elif mlb:
        c1 = cuota("over")
        c2 = cuota("over")
        msg += f"- {mlb[0]} - Over 8.5 @{c1}\n"
        msg += f"- {(mlb[1] if len(mlb)>1 else futbol[2])} - Over 8.5 @{c2}\n\n"
    elif nfl:
        c1 = cuota("nfl")
        c2 = cuota("btts")
        msg += f"- {nfl[0]} - Over 45.5 @{c1}\n"
        msg += f"- {futbol[2]} - BTTS SI @{c2}\n\n"
    else:
        c1 = cuota("btts")
        c2 = cuota("over")
        msg += f"- {futbol[2]} - BTTS SI @{c1}\n"
        msg += f"- {futbol[3]} - Over 2.5 @{c2}\n\n"

    # 3) FIJA - YA DICE QUIEN GANA
    local_fija = futbol[2].split(' vs ')[0]
    c_fija = cuota("fija")
    msg += f"3) FIJA 1.80\n"
    msg += f"- {futbol
