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
        hist = hist[-40:]
        with open(HISTORY_FILE, "w") as f:
            json.dump({"recent": hist}, f)
    except:
        pass

def cuota_fallback(t):
    r = {
        "btts": (1.70, 1.95),
        "mlb": (1.65, 1.90),
        "nfl": (1.85, 1.95),
        "nhl": (1.90, 2.15),
        "fija": (1.70, 1.95)
    }
    a, b = r.get(t, (1.80, 1.95))
    return round(random.uniform(a, b), 2)

def get_real_odds(match_id):
    """Obtiene cuotas reales de API-Football"""
    try:
        url = f"https://apiv3.apifootball.com/?action=get_odds&match_id={match_id}&APIkey={API_KEY}"
        data = requests.get(url, timeout=12).json()
        if not isinstance(data, list) or not data:
            return None, None

        btts_list = []
        home_list = []

        for book in data:
            btts = book.get("bts_yes")
            home = book.get("odd_1")
            if btts and str(btts).replace(".", "").isdigit():
                btts_list.append(float(btts))
            if home and str(home).replace(".", "").isdigit():
                home_list.append(float(home))

        btts_avg = round(sum(btts_list) / len(btts_list), 2) if btts_list else None
        home_avg = round(sum(home_list) / len(home_list), 2) if home_list else None
        return btts_avg, home_avg
    except:
        return None, None

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
            return 0, 0, True
        avg = sum(totales) / len(totales)
        pct = sum(1 for x in totales if x > line) / len(totales) * 100
        ok = avg >= line * 0.85 and pct >= 40
        return round(avg, 1), round(pct, 0), ok
    except:
        return 0, 0, True

def get_pick_espn(
