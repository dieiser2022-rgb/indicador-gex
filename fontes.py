"""Fontes externas de dados: candles, precos, calendario economico e noticias.

Todas as funcoes sao tolerantes a falha: se a fonte cair, devolvem lista vazia
ou None em vez de levantar excecao, para nao derrubar o terminal inteiro.
"""

import json
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")

YAHOO_CHART = "https://query1.finance.yahoo.com/v8/finance/chart/"

CALENDARIO_URLS = [
    "https://nfs.faireconomy.media/ff_calendar_thisweek.json",
    "https://nfs.faireconomy.media/ff_calendar_thisweek.xml",
]

# Fontes em portugues primeiro: nao precisam de traducao e falam de mercado.
# As internacionais entram depois e passam pelo tradutor.
# Evitar feeds "top stories" de portais: eles trazem financas pessoais
# ("devo vender minha casa?"), que nao servem para operar.
# Usar sempre o feed da SECAO de mercado, nunca o feed geral do portal.
# O feed geral publica tudo: loteria, politica, celebridade. Ja aconteceu
# duas vezes de entrar lixo no painel por causa disso.
NOTICIAS_RSS = [
    ("InfoMoney mercados", "https://www.infomoney.com.br/mercados/feed/", "pt"),
    ("InfoMoney economia", "https://www.infomoney.com.br/economia/feed/", "pt"),
    ("InfoMoney onde investir", "https://www.infomoney.com.br/onde-investir/feed/", "pt"),
    ("Investing BR", "https://br.investing.com/rss/news_25.rss", "pt"),
    ("Investing BR economia", "https://br.investing.com/rss/news_14.rss", "pt"),
    ("Money Times mercados", "https://www.moneytimes.com.br/mercados/feed/", "pt"),
    ("MarketWatch mercados", "https://feeds.content.dowjones.io/public/rss/mw_marketpulse", "en"),
    ("CNBC mercados", "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=20910258", "en"),
    ("Investing mercados", "https://www.investing.com/rss/news_25.rss", "en"),
]

# Rede de seguranca: mesmo no feed de secao as vezes escapa conteudo que nao
# serve para operar. Se o titulo tiver qualquer um destes termos, ele cai fora.
NOTICIAS_BLOQUEAR = (
    "mega-sena", "mega sena", "megasena", "quina", "lotofacil", "lotofácil",
    "lotomania", "timemania", "dia de sorte", "super sete", "loteria",
    "concurso ", "sorteio", "resultado do concurso", "premio acumulado",
    "+milionaria", "+milionária", "milionario hoje", "milionário hoje",
    "horoscopo", "horóscopo", "signo", "receita federal consulta",
    "bolsa familia", "bolsa família", "inss calendario", "inss calendário",
    "novela", "bbb", "big brother", "libertadores", "brasileirao",
    "brasileirão", "escalacao", "escalação", "palpites para",
)

# eventos de calendario que nao servem para nada ao operar
AGENDA_IGNORAR = ("daylight saving", "horario de verao", "bank holiday",
                  "holiday", "market holiday", "no data")

# panorama macro usado no morning call
PAINEL_MACRO = [
    ("NQ=F", "Nasdaq fut"),
    ("ES=F", "S&P fut"),
    ("YM=F", "Dow fut"),
    ("^VIX", "VIX"),
    ("^STOXX50E", "Europa 50"),
    ("^GDAXI", "Alemanha"),
    ("^N225", "Japao"),
    ("^HSI", "Hong Kong"),
    ("^TNX", "Juros 10a EUA"),
    ("DX-Y.NYB", "Dolar (DXY)"),
    ("CL=F", "Petroleo"),
    ("GC=F", "Ouro"),
    ("BTC-USD", "Bitcoin"),
]


def http_get(url, timeout=25):
    pedido = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "application/json, text/xml, application/xml, text/html, */*",
        "Accept-Language": "en-US,en;q=0.9",
    })
    with urllib.request.urlopen(pedido, timeout=timeout) as r:
        return r.read().decode("utf-8", "ignore")


def _url_yahoo(simbolo):
    return YAHOO_CHART + urllib.parse.quote(simbolo, safe="")


# ------------------------------------------------------------------ candles

def candles(simbolo, intervalo="15m", janela="5d"):
    """Lista de candles: [{t, o, h, l, c, v}, ...]. Vazia se a fonte falhar."""
    for tentativa in (intervalo, "1h", "1d"):
        url = (_url_yahoo(simbolo) + "?interval=" + tentativa
               + "&range=" + janela + "&includePrePost=false")
        try:
            dados = json.loads(http_get(url))
        except Exception:
            continue
        res = (dados.get("chart") or {}).get("result")
        if not res:
            continue
        r0 = res[0]
        tempos = r0.get("timestamp") or []
        q = ((r0.get("indicators") or {}).get("quote") or [{}])[0]
        ab, al, ba, fe = (q.get("open") or [], q.get("high") or [],
                          q.get("low") or [], q.get("close") or [])
        vo = q.get("volume") or []
        saida = []
        for i in range(len(tempos)):
            if i >= len(fe) or fe[i] is None:
                continue
            saida.append({
                "t": tempos[i],
                "o": ab[i] if i < len(ab) and ab[i] is not None else fe[i],
                "h": al[i] if i < len(al) and al[i] is not None else fe[i],
                "l": ba[i] if i < len(ba) and ba[i] is not None else fe[i],
                "c": fe[i],
                "v": vo[i] if i < len(vo) and vo[i] is not None else 0,
            })
        if saida:
            return saida
    return []


