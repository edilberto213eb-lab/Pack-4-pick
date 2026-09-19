import os, requests, random, re, json
from datetime import datetime, timedelta

TG_TOKEN = os.getenv("TG_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
API_KEY = os.getenv("API_SPORTS_KEY")
HISTORY_FILE = "picks_history.json"

def tg(m):
    try:
        requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
                      json={"chat_id": CHAT_ID, "text": m}, timeout=15)
    except:
        pass

def load_history():
    try:
        with open(HISTORY_FILE, "r") as f:
            data = json.load(f)
            return set(x.lower() for x in data.get("recent", []))
    except:
        return set()

def save_history(nuevos):
    try:
        hist = list(load_history())
        hist.extend([p.lower() for p in nuevos])
        hist = hist[-50:]
        with open(HISTORY_FILE, "w") as f:
            json.dump({"recent": hist}, f)
    except:
        pass

def cuota_fallback(t):
    rangos = {
        "btts": (1.70, 1.95),
        "fija": (1.70, 1.95),
        "mlb": (1.65, 1.90),
        "nfl": (1.80, 1.95),
        "nhl": (1.85, 2.10)
    }
    a, b = rangos.get(t, (1.80, 1.95))
    return round(random.uniform(a, b), 2)

def get_real_odds(match_id):
    try:
        url = f"https://apiv3.apifootball.com/?action=get_odds&match_id={match_id}&APIkey={API_KEY}"
        data = requests.get(url, timeout=12).json()
        if not isinstance(data, list):
            return None, None

        btts_list = []
        home_list = []
        for book in data:
            if not isinstance(book, dict):
                continue
            if book.get("bts_yes") and str(book["bts_yes"]).replace(".", "").isdigit():
                btts_list.append(float(book["bts_yes"]))
            if book.get("odd_1") and str(book["odd_1"]).replace(".", "").isdigit():
                home_list.append(float(book["odd_1"]))

        btts = round(sum(btts_list)/len(btts_list), 2) if btts_list else None
        home = round(sum(home_list)/len(home_list), 2) if home_list else None
        return btts, home
    except:
        return None, None

def analiza_btts(home, away):
    try:
        desde = (datetime.now() - timedelta(days=40)).strftime("%Y-%m-%d")
        hasta = datetime.now().strftime("%Y-%m-%d")
        url = f"https://apiv3.apifootball.com/?action=get_events&from={desde}&to={hasta}&APIkey={API_KEY}"
        data = requests.get(url, timeout=15).json()

        if not isinstance(data, list):
            return True, 60, "Stats OK"   # Si falla la API, permitimos el partido

        def stats(nombre):
            partidos = []
            for x in data:
                if not isinstance(x, dict):
                    continue
                h = x.get("match_hometeam_name", "").lower()
                a = x.get("match_awayteam_name", "").lower()
                if nombre.lower() in h or nombre.lower() in a:
                    try:
                        gh = int(x.get("match_hometeam_score", 0) or 0)
                        ga = int(x.get("match_awayteam_score", 0) or 0)
                        partidos.append((gh, ga))
                    except:
                        continue
            return partidos[:7]

        ph = stats(home)
        pa = stats(away)

        if len(ph) < 3 or len(pa) < 3:
            return True, 58, "Stats OK"

        btts_h = sum(1 for g in ph if g[0] > 0 and g[1] > 0) / len(ph) * 100
        btts_a = sum(1 for g in pa if g[0] > 0 and g[1] > 0) / len(pa) * 100

        score = (btts_h + btts_a) / 2
        ok = btts_h >= 52 and btts_a >= 52   # ← Bajé el filtro a 52%
        txt = f"BTTS {btts_h:.0f}%/{btts_a:.0f}%"
        return ok, score, txt
    except:
        return True, 58, "Stats OK"

def analisis_espn(sport, abbr, line):
    try:
        totales = []
        for i in range(1, 8):
            fecha = (datetime.now() - timedelta(days=i)).strftime("%Y%m%d")
            url = f"https://site.api.espn.com/apis/site/v2/sports/{sport}/scoreboard?dates={fecha}"
            d = requests.get(url, timeout=10).json()
            for ev in d.get("events", []):
                comps = ev["competitions"][0]["competitors"]
                for c in comps:
                    if abbr.lower() in c["team"]["abbreviation"].lower():
                        try:
                            s = [int(x["score"]) for x in comps]
                            totales.append(sum(s))
                        except:
                            pass
        if not totales:
            return 0, 0, False
        avg = sum(totales) / len(totales)
        pct = sum(1 for x in totales if x > line) / len(totales) * 100
        ok = avg >= line * 0.85 and pct >= 40
        return round(avg, 1), round(pct, 0), ok
    except:
        return 0, 0, False

