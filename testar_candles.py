import json
import urllib.request
from datetime import datetime

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/131.0.0.0 Safari/537.36"

# queremos candle de 15 minutos; 1h fica como reserva
INTERVALOS = ["15m", "1h"]
JANELA = "1mo"

YAHOO = [
    ("Yahoo NQ=F  (futuro Nasdaq)", "NQ%3DF"),
    ("Yahoo ES=F  (futuro S&P)", "ES%3DF"),
    ("Yahoo ^NDX  (indice Nasdaq-100)", "%5ENDX"),
    ("Yahoo ^SPX  (indice S&P 500)", "%5ESPX"),
    ("Yahoo QQQ   (ETF Nasdaq)", "QQQ"),
]

STOOQ = [
    ("Stooq ^ndx (diario)", "https://stooq.com/q/d/l/?s=%5Endx&i=d"),
    ("Stooq qqq.us (diario)", "https://stooq.com/q/d/l/?s=qqq.us&i=d"),
]


def pegar(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "ignore")


def testar_yahoo(nome, simbolo):
    print("")
    print("---", nome, "---")
    for intervalo in INTERVALOS:
        url = ("https://query1.finance.yahoo.com/v8/finance/chart/" + simbolo
               + "?interval=" + intervalo + "&range=" + JANELA)
        try:
            dados = json.loads(pegar(url))
            res = dados.get("chart", {}).get("result")
            if not res:
                erro = dados.get("chart", {}).get("error")
                print("   " + intervalo + ": sem resultado:", erro)
                continue
            r0 = res[0]
            tempos = r0.get("timestamp") or []
            q = (r0.get("indicators", {}).get("quote") or [{}])[0]
            fech = q.get("close") or []
            if not tempos:
                print("   " + intervalo + ": veio vazio")
                continue
            print("   " + intervalo + ": OK - candles recebidos:", len(tempos))
            for i in [-3, -2, -1]:
                if abs(i) <= len(tempos):
                    t = datetime.fromtimestamp(tempos[i])
                    o = q.get("open", [None])[i]
                    h = q.get("high", [None])[i]
                    l = q.get("low", [None])[i]
                    c = fech[i]
                    print("     %s  O=%s H=%s L=%s C=%s"
                          % (t.strftime("%d/%m %H:%M"), o, h, l, c))
            return intervalo
        except Exception as e:
            print("   " + intervalo + ": FALHOU:", e)
    return ""


def testar_stooq(nome, url):
    print("")
    print("---", nome, "---")
    try:
        txt = pegar(url)
        linhas = [l for l in txt.splitlines() if l.strip()]
        print("   OK - linhas recebidas:", len(linhas))
        for l in linhas[:1] + linhas[-2:]:
            print("    ", l)
        return True
    except Exception as e:
        print("   FALHOU:", e)
        return False


print("procurando fonte de candles de 15 minutos...")
bons = []
for nome, simbolo in YAHOO:
    qual = testar_yahoo(nome, simbolo)
    if qual:
        bons.append(nome + "  [" + qual + "]")
for nome, url in STOOQ:
    if testar_stooq(nome, url):
        bons.append(nome)

print("")
print("=" * 50)
print("FUNCIONARAM:")
if bons:
    for b in bons:
        print("  -", b)
else:
    print("  nenhuma")
print("=" * 50)
