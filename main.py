import os
import requests
import random
import re
import json
from datetime import datetime, timedelta, timezone

# ============================================================
# CONFIGURACIÓN
# ============================================================

TG_TOKEN = os.getenv("TG_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
API_KEY = os.getenv("API_SPORTS_KEY")

HISTORY_FILE = "picks_history.json"

# Margen de seguridad:
# El partido debe comenzar al menos X minutos después de ahora.
MINUTOS_ANTICIPACION = 10


# ============================================================
# TELEGRAM
# ============================================================

def tg(m):
    try:
        if not TG_TOKEN or not CHAT_ID:
            print("Faltan TG_TOKEN o CHAT_ID")
            return

        requests.post(
            f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
            json={
                "chat_id": CHAT_ID,
                "text": m
            },
            timeout=15
        )
    except Exception as e:
        print("Error Telegram:", e)


# ============================================================
# HISTORIAL
# ============================================================

def load_history():
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        return set(
            str(x).lower()
            for x in data.get("recent", [])
        )

    except Exception:
        return set()


def save_history(nuevos):
    try:
        hist = list(load_history())

        for p in nuevos:
            if p:
                hist.append(str(p).lower())

        hist = hist[-60:]

        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(
                {"recent": hist},
                f,
                ensure_ascii=False,
                indent=2
            )

    except Exception as e:
        print("Error guardando historial:", e)


# ============================================================
# CUOTAS FALLBACK
# ============================================================

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


# ============================================================
# FECHA/HORA DEL PARTIDO
# ============================================================

def obtener_hora_partido(p):
    """
    Intenta obtener la fecha/hora de inicio desde distintos
    campos utilizados por API-Football.
    """

    posibles = [
        p.get("match_date"),
        p.get("match_time"),
        p.get("match_datetime"),
        p.get("match_start"),
        p.get("event_date"),
        p.get("date")
    ]

    fecha = None
    hora = None

    for valor in posibles:
        if not valor:
            continue

        texto = str(valor).strip()

        # Detectar fecha YYYY-MM-DD
        m_fecha = re.search(
            r"(20\d{2}-\d{2}-\d{2})",
            texto
        )

        # Detectar hora HH:MM
        m_hora = re.search(
            r"(\d{1,2}:\d{2})",
            texto
        )

        if m_fecha:
            fecha = m_fecha.group(1)

        if m_hora:
            hora = m_hora.group(1)

        if fecha and hora:
            break

    if not fecha:
        return None

    if not hora:
        hora = "00:00"

    try:
        return datetime.strptime(
            f"{fecha} {hora}",
            "%Y-%m-%d %H:%M"
        )

    except Exception:
        return None


def partido_es_futuro(p):
    """
    FILTRO PRINCIPAL.

    El partido solamente pasa si:
    - tiene fecha/hora válida
    - comienza después de ahora + margen
    """

    inicio = obtener_hora_partido(p)

    if inicio is None:
        return False

    ahora = datetime.now()

    limite = ahora + timedelta(
        minutes=MINUTOS_ANTICIPACION
    )

    return inicio > limite


# ============================================================
# FILTRO DE ESTADOS
# ============================================================

ESTADOS_PROHIBIDOS = [
    "live",
    "1h",
    "2h",
    "ht",
    "half",
    "halftime",
    "ft",
    "finished",
    "final",
    "ended",
    "complete",
    "completed",
    "cancel",
    "cancelled",
    "canceled",
    "postponed",
    "suspended",
    "abandoned",
    "delayed",
    "interrupted"
]


def estado_prohibido(p):
    campos = [
        p.get("match_status"),
        p.get("status"),
        p.get("status_name"),
        p.get("event_status")
    ]

    texto = " ".join(
        str(x).lower()
        for x in campos
        if x
    )

    for estado in ESTADOS_PROHIBIDOS:
        if estado in texto:
            return True

    return False


# ============================================================
# LIGAS PERMITIDAS
# ============================================================

LIGAS_EXACTAS = {
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

    "brasileirao serie a",
    "brazil serie a",

    "liga mx",
    "mexico liga mx",

    "mls",
    "major league soccer",

    "eredivisie",

    "primeira liga",
    "liga portugal",

    "liga profesional",
    "argentina primera division",

    "championship",
    "english championship",

    "laliga2",
    "la liga 2",
    "segunda division",

    "serie b",

    "2. bundesliga",
    "2 bundesliga",

    "ligue 2"
}


def normalizar_liga(liga):
    liga = str(liga).lower().strip()

    liga = re.sub(
        r"\s+",
        " ",
        liga
    )

    return liga


def liga_permitida(liga):
    l = normalizar_liga(liga)

    # Coincidencia exacta
    if l in LIGAS_EXACTAS:
        return True

    # Algunos nombres oficiales pueden traer prefijos.
    permitidas_parciales = [
        "uefa champions league",
        "uefa europa league",
        "english championship",
        "major league soccer",
        "brazil serie a",
        "mexico liga mx",
        "argentina primera division"
    ]

    for x in permitidas_parciales:
        if l == x:
            return True

    return False


# ============================================================
# FILTRO DE LIGAS BASURA
# ============================================================

def es_basura(txt, liga):
    t = str(txt).lower()
    l = str(liga).lower()

    patrones = [
        r"\bu\d{1,2}\b",
        r"\bsub[-\s]?\d+",
        r"\byouth\b",
        r"\bjuvenil\b",
        r"\breserve\b",
        r"\breserves\b",
        r"\bwomen\b",
        r"\bfemenino\b",
        r"\bfeminino\b",
        r"\bgirls\b",
        r"\b2nd team\b",
        r"\bii\b"
    ]

    for patron in patrones:
        if re.search(patron, t):
            return True

    ligas_malas = [
        "serie c",
        "serie d",
        "3. liga",
        "3 liga",
        "national league",
        "liga 3",
        "terceira",
        "expansion",
        "liga premier",
        "ascenso",
        "regional",
        "amateur",
        "reserve",
        "reserves",
        "youth",
        "u21",
        "u20",
        "u19",
        "u18",
        "u17"
    ]

    for mala in ligas_malas:
        if mala in l:
            return True

    return False


# ============================================================
# VALIDACIÓN COMPLETA DEL PARTIDO
# ============================================================

def partido_valido(p):
    if not isinstance(p, dict):
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

    # --------------------------------------------------------
    # 1. LIGA ESTRICTA
    # --------------------------------------------------------

    if not liga_permitida(liga):
        return False

    # --------------------------------------------------------
    # 2. BASURA
    # --------------------------------------------------------

    txt = f"{liga} {pais} {home} {away}"

    if es_basura(txt, liga):
        return False

    # --------------------------------------------------------
    # 3. ESTADO
    # --------------------------------------------------------

    if estado_prohibido(p):
        return False

    # --------------------------------------------------------
    # 4. FECHA/HORA FUTURA
    # --------------------------------------------------------

    if not partido_es_futuro(p):
        return False

    # --------------------------------------------------------
    # 5. MÉXICO
    # --------------------------------------------------------

    if "mexico" in pais.lower():

        if "liga mx" not in liga.lower():
            return False

    return True


# ============================================================
# ODDS REALES
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
            timeout=12
        ).json()

        if not isinstance(data, list):
            return {}

        odds = {
            "btts": [],
            "anota": [],
            "over25": [],
            "under25": [],
            "home": []
        }

        for book in data:

            if not isinstance(book, dict):
                continue

            valores = {
                "btts": book.get("bts_yes"),
                "anota": book.get("o+0.5"),
                "over25": book.get("o+2.5"),
                "under25": book.get("u+2.5"),
                "home": book.get("odd_1")
            }

            for key, valor in valores.items():

                try:

                    if valor is not None:

                        numero = float(valor)

                        if numero > 1:
                            odds[key].append(numero)

                except:
                    pass

        resultado = {}

        for k, v in odds.items():

            if v:
                resultado[k] = round(
                    sum(v) / len(v),
                    2
                )

        return resultado

    except Exception as e:

        print("Error odds:", e)

        return {}


