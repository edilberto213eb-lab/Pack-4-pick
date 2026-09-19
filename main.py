import os
import requests
import json
import re
import time
from datetime import datetime, timedelta

# ============================================================
# CONFIGURACIÓN
# ============================================================

TG_TOKEN = os.getenv("TG_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
API_KEY = os.getenv("API_SPORTS_KEY")

HISTORY_FILE = "picks_history.json"

# Cuántos días permanecerá bloqueado un partido
MATCH_COOLDOWN_DAYS = 7

# Cuántos registros conservar
MAX_HISTORY = 500

# ============================================================
# TELEGRAM
# ============================================================

def tg(m):
    try:
        if not TG_TOKEN or not CHAT_ID:
            print("Faltan TG_TOKEN o CHAT_ID")
            return False

        r = requests.post(
            f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
            json={
                "chat_id": CHAT_ID,
                "text": m
            },
            timeout=15
        )

        return r.ok

    except Exception as e:
        print("Error Telegram:", e)
        return False


# ============================================================
# HISTORIAL
# ============================================================

def load_history():

    try:
        if not os.path.exists(HISTORY_FILE):
            return []

        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, dict):
            return []

        history = data.get("history", [])

        if not isinstance(history, list):
            return []

        return history

    except Exception as e:
        print("Error cargando historial:", e)
        return []


def save_history(history):

    try:

        # Limpiar historial antiguo
        limite = datetime.now() - timedelta(days=30)

        limpio = []

        for x in history:

            try:
                fecha = datetime.fromisoformat(x.get("timestamp", ""))

                if fecha >= limite:
                    limpio.append(x)

            except:
                continue

        limpio = limpio[-MAX_HISTORY:]

        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(
                {"history": limpio},
                f,
                ensure_ascii=False,
                indent=2
            )

    except Exception as e:
        print("Error guardando historial:", e)


def normalizar(txt):

    if not txt:
        return ""

    txt = str(txt).lower().strip()

    txt = re.sub(r"\s+", " ", txt)

    txt = txt.replace("-", " ")

    return txt


def match_key(deporte, liga, home, away):

    return (
        f"{normalizar(deporte)}|"
        f"{normalizar(liga)}|"
        f"{normalizar(home)}|"
        f"{normalizar(away)}"
    )


def equipo_key(deporte, home, away):

    equipos = sorted([
        normalizar(home),
        normalizar(away)
    ])

    return f"{normalizar(deporte)}|{equipos[0]}|{equipos[1]}"


def usado_recientemente(deporte, liga, home, away, history):

    ahora = datetime.now()

    mk = match_key(deporte, liga, home, away)
    ek = equipo_key(deporte, home, away)

    for x in history:

        try:

            fecha = datetime.fromisoformat(
                x.get("timestamp", "")
            )

            if ahora - fecha > timedelta(days=MATCH_COOLDOWN_DAYS):
                continue

            if x.get("match_key") == mk:
                return True

            # También bloqueamos mismo enfrentamiento
            # aunque cambie ligeramente el nombre de la liga
            if x.get("team_key") == ek:
                return True

        except:
            continue

    return False


def registrar_pick(
    deporte,
    liga,
    home,
    away,
    mercado,
    history
):

    history.append({
        "timestamp": datetime.now().isoformat(),
        "deporte": deporte,
        "liga": liga,
        "home": home,
        "away": away,
        "mercado": mercado,
        "match_key": match_key(
            deporte,
            liga,
            home,
            away
        ),
        "team_key": equipo_key(
            deporte,
            home,
            away
        )
    })


# ============================================================
# LIGAS DE FÚTBOL PERMITIDAS
# ============================================================

LIGAS_PERMITIDAS = {

    "premier league",
    "english premier league",

    "la liga",
    "laliga",

    "serie a",

    "bundesliga",

    "ligue 1",

    "champions league",
    "uefa champions league",

    "europa league",
    "uefa europa league",

    "conference league",
    "uefa conference league",

    "eredivisie",

    "primeira liga",
    "liga portugal",

    "brasileirao",
    "brasileirão",

    "liga mx",

    "mls",

    "liga profesional",
    "argentina primera division",

    "championship",

    "segunda division",
    "laliga2",

    "2. bundesliga",

    "ligue 2",

    "serie b"
}


