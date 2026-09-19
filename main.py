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
        "btts": (1.75, 1.95),
        "over25": (1.75, 2.05),
        "under25": (1.75, 2.10),
        "home15": (1.75, 2.15),
        "mlb": (1.70, 1.95),
        "nfl": (1.80, 1.95),
        "nba": (1.80, 1.95),
        "nhl": (1.85, 2.10)
    }
    a, b = rangos.get(t, (1.80, 1.95))
    return round(random.uniform(a, b), 2)

def get_real_odds(match_id):
    try:
        url = f"https://apiv3.apifootball.com/?action=get_odds&match_id={match_id}&APIkey={API_KEY}"
        data = requests.get(url, timeout=12).json()
        if not isinstance(data, list) or not data:
            return {}

        odds = {"btts": [], "over25": [], "under25": [], "home": []}
        for book in data:
            if book.get("bts_yes") and str(book["bts_yes"]).replace(".", "").isdigit():
                odds["btts"].append(float(book["bts_yes"]))
            if book.get("o+2.5") and str(book["o+2.5"]).replace(".", "").isdigit():
                odds["over25"].append(float(book["o+2.5"]))
            if book.get("u+2.5") and str(book["u+2.5"]).replace(".", "").isdigit():
                odds["under25"].append(float(book["u+2.5"]))
            if book.get("odd_1") and str(book["odd_1"]).replace(".", "").isdigit():
                odds["home"].append(float(book["odd_1"]))

        result = {}
        for k, v in odds.items():
            if v:
                result[k] = round(sum(v) / len(v), 2)
        return result
    except:
        return {}

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
        for ev in d.get("events", [])[:15]:
            status = ev.get("status", {}).get("type", {})
            if status.get("completed", False) or "FINAL" in status.get("name", "").upper():
                continue

            comp = ev["competitions"][0]["competitors"]
            h = next((x for x in comp if x["homeAway"] == "home"), comp[0])
            a = next((x for x in comp if x["homeAway"] == "away"), comp[1])
            
            nombre_h = h["team"]["displayName"]
            nombre_a = a["team"]["displayName"]
            partido = f"{nombre_a} vs {nombre_h}"

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
        for ev in d.get("events", [])[:10]:
            status = ev.get("status", {}).get("type", {})
            if status.get("completed", False) or "FINAL" in status.get("name", "").upper():
                continue
            c = ev["competitions"][0]["competitors"]
            h = next((x for x in c if x["homeAway"] == "home"), c[0])
            a = next((x for x in c if x["homeAway"] == "away"), c[1])
            p = f"{a['team']['displayName']} vs {h['team']['displayName']}"
            if p.lower() not in historial:
                out.append(p)
        return out
    except:
        return []

def analiza_mercados(home, away):
    """Versión Alto Acierto - filtros estrictos"""
    try:
        desde = (datetime.now() - timedelta(days=45)).strftime("%Y-%m-%d")
        hasta = datetime.now().strftime("%Y-%m-%d")
        url = f"https://apiv3.apifootball.com/?action=get_events&from={desde}&to={hasta}&APIkey={API_KEY}"
        data = requests.get(url, timeout=15).json()

        def get_stats(nombre):
            partidos = []
            for x in data:
                h_name = x.get("match_hometeam_name", "").lower()
                a_name = x.get("match_awayteam_name", "").lower()
                if nombre.lower() in h_name or nombre.lower() in a_name:
                    try:
                        gh = int(x.get("match_hometeam_score", 0) or 0)
                        ga = int(x.get("match_awayteam_score", 0) or 0)
                        es_local = nombre.lower() in h_name
                        partidos.append((gh, ga, es_local))
                    except:
                        continue
            return partidos[:8]

        partidos_h = get_stats(home)
        partidos_a = get_stats(away)

        if len(partidos_h) < 4 or len(partidos_a) < 4:
            return None

        # Cálculos
        def calc_btts(partidos):
            return sum(1 for g in partidos if g[0] > 0 and g[1] > 0) / len(partidos) * 100

        def calc_over25(partidos):
            return sum(1 for g in partidos if g[0] + g[1] >= 3) / len(partidos) * 100

        def calc_under25(partidos):
            return sum(1 for g in partidos if g[0] + g[1] <= 2) / len(partidos) * 100

        def calc_avg_goals(partidos):
            return sum(g[0] + g[1] for g in partidos) / len(partidos)

        def calc_home_over15(partidos):
            locales = [g for g in partidos if g[2]]
            if len(locales) < 3:
                return 0
            return sum(1 for g in locales if g[0] >= 2) / len(locales) * 100

        btts_h = calc_btts(partidos_h)
        btts_a = calc_btts(partidos_a)
        over_h = calc_over25(partidos_h)
        over_a = calc_over25(partidos_a)
        under_h = calc_under25(partidos_h)
        under_a = calc_under25(partidos_a)
        avg_h = calc_avg_goals(partidos_h)
        avg_a = calc_avg_goals(partidos_a)
        home15 = calc_home_over15(partidos_h)

        media_combinada = (avg_h + avg_a) / 2

        # === FILTROS ESTRICTOS (ALTO ACIERTO) ===
        mercados = []

        # BTTS Sí - ambos equipos ≥ 58%
        if btts_h >= 58 and btts_a >= 58:
            score = (btts_h + btts_a) / 2
            mercados.append({"tipo": "BTTS SI", "score": score, "key": "btts"})

        # Over 2.5 - ambos ≥ 58% + media combinada ≥ 2.75
        if over_h >= 58 and over_a >= 58 and media_combinada >= 2.75:
            score = (over_h + over_a) / 2
            mercados.append({"tipo": "Over 2.5", "score": score, "key": "over25"})

        # Under 2.5 - ambos ≥ 58%
        if under_h >= 58 and under_a >= 58:
            score = (under_h + under_a) / 2
            mercados.append({"tipo": "Under 2.5", "score": score, "key": "under25"})

        # Local Over 1.5 - local ≥ 62%
        if home15 >= 62:
            mercados.append({"tipo": "Local Over 1.5", "score": home15, "key": "home15"})

        if not mercados:
            return None

        # Elegimos el de mayor score
        mejor = max(mercados, key=lambda x: x["score"])
        return mejor

    except Exception as e:
        print("Error analiza_mercados:", e)
        return None