# ============================================================
# ANÁLISIS FÚTBOL
# ============================================================

def analiza_mercados_futbol(home, away):

    try:

        desde = (
            datetime.now() -
            timedelta(days=40)
        ).strftime("%Y-%m-%d")

        hasta = datetime.now().strftime(
            "%Y-%m-%d"
        )

        url = (
            "https://apiv3.apifootball.com/"
            f"?action=get_events"
            f"&from={desde}"
            f"&to={hasta}"
            f"&APIkey={API_KEY}"
        )

        data = requests.get(
            url,
            timeout=15
        ).json()

        if not isinstance(data, list):
            return None

        def get_stats(nombre):

            partidos = []

            for x in data:

                if not isinstance(x, dict):
                    continue

                h_name = str(
                    x.get(
                        "match_hometeam_name",
                        ""
                    )
                ).lower()

                a_name = str(
                    x.get(
                        "match_awayteam_name",
                        ""
                    )
                ).lower()

                if (
                    nombre.lower() in h_name
                    or
                    nombre.lower() in a_name
                ):

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
                            nombre.lower()
                            in h_name
                        )

                        partidos.append(
                            (gh, ga, es_local)
                        )

                    except:
                        continue

            return partidos[:8]

        ph = get_stats(home)
        pa = get_stats(away)

        if len(ph) < 4 or len(pa) < 4:
            return None

        def calc_btts(p):

            return (
                sum(
                    1 for g in p
                    if g[0] > 0
                    and g[1] > 0
                )
                / len(p)
                * 100
            )

        def calc_over(p):

            return (
                sum(
                    1 for g in p
                    if g[0] + g[1] >= 3
                )
                / len(p)
                * 100
            )

        def calc_under(p):

            return (
                sum(
                    1 for g in p
                    if g[0] + g[1] <= 2
                )
                / len(p)
                * 100
            )

        def calc_avg(p):

            return sum(
                g[0] + g[1]
                for g in p
            ) / len(p)

        def calc_home15(p):

            locales = [
                g for g in p
                if g[2]
            ]

            if len(locales) < 3:
                return 0

            return (
                sum(
                    1 for g in locales
                    if g[0] >= 2
                )
                / len(locales)
                * 100
            )

        def calc_anota(p, es_local):

            if not p:
                return 0

            return (
                sum(
                    1 for g in p
                    if (
                        g[0] > 0
                        if es_local
                        else g[1] > 0
                    )
                )
                / len(p)
                * 100
            )

        btts_h = calc_btts(ph)
        btts_a = calc_btts(pa)

        over_h = calc_over(ph)
        over_a = calc_over(pa)

        under_h = calc_under(ph)
        under_a = calc_under(pa)

        avg_comb = (
            calc_avg(ph)
            + calc_avg(pa)
        ) / 2

        home15 = calc_home15(ph)

        anota_h = calc_anota(
            ph,
            True
        )

        anota_a = calc_anota(
            pa,
            False
        )

        mercados = []

        if (
            btts_h >= 40
            and btts_a >= 40
        ):
            mercados.append({
                "tipo": "BTTS SI",
                "score": (
                    btts_h + btts_a
                ) / 2,
                "key": "btts"
            })

        elif (
            anota_h >= 70
            and anota_a >= 70
        ):
            mercados.append({
                "tipo": "Equipo Anota",
                "score": (
                    anota_h + anota_a
                ) / 2,
                "key": "anota"
            })

        if (
            over_h >= 55
            and over_a >= 55
            and avg_comb >= 2.70
        ):
            mercados.append({
                "tipo": "Over 2.5",
                "score": (
                    over_h + over_a
                ) / 2,
                "key": "over25"
            })

        if (
            under_h >= 55
            and under_a >= 55
        ):
            mercados.append({
                "tipo": "Under 2.5",
                "score": (
                    under_h + under_a
                ) / 2,
                "key": "under25"
            })

        if home15 >= 60:
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

        print(
            "Error análisis fútbol:",
            e
        )

        return None


