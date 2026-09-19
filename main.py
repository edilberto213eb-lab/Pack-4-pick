import os, requests, random, re
from datetime import datetime, timedelta

TG_TOKEN = os.getenv("TG_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
API_KEY = os.getenv("API_SPORTS_KEY")

def tg(m):
    try:
        requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", json={"chat_id": CHAT_ID, "text": m}, timeout=15)
    except:
        pass

def cuota(t):
    r = {"btts":(1.68,1.95),"mlb":(1.62,1.85),"nfl":(1.87,1.93),"nhl":(1.9,2.1),"fija":(1.72,1.86)}
    a,b = r.get(t,(1.8,1.95))
    return round(random.uniform(a,b),2)

# --- ANALISIS ESPN REAL ---
def analisis_espn(sport, abbr, line):
    try:
        totales=[]
        for i in range(1,8):
            fecha=(datetime.now()-timedelta(days=i)).strftime('%Y%m%d')
            url=f"https://site.api.espn.com/apis/site/v2/sports/{sport}/scoreboard?dates={fecha}"
            d=requests.get(url,timeout=10).json()
            for ev in d.get('events',[]):
                comps=ev['competitions'][0]['competitors']
                for c in comps:
                    if abbr.lower() in c['team']['abbreviation'].lower():
                        try:
                            s=[int(x['score']) for x in comps]
                            totales.append(sum(s))
                        except:
                            pass
        if not totales:
            return 0,0,True
        avg=sum(totales)/len(totales)
        pct=sum(1 for x in totales if x>line)/len(totales)*100
        ok= avg >= line*0.85 and pct>=40
        return round(avg,1), round(pct,0), ok
    except:
        return 0,0,True

def get_pick_espn(sport, line):
    try:
        d=requests.get(f"https://site.api.espn.com/apis/site/v2/sports/{sport}/scoreboard",timeout=10).json()
        lista=[]
        for ev in d.get('events',[])[:6]:
            comp=ev['competitions'][0]['competitors']
            h=next((x for x in comp if x['homeAway']=='home'),comp[0])
            a=next((x for x in comp if x['homeAway']=='away'),comp[1])
            ah=h['team']['abbreviation']
            aa=a['team']['abbreviation']
            avg_h,pct_h,ok_h=analisis_espn(sport,ah,line)
            avg_a,pct_a,ok_a=analisis_espn(sport,aa,line)
            avg=(avg_h+avg_a)/2 if avg_h and avg_a else max(avg_h,avg_a)
            if ok_h or ok_a:
                lista.append({"partido":f"{aa} vs {ah}","avg":avg,"pct":max(pct_h,pct_a)})
        lista=sorted(lista,key=lambda x:x['avg'],reverse=True)
        return lista[0] if lista else None
    except:
        return None

def get_fallback(sport):
    try:
        d=requests.get(f"https://site.api.espn.com/apis/site/v2/sports/{sport}/scoreboard",timeout=10).json()
        out=[]
        for ev in d.get('events',[])[:4]:
            c=ev['competitions'][0]['competitors']
            h=next((x for x in c if x['homeAway']=='home'),c[0])
            a=next((x for x in c if x['homeAway']=='away'),c[1])
            out.append(f"{a['team']['abbreviation']} vs {h['team']['abbreviation']}")
        return out
    except:
        return []

# --- BTTS FUTBOL 7 PJ ---
def analiza_btts(home, away):
    try:
        desde=(datetime.now()-timedelta(days=30)).strftime('%Y-%m-%d')
        hasta=datetime.now().strftime('%Y-%m-%d')
        url=f"https://apiv3.apifootball.com/?action=get_events&from={desde}&to={hasta}&APIkey={API_KEY}"
        data=requests.get(url,timeout=15).json()
        def stats(nombre):
            pars=[x for x in data if nombre.lower() in (x.get('match_hometeam_name','')+x.get('match_awayteam_name','')).lower()][:7]
            if len(pars)<3:
                return 70,70
            btts=0
            over=0
            for p in pars:
                try:
                    gh=int(p.get('match_hometeam_score',0) or 0)
                    ga=int(p.get('match_awayteam_score',0) or 0)
                    if gh>0 and ga>0:
                        btts+=1
                    if gh+ga>=3:
                        over+=1
                except:
                    continue
            pb=btts/len(pars)*100 if pars else 0
            po=over/len(pars)*100 if pars else 0
            return pb,po
        bh,oh=stats(home)
        ba,oa=stats(away)
        valido = bh>=50 and ba>=50
        txt=f"BTTS {bh:.0f}%/{ba:.0f}% Over {oh:.0f}%"
        return valido,txt
    except:
        return True,"Stats OK"

hoy=datetime.now().strftime('%d/%m')
hoy_api=datetime.now().strftime('%Y-%m-%d')
hora=datetime.now().strftime('%H:%M')

PAISES=["england","spain","italy","germany","france","brazil","argentina","mexico","netherlands","portugal","usa","ecuador","belgium","turkey","scotland","switzerland","austria","norway","greece","chile","colombia","uruguay","paraguay","internacional","europa","world"]
LIGAS=["premier league","la liga","serie a","bundesliga","ligue 1","brasileirao","liga profesional","eredivisie","primeira liga","mls","liga pro","liga mx","expansion mx","champions league","libertadores","europa league","championship","laliga2","2. bundesliga","ligue 2","eerste divisie","segunda liga","1. lig","serie b"]

def es_basura(txt,liga):
    t=txt.lower()
    l=liga.lower()
    if re.search(r'u\d{1,2}|sub[-\s]?\d|juvenil|youth|reserve|women|femen',t):
        return True
    if re.search(r'serie\s+[c-z]',l):
        return True
    if re.search(r'(grupo|group|girone)\s+[a-z]\b',l):
        return True
    if re.search(r'(grupo|group)\s+[ivx]{1,4}\b',l):
        return True
    if re.search(r'(grupo|group)\s+\d+\b',l):
        return True
    if any(x in t for x in ["futsal","beach","esports","club friendly","amateur"]):
        return True
    return False

futbol=[]
vistos=set()
detalles=[]

try:
    data=requests.get(f"https://apiv3.apifootball.com/?action=get_events&from={hoy_api}&to={hoy_api}&APIkey={API_KEY}",timeout=15).json()
    for p in data:
        st=str(p.get('match_status','')).lower()
        if any(x in st for x in ['ft','finished','after','live','ht','cancel']):
            continue
        liga=str(p.get('league_name',''))
        pais=str(p.get('country_name','') or "")
        home=p.get('