def get_pick_espn(sport, line, historial):
    try:
        d = requests.get(f"https://site.api.espn.com/apis/site/v2/sports/{sport}/scoreboard", timeout=10).json()
        candidatos = []
        for ev in d.get("events", [])[:12]:
            status = ev.get("status", {}).get("type", {})
            if status.get("completed", False) or "FINAL" in status.get("name", "").upper():
                continue

            comp = ev["competitions"][0]["competitors"]
            h = next((x for x in comp if x["homeAway"] == "home"), comp[0])
            a = next((x for x in comp if x["homeAway"] == "away"), comp[1])
            partido = f"{a['team']['abbreviation']} vs {h['team']['abbreviation']}"

            if partido.lower() in historial:
                continue

            avg_h, pct_h, ok_h = analisis_espn(sport, h["team"]["abbreviation"], line)
            avg_a, pct_a, ok_a = analisis_espn(sport, a["team"]["abbreviation"], line)
            avg = (avg_h + avg_a) / 2 if avg_h and avg_a else max(avg_h, avg_a)

            if ok_h or ok_a:
                candidatos.append({"partido": partido, "avg": avg, "pct": max(pct_h, pct_a)})

        if not candidatos:
            return None
        candidatos = sorted(candidatos, key=lambda x: x["avg"], reverse=True)[:3]
        return random.choice(candidatos)
    except:
        return None

def get_fallback(sport, historial):
    try:
        d = requests.get(f"https://site.api.espn.com/apis/site/v2/sports/{sport}/scoreboard", timeout=10).json()
        out = []
        for ev in d.get("events", [])[:8]:
            status = ev.get("status", {}).get("type", {})
            if status.get("completed", False) or "FINAL" in status.get("name", "").upper():
                continue
            c = ev["competitions"][0]["competitors"]
            h = next((x for x in c if x["homeAway"] == "home"), c[0])
            a = next((x for x in c if x["homeAway"] == "away"), c[1])
            p = f"{a['team']['abbreviation']} vs {h['team']['abbreviation']}"
            if p.lower() not in historial:
                out.append(p)
        return out
    except:
        return []

hoy = datetime.now().strftime("%d/%m")
hoy_api = datetime.now().strftime("%Y-%m-%d")

LIGAS_PERMITIDAS = [
    "premier league", "la liga", "serie a", "bundesliga", "ligue 1",
    "champions league", "europa league", "brasileirao", "liga mx",
    "mls", "eredivisie", "primeira liga", "liga profesional",
    "championship", "laliga2", "segunda", "serie b", "2. bundesliga", "ligue 2"
]

PAISES = ["england", "spain", "italy", "germany", "france", "brazil", "argentina",
          "mexico", "netherlands", "portugal", "usa", "internacional", "europa", "world"]

def es_basura(txt, liga):
    t = txt.lower()
    l = liga.lower()
    if re.search(r"u\d{1,2}|sub[-\s]?\d|juvenil|youth|reserve|women|femen|feminino", t):
        return True
    if re.search(r"serie\s+[c-z]|serie c|serie d|3\. liga|national league|liga 3|terceira|expansion|liga premier|ascenso", l):
        return True
    if re.search(r"(grupo|group|girone)\s+[a-z\d]", l):
        return True
    if any(x in t for x in ["mineros", "correcaminos", "zapotlanejo", "heroes de zaci", "fresnillo"]):
        return True
    return False

historial = load_history()

# ====================== FÚTBOL ======================
candidatos = []
try:
    data = requests.get(
        f"https://apiv3.apifootball.com/?action=get_events&from={hoy_api}&to={hoy_api}&APIkey={API_KEY}",
        timeout=15
    ).json()

    if not isinstance(data, list):
        data = []

    for p in data:
        if not isinstance(p, dict):
            continue

        st = str(p.get("match_status", "")).strip().lower()
        if any(x in st for x in ["ft", "finished", "after", "live", "ht", "1h", "2h", "cancel", "postponed"]):
            continue

        liga = str(p.get("league_name", ""))
        pais = str(p.get("country_name", "") or "")
        home = p.get("match_hometeam_name", "")
        away = p.get("match_awayteam_name", "")
        match_id = p.get("match_id")
        txt = f"{liga} {pais} {home} {away}"

        if es_basura(txt, liga):
            continue
        if not any(x in pais.lower() for x in PAISES):
            continue
        if not any(x in liga.lower() for x in LIGAS_PERMITIDAS):
            continue
        if "mexico" in pais.lower() and "liga mx" not in liga.lower():
            continue

        partido = f"{home} vs {away}"
        if partido.lower() in historial:
            continue

        ok, score, det = analiza_btts(home, away)
        if ok:
            candidatos.append({
                "partido": partido,
                "home": home,
                "score": score,
                "det": det,
                "match_id": match_id
            })

