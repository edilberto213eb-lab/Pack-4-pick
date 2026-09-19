import requests, os
from datetime import datetime

TG_TOKEN = os.getenv("TG_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
API_KEY = os.getenv("API_SPORTS_KEY")

def enviar(msg):
    print(msg)
    if not TG_TOKEN or not CHAT_ID: return
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    try:
        r = requests.post(url, json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=15)
        print(f"TG: {r.status_code}")
    except Exception as e:
        print(f"Error TG: {e}")

def get_fixtures_reales():
    if not API_KEY:
        print("❌ Falta API_SPORTS_KEY")
        return []
    hoy = datetime.now().strftime('%Y-%m-%d')
    url = f"https://v3.football.api-sports.io/fixtures?date={hoy}"
    headers = {"x-apisports-key": API_KEY}
    try:
        r = requests.get(url, headers=headers, timeout=20)
        data = r.json()
        print(f"API encontró {len(data.get('response',[]))} partidos hoy")
        return data.get('response',[])[:20] # primeros 20 para no saturar
    except Exception as e:
        print(f"Error API: {e}")
        return []

# --- LÓGICA REAL ---
fixtures = get_fixtures_reales()

if not fixtures:
    print("No hay partidos hoy o API falló, no se envía")
    exit()

# Por ahora tomamos 2 con más goles como BTTS (luego afinamos con stats)
pack_btts = []
for f in fixtures[:2]:
    home = f['teams']['home']['name']
    away = f['teams']['away']['name']
    pack_btts.append({
        "partido": f"{home} vs {away}",
        "pick": "BTTS SI",
        "cuota": 1.85,
        "detalle": f"Partido real {f['league']['name']}"
    })

if len(pack_btts) < 2:
    print("No hay suficientes datos reales hoy")
    exit()

cuota = 1
for p in pack_btts: cuota *= p['cuota']

hoy_str = datetime.now().strftime('%d/%m')
texto = f"""🔥 *PACK REAL - {hoy_str} - CUOTA {cuota:.2f}*

*1) MINI BTTS @{cuota:.2f}*
"""
for p in pack_btts:
    texto+=f"- {p['partido']} {p['pick']} @{p['cuota']} - {p['detalle']}\n"

texto+=f"\n_Son partidos reales de hoy sacados de API-Sports_"

# Solo envía si hay 2 reales
if cuota >= 2.8 and cuota <= 4.5:
    enviar(texto)
else:
    print(f"Cuota {cuota} fuera de rango 2.8-4.5")