# ============================================================
# LIGAS / COMPETICIONES PROHIBIDAS
# ============================================================

PALABRAS_PROHIBIDAS = [

    "women",
    "woman",
    "femenino",
    "feminino",

    "youth",
    "juvenil",

    "reserve",
    "reserves",

    "u18",
    "u19",
    "u20",
    "u21",
    "u22",
    "u23",

    "under 18",
    "under 19",
    "under 20",
    "under 21",
    "under 23",

    "sub 18",
    "sub 19",
    "sub 20",
    "sub 21",
    "sub 23",

    "serie c",
    "serie d",

    "3. liga",
    "liga 3",

    "national league",

    "national league north",
    "national league south",

    "regional",

    "amateur",

    "reserve league",

    "expansion",

    "ascenso",

    "liga premier",

    "terceira",

    "grupo",
    "group",
    "girone",

    "friendly",
    "amistoso",
    "club friendly",

    "preseason",

    "playoff youth"
]


def liga_permitida(liga, pais=""):

    liga_n = normalizar(liga)
    pais_n = normalizar(pais)

    # Primero bloquear basura
    for palabra in PALABRAS_PROHIBIDAS:

        if palabra in liga_n:
            return False

    # México:
    # solamente Liga MX
    if "mexico" in pais_n:

        if liga_n not in {
            "liga mx",
            "liga mx, apertura",
            "liga mx, clausura"
        }:
            return False

    # Lista blanca exacta
    if liga_n in LIGAS_PERMITIDAS:
        return True

    # Algunas APIs agregan texto delante/después
    for permitida in LIGAS_PERMITIDAS:

        if liga_n.startswith(permitida + " "):
            return True

        if liga_n.endswith(" " + permitida):
            return True

    return False


# ============================================================
# FILTRO PARTIDO
# ============================================================

def partido_valido(p, history):

    if not isinstance(p, dict):
        return False

    estado = normalizar(
        p.get("match_status", "")
    )

    estados_prohibidos = [
        "ft",
        "finished",
        "live",
        "ht",
        "1h",
        "2h",
        "cancel",
        "cancelled",
        "postponed",
        "postponed"
    ]

    if any(x == estado or x in estado for x in estados_prohibidos):
        return False

    liga = str(
        p.get("league_name", "")
    ).strip()

    pais = str(
        p.get("country_name", "")
    ).strip()

    home = str(
        p.get("match_hometeam_name", "")
    ).strip()

    away = str(
        p.get("match_awayteam_name", "")
    ).strip()

    if not liga or not home or not away:
        return False

    if not liga_permitida(liga, pais):
        return False

    if usado_recientemente(
        "futbol",
        liga,
        home,
        away,
        history
    ):
        return False

    return True


# ============================================================
# OBTENER PARTIDOS DEL DÍA
# ============================================================

def get_futbol_hoy():

    hoy = datetime.now().strftime("%Y-%m-%d")

    try:

        url = (
            "https://apiv3.apifootball.com/"
            f"?action=get_events"
            f"&from={hoy}"
            f"&to={hoy}"
            f"&APIkey={API_KEY}"
        )

        r = requests.get(
            url,
            timeout=20
        )

        data = r.json()

        if not isinstance(data, list):
            return []

        return data

    except Exception as e:

        print("Error API fútbol:", e)

        return []


# ============================================================
# ESTADÍSTICAS DE FÚTBOL
# ============================================================

def obtener_historial_futbol():

    desde = (
        datetime.now() -
        timedelta(days=40)
    ).strftime("%Y-%m-%d")

    hasta = datetime.now().strftime("%Y-%m-%d")

    try:

        url = (
            "https://apiv3.apifootball.com/"
            f"?action=get_events"
            f"&from={desde}"
            f"&to={hasta}"
            f"&APIkey={API_KEY}"
        )

        data = requests.get(
            url,
            timeout=20
        ).json()

        if not isinstance(data, list):
            return []

        return data

    except Exception as e:

        print("Error estadísticas:", e)

        return []


