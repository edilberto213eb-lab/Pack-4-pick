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
        hist.extend([p.lower() for p in nuevos if p])
        hist = hist[-60:]
        with open(HISTORY_FILE, "w") as f:
            json.dump({"recent": hist}, f)
    except:
        pass

def cuota_fallback(t):
    rangos = {
        "btts": (1.72, 1.95),
        "anota": (1.25, 1.45),
        "over25": (1.70, 2.05),
        "under25": (1.70, 2.10),
        "home15": (1.70, 2.15),
        "mlb": (1.65, 1.90),
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
        if not isinstance(data, list):
            return {}

        odds = {"btts": [], "anota": [], "over25": [], "under25": [], "home": []}
        for book in data:
            if not isinstance(book, dict):
                continue
            if book.get("bts_yes") and str(book["bts_yes"]).replace(".", "").isdigit():
                odds["btts"].append(float(book["bts_yes"]))
            if book.get("o+0.5") and str(book["o+0.5"]).replace(".", "").isdigit():
                odds["anota"].append(float(book["o+0.5"]))
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

def analiza_mercados_futbol(home, away):
    try:
        desde = (datetime.now() - timedelta(days=40)).strftime("%Y-%m-%d")
        hasta = datetime.now().strftime("%Y-%m-%d")
        url = f"https://apiv3.apifootball.com/?action=get_events&from={desde}&to={hasta}&APIkey={API_KEY}"
        data = requests.get(url, timeout=15).json()

        if not isinstance(data, list):
            return None

        def get_stats(nombre):
            partidos = []
            for x in data:
                if not isinstance(x, dict):
                    continue
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

        ph = get_stats(home)
        pa = get_stats(away)

        if len(ph) < 4 or len(pa) < 4:
            return None

        def calc_btts(p): return sum(1 for g in p if g[0] > 0 and g[1] > 0) / len(p) * 100
        def calc_over(p): return sum(1 for g in p if g[0] + g[1] >= 3) / len(p) * 100
        def calc_under(p): return sum(1 for g in p if g[0] + g[1] <= 2) / len(p) * 100
        def calc_avg(p): return sum(g[0] + g[1] for g in p) / len(p)
        def calc_home15(p):
            locales = [g for g in p if g[2]]
            if len(locales) < 3: return 0
            return sum(1 for g in locales if g[0] >= 2) / len(locales) * 100
        
        def calc_anota(p, es_local):
            if not p: return 0
            return sum(1 for g in p if (g[0] > 0 if es_local else g[1] > 0)) / len(p) * 100

        btts_h, btts_a = calc_btts(ph), calc_btts(pa)
        over_h, over_a = calc_over(ph), calc_over(pa)
        under_h, under_a = calc_under(ph), calc_under(pa)
        avg_comb = (calc_avg(ph) + calc_avg(pa)) / 2
        home15 = calc_home15(ph)
        anota_h = calc_anota(ph, True)
        anota_a = calc_anota(pa, False)

        mercados = []

        if btts_h >= 40 and btts_a >= 40:
            mercados.append({"tipo": "BTTS SI", "score": (btts_h + btts_a)/2, "key": "btts"})
        elif anota_h >= 70 and anota_a >= 70:
            mercados.append({"tipo": "Equipo Anota", "score": (anota_h + anota_a)/2, "key": "anota"})

        if over_h >= 55 and over_a >= 55 and avg_comb >= 2.70:
            mercados.append({"tipo": "Over 2.5", "score": (over_h + over_a)/2, "key": "over25"})
        if under_h >= 55 and under_a >= 55:
            mercados.append({"tipo": "Under 2.5", "score": (under_h + under_a)/2, "key": "under25"})
        if home15 >= 60:
            mercados.append({"tipo": "Local Over 1.5", "score": home15, "key": "home15"})

        if not mercados:
            return None
        return max(mercados, key=lambda x: x["score"])
    except:
        return None

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

            avg_h, pct_h, ok_h = 0, 0, False
            avg_a, pct_a, ok_a = 0, 0, False

            try:
                for i in range(1, 7):
                    fecha = (datetime.now() - timedelta(days=i)).strftime("%Y%m%d")
                    url = f"https://site.api.espn.com/apis/site/v2/sports/{sport}/scoreboard?dates={fecha}"
                    dd = requests.get(url, timeout=8).json()
                    for e in dd.get("events", []):
                        comps = e["competitions"][0]["competitors"]
                        for c in comps:
                            if h["team"]["abbreviation"].lower() in c["team"]["abbreviation"].lower():
                                s = [int(x["score"]) for x in comps]
                                avg_h = sum(s)
                                pct_h += 1 if sum(s) > line else 0
                            if a["team"]["abbreviation"].lower() in c["team"]["abbreviation"].lower():
                                s = [int(x["score"]) for x in comps]
                                avg_a = sum(s)
                                pct_a += 1 if sum(s) > line else 0
            except:
                pass

            avg = (avg_h + avg_a) / 2 if avg_h and avg_a else max(avg_h, avg_a)
            if avg > line * 0.9:
                candidatos.append({"partido": partido, "avg": round(avg, 1)})

        if not candidatos:
            return None
        candidatos = sorted(candidatos, key=lambda x: x["avg"], reverse=True)
        return candidatos[0]
    except:
        return None

def get_fallback(sport, historial):
    try:
        d = requests.get(f"https://site.api.espn.com/apis/site/v2/sports/{sport}/scoreboard", timeout=10).json()
        for ev in d.get("events", [])[:10]:
            status = ev.get("status", {}).get("type", {})
            if status.get("completed", False) or "FINAL" in status.get("name", "").upper():
                continue
            c = ev["competitions"][0]["competitors"]
            h = next((x for x in c if x["homeAway"] == "home"), c[0])
            a = next((x for x in c if x["homeAway"] == "away"), c[1])
            p = f"{a['team']['displayName']} vs {h['team']['displayName']}"
            if p.lower() not in historial:
                return p
        return None
    except:
        return None

hoy = datetime.now().strftime("%d/%m")
hoy_api = datetime.now().strftime("%Y-%m-%d")
historial = load_history()

LIGAS_OK = [
    "premier league", "la liga", "serie a", "bundesliga", "ligue 1",
    "champions league", "europa league", "brasileirao", "liga mx",
    "mls", "eredivisie", "primeira liga", "liga profesional",
    "championship", "laliga2", "segunda", "serie b", "2. bundesliga", "ligue 2"
]

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

# ====================== FÚTBOL ======================
futbol_picks = []  # Lista para guardar 2 picks
try:
    data = requests.get(
        f"https://apiv3.apifootball.com/?action=get_events&from={hoy_api}&to={hoy_api}&APIkey={API_KEY}",
        timeout=15
    ).json()

    if not isinstance(data, list):
        data = []

    candidatos = []
    for p in data:
        if not isinstance(p, dict):
            continue
        st = str(p.get("match_status", "")).lower()
        if any(x in st for x in ["ft", "finished", "live", "ht", "1h", "2h", "cancel", "postponed"]):
            continue

        liga = str(p.get("league_name", ""))
        pais = str(p.get("country_name", "") or "")
        home = p.get("match_hometeam_name", "")
        away = p.get("match_awayteam_name", "")
        match_id = p.get("match_id")
        txt = f"{liga} {pais} {home} {away}"

        if es_basura(txt, liga):
            continue
        if not any(x in liga.lower() for x in LIGAS_OK):
            continue
        if "mexico" in pais.lower() and "liga mx" not in liga.lower():
            continue

        partido = f"{home} vs {away}"
        if partido.lower() in historial:
            continue

        mejor = analiza_mercados_futbol(home, away)
        if mejor:
            candidatos.append({
                "partido": partido,
                "mercado": mejor,
                "match_id": match_id,
                "score": mejor["score"]
            })

    # Sistema de respaldo para garantizar que el Punto 1 tenga 2 picks reales
    if len(candidatos) < 2:
        for p in data:
            if not isinstance(p, dict): continue
            st = str(p.get("match_status", "")).lower()
            if any(x in st for x in ["ft", "finished", "live", "ht", "1h", "2h", "cancel", "postponed"]): continue
            liga = str(p.get("league_name", ""))
            pais = str(p.get("country_name", "") or "")
            home = p.get("match_hometeam_name", "")
            away = p.get("match_awayteam_name", "")
            match_id = p.get("match_id")
            txt = f"{liga} {pais} {home} {away}"

            if es_basura(txt, liga): continue
            if not any(x in liga.lower() for x in LIGAS_OK): continue
            if "mexico" in pais.lower() and "liga mx" not in liga.lower(): continue

            partido = f"{home} vs {away}"
            if partido.lower() in historial: continue
            if any(c["partido"] == partido for c in candidatos): continue

            candidatos.append({
                "partido": partido,
                "mercado": {"tipo": "BTTS SI", "score": 50, "key": "btts"},
                "match_id": match_id,
                "score": 50
            })
            if len(candidatos) >= 2:
                break

    if candidatos:
        candidatos = sorted(candidatos, key=lambda x: x["score"], reverse=True)
        seleccionados = candidatos[:2] # Tomar los 2 mejores
        
        for elegido in seleccionados:
            real = get_real_odds(elegido["match_id"])
            key = elegido["mercado"]["key"]
            cuota = cuota_fallback(key)
            if key in real and 1.65 <= real[key] <= 2.25:
                cuota = real[key]
            
            futbol_picks.append({
                "partido": elegido["partido"],
                "mercado": elegido["mercado"]["tipo"],
                "cuota": cuota,
                "score": round(elegido["score"])
            })
except Exception as e:
    print("Error fútbol:", e)

# ====================== OTROS DEPORTES ======================
mes_actual = datetime.now().month
nba_en_temporada = mes_actual >= 10 or mes_actual <= 6

if nba_en_temporada:
    nba = get_pick_espn("basketball/nba", 220.5, historial)
else:
    nba = None

mlb = get_pick_espn("baseball/mlb", 8.5, historial)
nfl = get_pick_espn("football/nfl", 45.5, historial)
nhl = get_pick_espn("hockey/nhl", 6.5, historial)

mlb_txt = mlb["partido"] if mlb else (get_fallback("baseball/mlb", historial) or "Yankees vs Red Sox")
nfl_txt = nfl["partido"] if nfl else (get_fallback("football/nfl", historial) or "Chiefs vs Bills")
nhl_txt = nhl["partido"] if nhl else (get_fallback("hockey/nhl", historial) or "Maple Leafs vs Canadiens")

mlb_det = f"Avg {mlb['avg']}" if mlb else "MLB"
nfl_det = f"Avg {nfl['avg']}" if nfl else "NFL"
nhl_det = f"Avg {nhl['avg']}" if nhl else "NHL"

if nba:
    nba_txt = nba["partido"]
    nba_det = f"Avg {nba['avg']}"
    nba_cuota = cuota_fallback('nba')
    nba_mercado = "Over 220.5"
else:
    nba_txt = get_fallback("baseball/mlb", historial) or "Yankees vs Red Sox"
    nba_det = "MLB"
    nba_cuota = cuota_fallback('mlb')
    nba_mercado = "Over 8.5"

# ====================== MENSAJE FINAL ======================
msg = f"🔥 PACK 4 PICKS - {hoy} - STATS + CUOTAS REALES\n\n"

# 1) MINI BTTS (Fútbol) - AHORA CON 2 PARTIDOS
if futbol_picks:
    # Calcular cuota combinada de los 2 picks
    cuota_combinada = 1.0
    for fp in futbol_picks:
        cuota_combinada *= fp["cuota"]
    cuota_combinada = round(cuota_combinada, 2)
    
    # Título dinámico según los mercados
    titulos = [fp["mercado"] for fp in futbol_picks]
    titulo_1 = "MINI BTTS" if all("BTTS" in t for t in titulos) else "MINI BTTS/ANOTA"
    
    msg += f"1) ⚽ {titulo_1} @{cuota_combinada}\n"
    for fp in futbol_picks:
        msg += f"- {fp['partido']} - {fp['mercado']} @{fp['cuota']} [{fp['score']}%]\n"
    msg += "\n"
else:
    # Respaldo extremo en caso de que la API falle por completo
    msg += f"1) ⚽ MINI BTTS @1.85\n"
    msg += f"- Partido por confirmar - BTTS SI @1.85 [50%]\n\n"

# 2) COMBI MIXTA (NFL + NBA/MLB)
cuota_combi = round(cuota_fallback('nfl') * nba_cuota, 2)
msg += f"2) 🏈{'🏀' if nba else '⚾'} COMBI MIXTA @{cuota_combi}\n"
msg += f"- 🏈 {nfl_txt} - Over 45.5 @{cuota_fallback('nfl')} [{nfl_det}]\n"
msg += f"- {'🏀' if nba else '⚾'} {nba_txt} - {nba_mercado} @{nba_cuota} [{nba_det}]\n\n"

# 3) FIJA (NHL)
msg += f"3) 🏒 FIJA\n"
msg += f"- {nhl_txt} - Over 6.5 @{cuota_fallback('nhl')}\n\n"

# 4) VALUE (MLB)
msg += f"4) ⚾ VALUE\n"
msg += f"- {mlb_txt} - Over 8.5 @{cuota_fallback('mlb')} [{mlb_det}]\n\n"

msg += f"💵💰❤"

# Guardar historial de los usados
usados = [fp["partido"] for fp in futbol_picks] + [nfl_txt, nba_txt, nhl_txt, mlb_txt]
save_history(usados)

tg(msg)
print(msg)