# ============================================================
# OBTENER PARTIDOS FÚTBOL
# ============================================================

def obtener_partidos_futbol():

    hoy = datetime.now().strftime(
        "%Y-%m-%d"
    )

    url = (
        "https://apiv3.apifootball.com/"
        f"?action=get_events"
        f"&from={hoy}"
        f"&to={hoy}"
        f"&APIkey={API_KEY}"
    )

    try:

        data = requests.get(
            url,
            timeout=15
        ).json()

        if not isinstance(data, list):
            return []

        return [
            p for p in data
            if partido_valido(p)
        ]

    except Exception as e:

        print(
            "Error obteniendo fútbol:",
            e
        )

        return []


# ============================================================
# FÚTBOL PICKS
# ============================================================

historial = load_history()

futbol_picks = []

try:

    partidos = obtener_partidos_futbol()

    print(
        "Partidos futuros válidos:",
        len(partidos)
    )

    candidatos = []

    for p in partidos:

        home = p.get(
            "match_hometeam_name",
            ""
        )

        away = p.get(
            "match_awayteam_name",
            ""
        )

        liga = p.get(
            "league_name",
            ""
        )

        match_id = p.get(
            "match_id"
        )

        partido = (
            f"{home} vs {away}"
        )

        # Historial
        if partido.lower() in historial:
            continue

        mejor = analiza_mercados_futbol(
            home,
            away
        )

        if mejor:

            candidatos.append({
                "partido": partido,
                "liga": liga,
                "mercado": mejor,
                "match_id": match_id,
                "score": mejor["score"]
            })

    # Ordenar por score
    candidatos.sort(
        key=lambda x: x["score"],
        reverse=True
    )

    # Solo los 2 mejores
    seleccionados = candidatos[:2]

    for elegido in seleccionados:

        real = get_real_odds(
            elegido["match_id"]
        )

        key = elegido[
            "mercado"
        ]["key"]

        cuota = cuota_fallback(key)

        if (
            key in real
            and 1.65 <= real[key] <= 2.25
        ):
            cuota = real[key]

        futbol_picks.append({
            "partido": elegido["partido"],
            "liga": elegido["liga"],
            "mercado": elegido[
                "mercado"
            ]["tipo"],
            "cuota": cuota,
            "score": round(
                elegido["score"]
            )
        })