# ============================================================
# ANALIZADOR DE MERCADOS
# ============================================================

def analiza_mercados_futbol(
    home,
    away,
    data_hist
):

    try:

        def get_stats(nombre):

            partidos = []

            nombre_n = normalizar(nombre)

            for x in data_hist:

                if not isinstance(x, dict):
                    continue

                h_name = normalizar(
                    x.get(
                        "match_hometeam_name",
                        ""
                    )
                )

                a_name = normalizar(
                    x.get(
                        "match_awayteam_name",
                        ""
                    )
                )

                if (
                    nombre_n not in h_name
                    and
                    nombre_n not in a_name
                ):
                    continue

                try:

                    gh = int(
                        x.get(
                            "match_hometeam_score",
                            0
                        ) or 0
                    )

                    ga = int(
                        x.get(
                            "match_awayteam_score",
                            0
                        ) or 0
                    )

                    es_local = (
                        nombre_n in h_name
                    )

                    partidos.append(
                        (gh, ga, es_local)
                    )

                except:
                    continue

            return partidos[:10]

        ph = get_stats(home)
        pa = get_stats(away)

        if len(ph) < 5 or len(pa) < 5:
            return None

        def btts(p):

            return (
                sum(
                    1
                    for g in p
                    if g[0] > 0 and g[1] > 0
                )
                / len(p)
                * 100
            )

        def over25(p):

            return (
                sum(
                    1
                    for g in p
                    if g[0] + g[1] >= 3
                )
                / len(p)
                * 100
            )

        def under25(p):

            return (
                sum(
                    1
                    for g in p
                    if g[0] + g[1] <= 2
                )
                / len(p)
                * 100
            )

        def promedio(p):

            return (
                sum(
                    g[0] + g[1]
                    for g in p
                )
                / len(p)
            )

        def local_over15(p):

            locales = [
                g for g in p
                if g[2]
            ]

            if len(locales) < 3:
                return 0

            return (
                sum(
                    1
                    for g in locales
                    if g[0] >= 2
                )
                / len(locales)
                * 100
            )

        def equipo_anota(p, local):

            if not p:
                return 0

            if local:

                return (
                    sum(
                        1
                        for g in p
                        if g[0] > 0
                    )
                    / len(p)
                    * 100
                )

            return (
                sum(
                    1
                    for g in p
                    if g[1] > 0
                )
                / len(p)
                * 100
            )

        btts_h = btts(ph)
        btts_a = btts(pa)

        over_h = over25(ph)
        over_a = over25(pa)

        under_h = under25(ph)
        under_a = under25(pa)

        avg_h = promedio(ph)
        avg_a = promedio(pa)

        avg_comb = (
            avg_h + avg_a
        ) / 2

        home15 = local_over15(ph)

        anota_h = equipo_anota(
            ph,
            True
        )

        anota_a = equipo_anota(
            pa,
            False
        )

        mercados = []

        # ----------------------------------------------------
        # BTTS
        # ----------------------------------------------------

        if (
            btts_h >= 55
            and
            btts_a >= 55
        ):

            score = (
                btts_h + btts_a
            ) / 2

            mercados.append({
                "tipo": "BTTS SI",
                "score": score,
                "key": "btts"
            })

        # ----------------------------------------------------
        # OVER 2.5
        # ----------------------------------------------------

        if (
            over_h >= 60
            and
            over_a >= 60
            and
            avg_comb >= 2.70
        ):

            score = (
                over_h + over_a
            ) / 2

            mercados.append({
                "tipo": "Over 2.5",
                "score": score,
                "key": "over25"
            })

        # ----------------------------------------------------
        # UNDER 2.5
        # ----------------------------------------------------

        if (
            under_h >= 60
            and
            under_a >= 60
        ):

            score = (
                under_h + under_a
            ) / 2

            mercados.append({
                "tipo": "Under 2.5",
                "score": score,
                "key": "under25"
            })

        # ----------------------------------------------------
        # EQUIPO ANOTA
        # ----------------------------------------------------

        if (
            anota_h >= 75
            and
            anota_a >= 75
        ):

            score = (
                anota_h + anota_a
            ) / 2

            mercados.append({
                "tipo": "Equipo Anota",
                "score": score,
                "key": "anota"
            })

        # ----------------------------------------------------
        # LOCAL OVER 1.5
        # ----------------------------------------------------

        if home15 >= 65:

            mercados.append({
                "tipo": "Local Over 1.5",
                "score": home15,
                "key": "home15"
            })

        if not mercados:
            return None

        return max(
            mercados,
            key=lambda x: x["score"]
        )

    except Exception as e:

        print("Error análisis:", e)

        return None


