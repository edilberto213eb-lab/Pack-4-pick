import requests, os
from datetime import datetime

TG_TOKEN = os.getenv("TG_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
API_KEY = os.getenv("API_SPORTS_KEY")

def enviar(msg):
    if not TG_TOKEN or not CHAT_ID:
        print(msg)
        return
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"})

# --- SIMULACION DE HOY (mañana lo conectamos a API real) ---
# Esto ya cumple tu regla de cuota 2.8 a 4.0
pack_btts = [
    {"partido": "Man City vs Arsenal", "pick": "BTTS SI", "cuota": 1.72, "detalle": "City 7/7 marca, Arsenal 6/7"},
    {"partido": "Boca vs River", "pick": "BTTS SI", "cuota": 1.85, "detalle": "Ambos 6/7 marca"}
]
pack_mixta = [
    {"partido": "Lakers vs Warriors", "pick": "Over 228.5", "cuota": 1.90},
    {"partido": "Yankees vs Red Sox", "pick": "Yankees ML", "cuota": 1.80}
]
fija_18 = {"partido": "Real Madrid vs Barcelona", "pick": "Real Madrid Gana", "cuota": 1.82, "score": 88}
value = {"partido": "Inter Miami vs Orlando", "pick": "Messi Anota", "cuota": 2.20, "motivo": "Lesión defensa rival"}

def calcular_cuota(lista):
    total=1
    for x in lista: total*=x['cuota']
    return total

hoy = datetime.now().strftime('%d/%m')
cuota_btts = calcular_cuota(pack_btts)
cuota_mix = calcular_cuota(pack_mixta)

texto = f"""🔥 *PACK 4 PICKS - {hoy} - CUOTA 3.0*

*1) MINI BTTS @{cuota_btts:.2f}*
"""
for p in pack_btts:
    texto+=f"- {p['partido']} {p['pick']} @{p['cuota']} - {p['detalle']}\n"

texto+=f"""
*2) COMBI MIXTA @{cuota_mix:.2f}*
"""
for p in pack_mixta:
    texto+=f"- {p['partido']} {p['pick']} @{p['cuota']}\n"

texto+=f"""
*3) FIJA 1.80*
- {fija_18['partido']} {fija_18['pick']} @{fija_18['cuota']} (Score {fija_18['score']})

*4) VALUE 2.0+*
- {value['partido']} {value['pick']} @{value['cuota']} - {value['motivo']}
"""

enviar(texto)
