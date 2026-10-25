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

# Nomes dos eventos economicos em portugues.
#
# Dicionario em vez de tradutor automatico por tres razoes: a lista de eventos
# e fechada e se repete toda semana, entao cobre quase tudo; os termos sao
# tecnicos e o tradutor erraria ("Core CPI" nao e "CPI do nucleo do caroco");
# e funciona sem rede, instantaneo, sem depender de servico de terceiro.
AGENDA_NOMES = {
    # inflacao
    "cpi": "IPC (inflacao ao consumidor)",
    "core cpi": "IPC nucleo",
    "ppi": "IPP (inflacao ao produtor)",
    "core ppi": "IPP nucleo",
    "pce price index": "Indice de precos PCE",
    "core pce price index": "Indice PCE nucleo",
    "cpi flash estimate": "IPC preliminar",
    # emprego
    "non-farm employment change": "Criacao de vagas (payroll)",
    "nonfarm payrolls": "Criacao de vagas (payroll)",
    "adp non-farm employment change": "Criacao de vagas (ADP)",
    "unemployment rate": "Taxa de desemprego",
    "unemployment claims": "Pedidos de auxilio-desemprego",
    "jobless claims": "Pedidos de auxilio-desemprego",
    "initial jobless claims": "Pedidos iniciais de auxilio-desemprego",
    "continuing jobless claims": "Pedidos continuados de auxilio-desemprego",
    "average hourly earnings": "Rendimento medio por hora",
    "jolts job openings": "Vagas abertas (JOLTS)",
    "challenger job cuts": "Cortes de vagas (Challenger)",
    "employment change": "Variacao do emprego",
    # juros e banco central
    "federal funds rate": "Decisao de juros do Fed",
    "fed interest rate decision": "Decisao de juros do Fed",
    "fomc statement": "Comunicado do FOMC",
    "fomc meeting minutes": "Ata do FOMC",
    "fomc press conference": "Entrevista do FOMC",
    "fomc member speaks": "Discurso de membro do FOMC",
    "fed chair powell speaks": "Discurso de Powell (Fed)",
    "fed chair powell testifies": "Powell no Congresso",
    "beige book": "Livro Bege do Fed",
    "main refinancing rate": "Decisao de juros do BCE",
    "ecb press conference": "Entrevista do BCE",
    "monetary policy statement": "Comunicado de politica monetaria",
    "official bank rate": "Decisao de juros do BoE",
    "boj policy rate": "Decisao de juros do BoJ",
    # atividade
    "gdp": "PIB",
    "gdp growth rate": "Crescimento do PIB",
    "prelim gdp": "PIB preliminar",
    "final gdp": "PIB final",
    "retail sales": "Vendas no varejo",
    "core retail sales": "Vendas no varejo nucleo",
    "industrial production": "Producao industrial",
    "capacity utilization rate": "Uso da capacidade industrial",
    "factory orders": "Pedidos a industria",
    "durable goods orders": "Pedidos de bens duraveis",
    "core durable goods orders": "Pedidos de bens duraveis nucleo",
    "trade balance": "Balanca comercial",
    "current account": "Conta corrente",
    # pesquisas e indices
    "ism manufacturing pmi": "PMI industrial (ISM)",
    "ism services pmi": "PMI de servicos (ISM)",
    "flash manufacturing pmi": "PMI industrial preliminar",
    "flash services pmi": "PMI de servicos preliminar",
    "manufacturing pmi": "PMI industrial",
    "services pmi": "PMI de servicos",
    "composite pmi": "PMI composto",
    "consumer confidence": "Confianca do consumidor",
    "cb consumer confidence": "Confianca do consumidor (CB)",
    "consumer sentiment": "Sentimento do consumidor",
    "prelim um consumer sentiment": "Sentimento do consumidor (Michigan)",
    "empire state manufacturing index": "Indice industrial de Nova York",
    "philly fed manufacturing index": "Indice industrial da Filadelfia",
    "chicago pmi": "PMI de Chicago",
    "zew economic sentiment": "Sentimento economico (ZEW)",
    "ifo business climate": "Clima de negocios (Ifo)",
    # imoveis
    "building permits": "Alvaras de construcao",
    "housing starts": "Inicio de construcoes",
    "existing home sales": "Venda de casas usadas",
    "new home sales": "Venda de casas novas",
    "pending home sales": "Vendas pendentes de casas",
    "case shiller home price index": "Indice de precos de casas (Case-Shiller)",
    # energia e tesouro
    "crude oil inventories": "Estoques de petroleo",
    "natural gas storage": "Estoques de gas natural",
    "10-y bond auction": "Leilao de titulos de 10 anos",
    "30-y bond auction": "Leilao de titulos de 30 anos",
    "treasury currency report": "Relatorio cambial do Tesouro",
}

# sufixos e marcadores que aparecem colados no nome do evento
AGENDA_SUFIXOS = [
    (" m/m", " mensal"), (" q/q", " trimestral"), (" y/y", " anual"),
    (" mom", " mensal"), (" qoq", " trimestral"), (" yoy", " anual"),
    (" (qoq)", " trimestral"), (" (yoy)", " anual"), (" (mom)", " mensal"),
]
AGENDA_PREFIXOS = [
    ("flash ", "preliminar: "), ("prelim ", "preliminar: "),
    ("preliminary ", "preliminar: "), ("final ", "final: "),
    ("revised ", "revisado: "), ("core ", "nucleo "),
]

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
        # guarda o nome original: o dicionario pode nao cobrir um evento novo,
        # e ai da para ver o que faltou traduzir
        e["original"] = e["titulo"]
        e["titulo"] = nome_evento(e["titulo"])
        e["traduzido"] = e["titulo"] != e["original"]
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