# ============================================================
# CUOTAS REALES
# ============================================================

def get_real_odds(match_id):

    try:

        url = (
            "https://apiv3.apifootball.com/"
            f"?action=get_odds"
            f"&match_id={match_id}"
            f"&APIkey={API_KEY}"
        )

        data = requests.get(
            url,
            timeout=15
        ).json()

        if not isinstance(data, list):
            return {}

        odds = {
            "btts": [],
            "anota": [],
            "over25": [],
            "under25": [],
            "home15": []
        }

        for book in data:

            if not isinstance(book, dict):
                continue

            campos = {
                "btts": "bts_yes",
                "over25": "o+2.5",
                "under25": "u+2.5",
                "anota": "o+0.5"
            }

            for key, campo in campos.items():

                valor = book.get(campo)

                try:

                    if valor is not None:

                        cuota = float(valor)

                        if 1.01 <= cuota <= 20:
                            odds[key].append(cuota)

                except:
                    pass

        result = {}

        for key, valores in odds.items():

            if valores:

                result[key] = round(
                    sum(valores) /
                    len(valores),
                    2
                )

        return result

    except Exception as e:

        print("Error cuotas:", e)

        return {}


# ============================================================
# SELECCIÓN DE FÚTBOL
# ============================================================

def seleccionar_futbol():

    history = load_history()

    partidos = get_futbol_hoy()

    if not partidos:
        print("No hay partidos de fútbol disponibles.")
        return [], history

    stats = obtener_historial_futbol()

    candidatos = []

    for p in partidos:

        if not partido_valido(
            p,
            history
        ):
            continue

        liga = str(
            p.get("league_name", "")
        )

        pais = str(
            p.get("country_name", "")
        )

        home = str(
            p.get("match_hometeam_name", "")
        )

        away = str(
            p.get("match_awayteam_name", "")
        )

        match_id = p.get("match_id")

        mercado = analiza_mercados_futbol(
            home,
            away,
            stats
        )

        if not mercado:
            continue

        candidatos.append({
            "partido": f"{home} vs {away}",
            "home": home,
            "away": away,
            "liga": liga,
            "pais": pais,
            "match_id": match_id,
            "mercado": mercado,
            "score": mercado["score"]
        })

    if not candidatos:
        print("No hay candidatos de fútbol válidos.")
        return [], history

    # Ordenar por calidad estadística
    candidatos.sort(
        key=lambda x: x["score"],
        reverse=True
    )

    seleccionados = []

    ligas_usadas = set()

    # --------------------------------------------------------
    # PRIMERA PASADA:
    # preferir ligas diferentes
    # --------------------------------------------------------

    for c in candidatos:

        liga = normalizar(
            c["liga"]
        )

        if liga in ligas_usadas:
            continue

        seleccionados.append(c)
        ligas_usadas.add(liga)

        if len(seleccionados) >= 2:
            break

    # --------------------------------------------------------
    # SEGUNDA PASADA:
    # si no hay dos ligas distintas
    # --------------------------------------------------------

    if len(seleccionados) < 2:

        for c in candidatos:

            if c in seleccionados:
                continue

            seleccionados.append(c)

            if len(seleccionados) >= 2:
                break

    resultado = []

    for c in seleccionados:

        real = get_real_odds(
            c["match_id"]
        )

        key = c["mercado"]["key"]

        cuota = real.get(key)

        # IMPORTANTE:
        # Si no hay cuota real, no inventamos una.
        if cuota is None:
            cuota = None

        resultado.append({
            "partido": c["partido"],
            "home": c["home"],
            "away": c["away"],
            "liga": c["liga"],
            "mercado": c["mercado"]["tipo"],
            "key": key,
            "cuota": cuota,
            "score": round(
                c["score"]
            )
        })

    return resultado, history