def cotacao(simbolo):
    """Ultimo preco e variacao do dia: {preco, variacao, pct} ou None."""
    url = _url_yahoo(simbolo) + "?interval=15m&range=5d"
    try:
        dados = json.loads(http_get(url))
    except Exception:
        return None
    res = (dados.get("chart") or {}).get("result")
    if not res:
        return None
    meta = res[0].get("meta") or {}
    q = ((res[0].get("indicators") or {}).get("quote") or [{}])[0]
    fechs = [x for x in (q.get("close") or []) if x is not None]
    if not fechs:
        return None
    preco = float(fechs[-1])
    antes = meta.get("chartPreviousClose") or meta.get("previousClose")
    if not antes:
        antes = fechs[0]
    antes = float(antes)
    var = preco - antes
    return {
        "preco": preco,
        "variacao": var,
        "pct": (var / antes * 100.0) if antes else 0.0,
    }


def panorama():
    """Cotacoes do painel macro, em paralelo. Lista de dicts."""
    from concurrent.futures import ThreadPoolExecutor
    saida = []
    with ThreadPoolExecutor(max_workers=8) as pool:
        futuros = {pool.submit(cotacao, s): (s, nome) for s, nome in PAINEL_MACRO}
        resultados = {}
        for f in futuros:
            s, nome = futuros[f]
            try:
                resultados[s] = f.result(timeout=30)
            except Exception:
                resultados[s] = None
    for s, nome in PAINEL_MACRO:
        c = resultados.get(s)
        saida.append({
            "simbolo": s,
            "nome": nome,
            "preco": c["preco"] if c else None,
            "pct": c["pct"] if c else None,
        })
    return saida


# -------------------------------------------------------- calendario economico

_MESES_IMPACTO = {"high": 3, "medium": 2, "low": 1, "holiday": 0, "": 0}


def _hora_evento(txt_data, txt_hora):
    """Converte '10-27-2026' + '8:30am' em datetime UTC (fonte usa Nova York)."""
    if not txt_data:
        return None
    formatos = ["%m-%d-%Y", "%Y-%m-%d", "%m/%d/%Y"]
    base = None
    for f in formatos:
        try:
            base = datetime.strptime(txt_data.strip(), f)
            break
        except ValueError:
            continue
    if base is None:
        return None
    h = (txt_hora or "").strip().lower()
    if h and h[0].isdigit():
        for f in ["%I:%M%p", "%I%p", "%H:%M"]:
            try:
                t = datetime.strptime(h.replace(" ", ""), f)
                base = base.replace(hour=t.hour, minute=t.minute)
                break
            except ValueError:
                continue
    # a fonte publica em horario de Nova York; -4 no verao, -5 no inverno
    desloc = 4 if 3 <= base.month <= 10 else 5
    return base.replace(tzinfo=timezone(timedelta(hours=-desloc)))


def calendario():
    """Eventos da semana: [{quando, titulo, moeda, impacto, previsao, anterior}]."""
    bruto = None
    formato = None
    for url in CALENDARIO_URLS:
        try:
            bruto = http_get(url, timeout=20)
            formato = "json" if url.endswith(".json") else "xml"
            break
        except Exception:
            continue
    if not bruto:
        return []

    cru = []
    try:
        if formato == "json":
            for e in json.loads(bruto):
                cru.append({
                    "titulo": e.get("title") or "",
                    "moeda": e.get("country") or "",
                    "impacto": (e.get("impact") or "").lower(),
                    "previsao": e.get("forecast") or "",
                    "anterior": e.get("previous") or "",
                    "quando": e.get("date") or "",
                    "hora": "",
                })
        else:
            raiz = ET.fromstring(bruto)
            for e in raiz.iter("event"):
                def pega(tag):
                    no = e.find(tag)
                    return (no.text or "").strip() if no is not None and no.text else ""
                cru.append({
                    "titulo": pega("title"),
                    "moeda": pega("country"),
                    "impacto": pega("impact").lower(),
                    "previsao": pega("forecast"),
                    "anterior": pega("previous"),
                    "quando": pega("date"),
                    "hora": pega("time"),
                })
    except Exception:
        return []

    saida = []
    for e in cru:
        quando = None
        texto = e["quando"]
        if texto and "T" in texto:
            try:
                quando = datetime.fromisoformat(texto.replace("Z", "+00:00"))
            except ValueError:
                quando = None
        if quando is None:
            quando = _hora_evento(texto, e["hora"])
        if quando is None:
            continue
        saida.append({
            "ts": int(quando.timestamp()),
            "titulo": e["titulo"],
            "moeda": e["moeda"],
            "impacto": e["impacto"],
            "peso": _MESES_IMPACTO.get(e["impacto"], 0),
            "previsao": e["previsao"],
            "anterior": e["anterior"],
        })
    # tira ruido: mudanca de horario de verao, feriado sem dado, e repetidos
    limpos = []
    vistos = set()
    for e in saida:
        baixo = e["titulo"].lower()
        if any(p in baixo for p in AGENDA_IGNORAR):
            continue
        chave = (e["titulo"].lower(), e["ts"], e["moeda"])
        if chave in vistos:
            continue
        vistos.add(chave)
        limpos.append(e)

    limpos.sort(key=lambda x: x["ts"])
    return limpos