except Exception as e:

    print(
        "Error fútbol:",
        e
    )


# ============================================================
# MENSAJE
# ============================================================

hoy = datetime.now().strftime(
    "%d/%m/%Y %H:%M"
)

msg = (
    "🔥 PACK FÚTBOL — "
    f"{hoy}\n\n"
)


if futbol_picks:

    cuota_combinada = 1.0

    for fp in futbol_picks:
        cuota_combinada *= fp["cuota"]

    cuota_combinada = round(
        cuota_combinada,
        2
    )

    msg += (
        f"⚽ MINI PACK "
        f"@{cuota_combinada}\n\n"
    )

    for i, fp in enumerate(
        futbol_picks,
        1
    ):

        msg += (
            f"{i}) {fp['partido']}\n"
            f"🏆 {fp['liga']}\n"
            f"📊 {fp['mercado']}\n"
            f"💰 @ {fp['cuota']}\n"
            f"📈 Score: {fp['score']}%\n\n"
        )

else:

    msg += (
        "⚠️ No encontré 2 partidos "
        "futuros que cumplan todos "
        "los filtros.\n\n"
        "No se genera un partido "
        "inventado.\n\n"
    )


# ============================================================
# ENVIAR
# ============================================================

tg(msg)

print(msg)


# ============================================================
# GUARDAR HISTORIAL
# ============================================================

usados = [
    fp["partido"]
    for fp in futbol_picks
]

save_history(usados)