# ============================================================
# ESPN
# ============================================================

def get_espn_events(sport):

    try:

        url = (
            f"https://site.api.espn.com/"
            f"apis/site/v2/sports/"
            f"{sport}/scoreboard"
        )

        data = requests.get(
            url,
            timeout=12
        ).json()

        return data.get(
            "events",
            []
        )

    except Exception as e:

        print(
            "Error ESPN",
            sport,
            e
        )

        return []


def seleccionar_espn(
    sport,
    mercado,
    historial
):

    eventos = get_espn_events(
        sport
    )

    candidatos = []

    for ev in eventos:

        try:

            status = ev.get(
                "status",
                {}
            ).get(
                "type",
                {}
            )

            if status.get(
                "completed",
                False
            ):
                continue

            comps = ev[
                "competitions"
            ][0]["competitors"]

            home = next(
                (
                    x for x in comps
                    if x["homeAway"] == "home"
                ),
                None
            )

            away = next(
                (
                    x for x in comps
                    if x["homeAway"] == "away"
                ),
                None
            )

            if not home or not away:
                continue

            home_name = home[
                "team"
            ]["displayName"]

            away_name = away[
                "team"
            ]["displayName"]

            liga = (
                ev.get(
                    "league",
                    {}
                ).get(
                    "name",
                    sport
                )
            )

            if usado_recientemente(
                sport,
                liga,
                home_name,
                away_name,
                historial
            ):
                continue

            candidatos.append({
                "home": home_name,
                "away": away_name,
                "liga": liga,
                "partido":
                    f"{away_name} vs {home_name}",
                "mercado": mercado
            })

        except:
            continue

    if not candidatos:
        return None

    # Rotación determinista basada en fecha
    # para no coger siempre el primero
    indice = (
        datetime.now().timetuple().tm_yday
        % len(candidatos)
    )

    return candidatos[indice]


# ============================================================
# CONSTRUIR PACK
# ============================================================