# ------------------------------------------------------------------- noticias

def _limpar_html(txt):
    saida = []
    dentro = False
    for ch in txt:
        if ch == "<":
            dentro = True
        elif ch == ">":
            dentro = False
        elif not dentro:
            saida.append(ch)
    limpo = "".join(saida)
    for de, para in [("&amp;", "&"), ("&quot;", '"'), ("&#39;", "'"),
                     ("&lt;", "<"), ("&gt;", ">"), ("&nbsp;", " "),
                     ("&apos;", "'"), ("&#8217;", "'"), ("&#8220;", '"'),
                     ("&#8221;", '"')]:
        limpo = limpo.replace(de, para)
    return " ".join(limpo.split())


def _data_rss(txt):
    if not txt:
        return 0
    txt = txt.strip()
    formatos = ["%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %Y %H:%M:%S %Z",
                "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ"]
    for f in formatos:
        try:
            d = datetime.strptime(txt, f)
            if d.tzinfo is None:
                d = d.replace(tzinfo=timezone.utc)
            return int(d.timestamp())
        except ValueError:
            continue
    return 0


_CACHE_TRADUCAO = {}


def traduzir(texto, para="pt"):
    """Traduz usando o endpoint publico do Google Translate.

    Nao e uma API oficial: o Google pode bloquear o trafego sem aviso. Por isso
    e tratada como enfeite - se falhar, devolve o texto original. A prioridade
    sao as fontes que ja publicam em portugues.
    """
    if not texto or not texto.strip():
        return texto
    chave = (texto[:200], para)
    if chave in _CACHE_TRADUCAO:
        return _CACHE_TRADUCAO[chave]

    url = ("https://translate.googleapis.com/translate_a/single"
           "?client=gtx&sl=auto&tl=" + para + "&dt=t&q="
           + urllib.parse.quote(texto[:1800]))
    try:
        bruto = http_get(url, timeout=12)
        pedacos = json.loads(bruto)[0]
        saida = "".join(p[0] for p in pedacos if p and p[0])
        saida = saida.strip() or texto
    except Exception:
        saida = texto
    _CACHE_TRADUCAO[chave] = saida
    return saida


def noticias(limite=14, traduzir_ingles=True):
    """Manchetes de varias fontes RSS, mais recentes primeiro.

    Os feeds em portugues vem direto. Os em ingles passam pelo tradutor,
    que e opcional: se cair, o titulo original e mantido.
    """
    from concurrent.futures import ThreadPoolExecutor

    def uma(par):
        nome, url, idioma = par
        try:
            bruto = http_get(url, timeout=18)
            raiz = ET.fromstring(bruto)
        except Exception:
            return []
        itens = []
        for it in list(raiz.iter("item")) + list(raiz.iter(
                "{http://www.w3.org/2005/Atom}entry")):
            def pega(*tags):
                for t in tags:
                    no = it.find(t)
                    if no is not None and (no.text or "").strip():
                        return no.text.strip()
                return ""
            titulo = _limpar_html(pega("title", "{http://www.w3.org/2005/Atom}title"))
            if not titulo:
                continue
            resumo = _limpar_html(pega("description", "summary",
                                       "{http://www.w3.org/2005/Atom}summary"))
            link = pega("link", "guid")
            quando = _data_rss(pega("pubDate", "published", "updated"))
            itens.append({"fonte": nome, "idioma": idioma, "titulo": titulo,
                          "resumo": resumo[:400], "link": link, "ts": quando,
                          "traduzido": False})
        return itens

    todas = []
    with ThreadPoolExecutor(max_workers=6) as pool:
        for lista in pool.map(uma, NOTICIAS_RSS):
            todas.extend(lista)

    vistos = set()
    unicas = []
    for n in sorted(todas, key=lambda x: x["ts"], reverse=True):
        baixo = n["titulo"].lower()
        if any(p in baixo for p in NOTICIAS_BLOQUEAR):
            continue
        chave = baixo[:70]
        if chave in vistos:
            continue
        vistos.add(chave)
        unicas.append(n)
    unicas = unicas[:limite]

    if traduzir_ingles:
        pendentes = [n for n in unicas if n.get("idioma") != "pt"]
        if pendentes:
            def verte(n):
                original = n["titulo"]
                n["titulo"] = traduzir(original)
                if n["resumo"]:
                    n["resumo"] = traduzir(n["resumo"])
                n["traduzido"] = n["titulo"] != original
                n["original"] = original
                return n
            with ThreadPoolExecutor(max_workers=4) as pool:
                list(pool.map(verte, pendentes))

    return unicas