def _traduz_google(texto, para):
    url = ("https://translate.googleapis.com/translate_a/single"
           "?client=gtx&sl=auto&tl=" + para + "&dt=t&q="
           + urllib.parse.quote(texto[:1800]))
    pedacos = json.loads(http_get(url, timeout=12))[0]
    return "".join(p[0] for p in pedacos if p and p[0]).strip()


def _traduz_mymemory(texto, para):
    # reserva: API publica, sem chave, com limite diario para anonimo
    alvo = "pt-br" if para == "pt" else para
    url = ("https://api.mymemory.translated.net/get?langpair=en|" + alvo
           + "&q=" + urllib.parse.quote(texto[:480]))
    d = json.loads(http_get(url, timeout=12))
    return (d.get("responseData") or {}).get("translatedText", "").strip()


def traduzir(texto, para="pt"):
    """Traduz com dois servicos em sequencia, cada um sem chave de API.

    Nenhum dos dois e contratado, entao qualquer um pode recusar o pedido a
    qualquer momento. Se os dois falharem, devolve o texto original - melhor a
    manchete em ingles do que manchete nenhuma.
    """
    if not texto or not texto.strip():
        return texto
    chave = (texto[:200], para)
    if chave in _CACHE_TRADUCAO:
        return _CACHE_TRADUCAO[chave]

    saida = ""
    for tentativa in (_traduz_google, _traduz_mymemory):
        try:
            saida = tentativa(texto, para)
            if saida and saida.lower() != texto.lower():
                break
        except Exception:
            saida = ""
    saida = saida or texto
    _CACHE_TRADUCAO[chave] = saida
    return saida


# ------------------------------------------------------------- relevancia
# Peso 3: mexe com o indice inteiro. Peso 2: mexe com um setor ou uma empresa
# grande. O resto fica em 1. A busca e feita no titulo em portugues, entao os
# termos aparecem nas duas linguas onde faz diferenca.
PESO_ALTO = (
    "fed", "fomc", "powell", "juros", "taxa de juros", "inflacao", "inflação",
    "cpi", "ipca", "payroll", "desemprego", "pib", "gdp", "recessao",
    "recessão", "tarifa", "tarifas", "guerra", "ataque", "sancao", "sanção",
    "banco central", "copom", "selic", "treasury", "titulos do tesouro",
    "rebaixa", "rating", "crise", "circuit breaker", "nasdaq", "s&p 500",
    "dolar dispara", "dólar dispara", "petroleo dispara", "petróleo dispara",
)
PESO_MEDIO = (
    "nvidia", "apple", "microsoft", "tesla", "amazon", "alphabet", "google",
    "meta", "broadcom", "amd", "intel", "balanco", "balanço", "resultado",
    "lucro", "prejuizo", "prejuízo", "receita", "guidance", "dividendo",
    "ipo", "fusao", "fusão", "aquisicao", "aquisição", "ibovespa",
    "petrobras", "vale", "itau", "itaú", "bitcoin", "ouro", "petroleo",
    "petróleo", "semicondutor", "inteligencia artificial",
    "inteligência artificial",
)


def relevancia(titulo, resumo=""):
    """Devolve 3, 2 ou 1 conforme o alcance do assunto."""
    texto = (titulo + " " + (resumo or "")).lower()
    if any(p in texto for p in PESO_ALTO):
        return 3
    if any(p in texto for p in PESO_MEDIO):
        return 2
    return 1


def nome_evento(titulo):
    """Nome do evento economico em portugues.

    Tenta na ordem: o nome inteiro no dicionario, depois o nome sem o sufixo
    de periodo, depois o nucleo da frase sem prefixos. Se nada bater, devolve
    o original - nome em ingles e melhor do que traducao errada de termo
    tecnico.
    """
    if not titulo:
        return titulo
    bruto = " ".join(titulo.split())
    baixo = bruto.lower()

    if baixo in AGENDA_NOMES:
        return AGENDA_NOMES[baixo]

    # separa o sufixo de periodo: "CPI m/m" -> "cpi" + " mensal"
    sufixo = ""
    for de, para in AGENDA_SUFIXOS:
        if baixo.endswith(de):
            baixo = baixo[:-len(de)].strip()
            sufixo = para
            break

    if baixo in AGENDA_NOMES:
        return AGENDA_NOMES[baixo] + sufixo

    # separa o prefixo: "Flash Manufacturing PMI" -> "preliminar: " + resto
    prefixo = ""
    for de, para in AGENDA_PREFIXOS:
        if baixo.startswith(de):
            resto = baixo[len(de):].strip()
            if resto in AGENDA_NOMES:
                return para + AGENDA_NOMES[resto] + sufixo
            prefixo = para
            baixo = resto
            break

    if baixo in AGENDA_NOMES:
        return prefixo + AGENDA_NOMES[baixo] + sufixo

    return bruto


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

    # Classifica depois de traduzir, para os termos serem encontrados no
    # titulo em portugues. Em seguida ordena por peso e, dentro do mesmo
    # peso, pelo mais recente - assim o que move o indice sobe para o topo.
    for n in unicas:
        n["peso"] = relevancia(n["titulo"], n.get("resumo"))
    unicas.sort(key=lambda n: (n["peso"], n["ts"]), reverse=True)

    return unicas