def construir_pack():

    history = load_history()

    futbol, history = seleccionar_futbol()

    seleccionados = []

    # --------------------------------------------------------
    # FÚTBOL
    # --------------------------------------------------------

    for fp in futbol:

        seleccionados.append({
            "deporte": "futbol",
            "home": fp["home"],
            "away": fp["away"],
            "liga": fp["liga"],
            "partido": fp["partido"],
            "mercado": fp["mercado"],
            "cuota": fp["cuota"],
            "score": fp["score"]
        })

    # --------------------------------------------------------
    # MLB
    # --------------------------------------------------------

    mlb = seleccionar_espn(
        "baseball/mlb",
        "Over 8.5",
        history
    )

    # --------------------------------------------------------
    # NFL
    # --------------------------------------------------------

    nfl = seleccionar_espn(
        "football/nfl",
        "Over 45.5",
        history
    )

    # --------------------------------------------------------
    # NHL
    # --------------------------------------------------------

    nhl = seleccionar_espn(
        "hockey/nhl",
        "Over 6.5",
        history
    )

    # --------------------------------------------------------
    # NBA
    # --------------------------------------------------------

    mes = datetime.now().month

    nba = None

    if mes >= 10 or mes <= 6:

        nba = seleccionar_espn(
            "basketball/nba",
            "Over 220.5",
            history
        )

    # --------------------------------------------------------
    # ARMAR MENSAJE
    # --------------------------------------------------------

    hoy = datetime.now().strftime(
        "%d/%m/%Y"
    )

    msg = (
        f"🔥 PACK PICKS - {hoy}\n"
        f"🛡️ FILTRO ANTI-REPETICIÓN ACTIVO\n\n"
    )

    numero = 1

    # --------------------------------------------------------
    # FÚTBOL
    # --------------------------------------------------------

    if seleccionados:

        msg += "⚽ FÚTBOL\n"

        for p in seleccionados:

            cuota_txt = (
                f"@{p['cuota']}"
                if p["cuota"]
                else "CUOTA NO DISPONIBLE"
            )

            msg += (
                f"{numero}) "
                f"{p['partido']}\n"
                f"   🏆 {p['liga']}\n"
                f"   🎯 {p['mercado']} "
                f"{cuota_txt}\n"
                f"   📊 Score {p['score']}%\n\n"
            )

            numero += 1

    # --------------------------------------------------------
    # MLB
    # --------------------------------------------------------

    if mlb:

        msg += (
            f"⚾ {numero}) MLB\n"
            f"{mlb['partido']}\n"
            f"🎯 {mlb['mercado']}\n\n"
        )

        numero += 1

    # --------------------------------------------------------
    # NFL
    # --------------------------------------------------------

    if nfl:

        msg += (
            f"🏈 {numero}) NFL\n"
            f"{nfl['partido']}\n"
            f"🎯 {nfl['mercado']}\n\n"
        )

        numero += 1

    # --------------------------------------------------------
    # NHL
    # --------------------------------------------------------

    if nhl:

        msg += (
            f"🏒 {numero}) NHL\n"
            f"{nhl['partido']}\n"
            f"🎯 {nhl['mercado']}\n\n"
        )

        numero += 1

    # --------------------------------------------------------
    # NBA
    # --------------------------------------------------------

    if nba:

        msg += (
            f"🏀 {numero}) NBA\n"
            f"{nba['partido']}\n"
            f"🎯 {nba['mercado']}\n\n"
        )

        numero += 1

    if len(seleccionados) == 0 and not any(
        [mlb, nfl, nhl, nba]
    ):

        msg += (
            "⚠️ No encontré picks nuevos "
            "que cumplan los filtros.\n"
            "No se enviaron partidos inventados."
        )

        return msg, history, []

    # --------------------------------------------------------
    # REGISTRAR TODO LO ENVIADO
    # --------------------------------------------------------

    enviados = []

    for p in seleccionados:

        registrar_pick(
            "futbol",
            p["liga"],
            p["home"],
            p["away"],
            p["mercado"],
            history
        )

        enviados.append(
            (
                "futbol",
                p["liga"],
                p["home"],
                p["away"]
            )
        )

    if mlb:

        registrar_pick(
            "baseball/mlb",
            mlb["liga"],
            mlb["home"],
            mlb["away"],
            mlb["mercado"],
            history
        )

        enviados.append(
            (
                "baseball/mlb",
                mlb["liga"],
                mlb["home"],
                mlb["away"]
            )
        )

    if nfl:

        registrar_pick(
            "football/nfl",
            nfl["liga"],
            nfl["home"],
            nfl["away"],
            nfl["mercado"],
            history
        )

        enviados.append(
            (
                "football/nfl",
                nfl["liga"],
                nfl["home"],
                nfl["away"]
            )
        )

    if nhl:

        registrar_pick(
            "hockey/nhl",
            nhl["liga"],
            nhl["home"],
            nhl["away"],
            nhl["mercado"],
            history
        )

        enviados.append(
            (
                "hockey/nhl",
                nhl["liga"],
                nhl["home"],
                nhl["away"]
            )
        )

    if nba:

        registrar_pick(
            "basketball/nba",
            nba["liga"],
            nba["home"],
            nba["away"],
            nba["mercado"],
            history
        )

        enviados.append(
            (
                "basketball/nba",
                nba["liga"],
                nba["home"],
                nba["away"]
            )
        )

    save_history(history)

    return msg, history, enviados


# ============================================================
# EJECUCIÓN
# ============================================================

if __name__ == "__main__":

    print(
        "======================================"
    )

    print(
        "🤖 BOT PICKS ULTRA"
    )

    print(
        "🛡️ Anti-repetición: ACTIVO"
    )

    print(
        "🧹 Filtro ligas basura: ACTIVO"
    )

    print(
        "📚 Historial: ACTIVO"
    )

    print(
        "======================================"
    )

    mensaje, history, enviados = construir_pack()

    print(mensaje)

    # Solo enviar si existe contenido real
    tg(mensaje)

    print(
        f"\n✅ Picks enviados: {len(enviados)}"
    )

    print(
        f"📚 Historial almacenado: {len(history)}"
    )