hoy = datetime.now().strftime("%Y-%m-%d")
hoy_api = hoy

LIGAS_PERMITIDAS = [
    "premier league", "la liga", "serie a", "bundesliga", "ligue 1",
    "champions league", "europa league", "brasileirao", "liga mx",
    "mls", "eredivisie", "primeira liga", "liga profesional",
    "championship", "laliga2", "segunda", "serie b", 
    "2. bundesliga", "ligue 2"
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
futbol_pick = None
futbol_mercado = None
futbol_cuota = None
futbol_score = 0

try:
    data = requests.get(
        f"https://apiv3.apifootball.com/?action=get_events&from={hoy_api}&to={hoy_api}&APIkey={API_KEY}",
        timeout=15
    ).json()

    candidatos = []
    for p in data:
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

        mejor = analiza_mercados(home, away)
        if mejor:
            candidatos.append({
                "partido": partido,
                "mercado": mejor,
                "match_id": match_id,
                "score": mejor["score"]
            })

    if candidatos:
        candidatos = sorted(candidatos, key=lambda x: x["score"], reverse=True)
        elegido = candidatos[0]
        futbol_pick = elegido["partido"]
        futbol_mercado = elegido["mercado"]["tipo"]
        futbol_score = round(elegido["score"])
        
        real_odds = get_real_odds(elegido["match_id"])
        key = elegido["mercado"]["key"]
        
        cuota = real_odds.get(key)
        # Solo aceptamos cuotas entre 1.70 y 2.20
        if cuota and 1.70 <= cuota <= 2.20:
            futbol_cuota = cuota
        else:
            futbol_cuota = cuota_fallback(key)

except Exception as e:
    print("Error fútbol:", e)

if not futbol_pick:
    futbol_pick = "Sin pick fuerte hoy"
    futbol_mercado = "BTTS SI"
    futbol_cuota = 1.85
    futbol_score = 0

# ====================== OTROS DEPORTES ======================
mlb_pick = get_pick_espn("baseball/mlb", 8.5, historial)
nfl_pick = get_pick_espn("football/nfl", 45.5, historial)
nba_pick = get_pick_espn("basketball/nba", 220.5, historial)
nhl_pick = get_pick_espn("hockey/nhl", 6.5, historial)

mlb_f = get_fallback("baseball/mlb", historial)
nfl_f = get_fallback("football/nfl", historial)
nba_f = get_fallback("basketball/nba", historial)
nhl_f = get_fallback("hockey/nhl", historial)

mlb_txt = mlb_pick["partido"] if mlb_pick else (mlb_f[0] if mlb_f else "Yankees vs Red Sox")
nfl_txt = nfl_pick["partido"] if nfl_pick else (nfl_f[0] if nfl_f else "Chiefs vs Bills")
nba_txt = nba_pick["partido"] if nba_pick else (nba_f[0] if nba_f else "Lakers vs Celtics")
nhl_txt = nhl_pick["partido"] if nhl_pick else (nhl_f[0] if nhl_f else "Maple Leafs vs Canadiens")

# ====================== MENSAJE FINAL ======================
msg = f"🔥 PACK 5 DEPORTES - {hoy}\n\n"

if futbol_score > 0:
    msg += f"⚽ FÚTBOL: {futbol_pick} - {futbol_mercado} @{futbol_cuota} [{futbol_score}%]\n"
else:
    msg += f"⚽ FÚTBOL: Sin pick de alta confianza hoy\n"

msg += f"🏈 NFL: {nfl_txt} - Over 45.5 @{cuota_fallback('nfl')}\n"
msg += f"🏀 NBA: {nba_txt} - Over 220.5 @{cuota_fallback('nba')}\n"
msg += f"🏒 NHL: {nhl_txt} - Over 6.5 @{cuota_fallback('nhl')}\n"
msg += f"⚾ MLB: {mlb_txt} - Over 8.5 @{cuota_fallback('mlb')}"

usados = [futbol_pick, nfl_txt, nba_txt, nhl_txt, mlb_txt]
save_history(usados)

tg(msg)
print(msg)