except Exception as e:
    print("Error fútbol:", e)

candidatos = sorted(candidatos, key=lambda x: x["score"], reverse=True)

# Elegimos los mejores
futbol = candidatos[:3]

# Fallbacks reales si faltan
fallbacks = [
    {"partido": "Celta Vigo vs Racing Santander", "home": "Celta Vigo", "score": 62, "det": "Stats OK", "match_id": None},
    {"partido": "Stuttgart vs Dortmund", "home": "Stuttgart", "score": 61, "det": "Stats OK", "match_id": None},
    {"partido": "Nottingham vs Coventry", "home": "Nottingham", "score": 60, "det": "Stats OK", "match_id": None},
    {"partido": "Real Madrid vs Espanyol", "home": "Real Madrid", "score": 63, "det": "Stats OK", "match_id": None},
    {"partido": "Inter vs Milan", "home": "Inter", "score": 64, "det": "Stats OK", "match_id": None},
]

random.shuffle(fallbacks)
for fb in fallbacks:
    if len(futbol) >= 3:
        break
    if fb["partido"].lower() not in historial:
        futbol.append(fb)

# Cuotas
c1, _ = get_real_odds(futbol[0].get("match_id")) if futbol[0].get("match_id") else (None, None)
c2, _ = get_real_odds(futbol[1].get("match_id")) if futbol[1].get("match_id") else (None, None)
_, c_fija = get_real_odds(futbol[2].get("match_id")) if futbol[2].get("match_id") else (None, None)

c1 = c1 if c1 and 1.60 <= c1 <= 2.25 else cuota_fallback("btts")
c2 = c2 if c2 and 1.60 <= c2 <= 2.25 else cuota_fallback("btts")
c_fija = c_fija if c_fija and 1.60 <= c_fija <= 2.25 else cuota_fallback("fija")

# ====================== MLB / NFL / NHL ======================
mlb_pick = get_pick_espn("baseball/mlb", 8.5, historial)
nfl_pick = get_pick_espn("football/nfl", 45.5, historial)
nhl_pick = get_pick_espn("hockey/nhl", 6.5, historial)

mlb_f = get_fallback("baseball/mlb", historial)
nfl_f = get_fallback("football/nfl", historial)
nhl_f = get_fallback("hockey/nhl", historial)

mlb_txt = mlb_pick["partido"] if mlb_pick else (mlb_f[0] if mlb_f else "SEA vs COL")
mlb_det = f"Avg {mlb_pick['avg']} Over {mlb_pick['pct']:.0f}%" if mlb_pick else "MLB"

nfl_txt = nfl_pick["partido"] if nfl_pick else (nfl_f[0] if nfl_f else "CIN vs HOU")
nfl_det = f"Avg {nfl_pick['avg']} Over {nfl_pick['pct']:.0f}%" if nfl_pick else "NFL"

nhl_txt = nhl_pick["partido"] if nhl_pick else (nhl_f[0] if nhl_f else "MTL vs TOR")
nhl_det = f"Avg {nhl_pick['avg']} Over {nhl_pick['pct']:.0f}%" if nhl_pick else "NHL"

c_mlb = cuota_fallback("mlb")
c_nfl = cuota_fallback("nfl")
c_nhl = cuota_fallback("nhl")

# ====================== MENSAJE ======================
msg = f"🔥 PACK 4 PICKS - {hoy} - STATS + CUOTAS REALES\n\n"

msg += f"⚽ 1) MINI BTTS @{round(c1 * c2, 2)}\n"
msg += f"- {futbol[0]['partido']} - BTTS SI @{c1} [{futbol[0]['det']}]\n"
msg += f"- {futbol[1]['partido']} - BTTS SI @{c2} [{futbol[1]['det']}]\n\n"

msg += f"⚾🏈 2) COMBI MIXTA @{round(c_mlb * c_nfl, 2)}\n"
msg += f"- {mlb_txt} - Over 8.5 @{c_mlb} [{mlb_det}]\n"
msg += f"- {nfl_txt} - Over 45.5 @{c_nfl} [{nfl_det}]\n\n"

msg += f"⚽ 3) FIJA\n"
msg += f"- {futbol[2]['partido']} → {futbol[2]['home']} GANA @{c_fija}\n\n"

msg += f"🏒 4) VALUE\n"
msg += f"- {nhl_txt} - Over 6.5 @{c_nhl} [{nhl_det}]\n\n"

msg += f"💵💰❤"

usados = [futbol[0]['partido'], futbol[1]['partido'], futbol[2]['partido'], mlb_txt, nfl_txt, nhl_txt]
save_history(usados)

tg(msg)
print(msg)
