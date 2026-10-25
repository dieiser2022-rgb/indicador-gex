"""Terminal GEX - servidor local.

Uso:
    python terminal.py

Abre o navegador em http://localhost:8777
"""

import json
import os
import threading
import types
import webbrowser
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

import exportar
import fontes
import leitura

BASE = os.path.dirname(os.path.abspath(__file__))
PORTA = 8777
CONFIG = os.path.join(BASE, "config.json")

ATIVOS = [
    ("NDX", "NQ", "NQ=F", "Nasdaq-100"),
    ("SPX", "ES", "ES=F", "S&P 500"),
    ("QQQ", "", "", "ETF Nasdaq"),
    ("SPY", "", "", "ETF S&P 500"),
]

GRAFICO_PADRAO = "NQ=F"

CORES_PADRAO = {
    "fundo": "#0b1120",
    "painel": "#111c33",
    "borda": "#1e293b",
    "texto": "#e2e8f0",
    "apagado": "#94a3b8",
    "alta": "#22c55e",
    "baixa": "#ef4444",
    # call verde e put vermelho: segue o lado da aposta, nao o papel de
    # suporte ou resistencia
    "call_wall": "#4ade80",
    "put_wall": "#f87171",
    "inversao": "#fbbf24",
    "destaque": "#38bdf8",
    "botao": "#2563eb",
}


def carregar_gamma():
    """Carrega gamma_cboe.py sem disparar a coleta dele."""
    caminho = os.path.join(BASE, "gamma_cboe.py")
    if not os.path.exists(caminho):
        raise SystemExit("gamma_cboe.py nao encontrado em " + BASE)
    texto = open(caminho, encoding="utf-8").read()
    linhas = []
    for l in texto.splitlines():
        if l.strip() == "main()":
            recuo = l[:len(l) - len(l.lstrip())]
            linhas.append(recuo + "pass")
        else:
            linhas.append(l)
    mod = types.ModuleType("gamma_cboe")
    exec(compile(chr(10).join(linhas), "gamma_cboe.py", "exec"), mod.__dict__)
    return mod


G = carregar_gamma()
G.MARGEM = 0.0
G.PASSOS = 51

CACHE = {"gamma": {}, "calendario": [], "noticias": [], "panorama": [],
         "candles": {}, "atualizado": None}
TRAVA = threading.Lock()


# ------------------------------------------------------------------- config

# cores usadas antes da troca: call vermelho e put verde
CORES_ANTIGAS = {"call_wall": "#f87171", "put_wall": "#4ade80"}

# Cada corretora chama o mesmo ativo de um jeito. Estes sao apenas sugestoes
# iniciais - o usuario ajusta no painel conforme a plataforma dele.
TICKERS_PADRAO = {
    "mt5": "USTEC",
    "tradingview": "MNQ",
    "ninjatrader": "MNQ",
}

# Em que preco a plataforma cota o ativo: no futuro ou no indice a vista.
# Importa porque a diferenca entre os dois (o basis) passa de 200 pontos no
# Nasdaq - usar a base errada desloca todos os niveis de uma vez.
# NQ, MNQ e NQ1! seguem o futuro. CFDs como USTEC dependem da corretora.
BASES_PADRAO = {
    "mt5": "futuro",
    "tradingview": "futuro",
    "ninjatrader": "futuro",
}


def ler_config():
    cfg = {"cores": dict(CORES_PADRAO), "tickers": dict(TICKERS_PADRAO),
           "bases": dict(BASES_PADRAO),
           "dias_max": 45, "grafico": GRAFICO_PADRAO}
    if os.path.exists(CONFIG):
        try:
            salvo = json.loads(open(CONFIG, encoding="utf-8").read())
            if isinstance(salvo.get("cores"), dict):
                cfg["cores"].update(salvo["cores"])
            if isinstance(salvo.get("tickers"), dict):
                cfg["tickers"].update(salvo["tickers"])
            if isinstance(salvo.get("bases"), dict):
                cfg["bases"].update({k: v for k, v in salvo["bases"].items()
                                     if k in BASES_PADRAO
                                     and v in ("futuro", "indice")})
            for chave in ("dias_max", "grafico"):
                if chave in salvo:
                    cfg[chave] = salvo[chave]
        except Exception:
            pass

    # Quem salvou as cores antes da troca tem call vermelho e put verde
    # gravado em disco, o que sobrescreveria o padrao novo. Se o arquivo tem
    # exatamente aquelas duas cores, troca. Cores escolhidas a mao nao mudam.
    if all(cfg["cores"].get(k, "").lower() == v
           for k, v in CORES_ANTIGAS.items()):
        cfg["cores"]["call_wall"] = CORES_PADRAO["call_wall"]
        cfg["cores"]["put_wall"] = CORES_PADRAO["put_wall"]

    return cfg


def gravar_config(novo):
    cfg = ler_config()
    if novo.get("reset_cores"):
        cfg["cores"] = dict(CORES_PADRAO)
    if isinstance(novo.get("cores"), dict):
        cfg["cores"].update({k: v for k, v in novo["cores"].items()
                             if k in CORES_PADRAO})
    if isinstance(novo.get("tickers"), dict):
        cfg["tickers"].update({k: str(v).strip().upper()[:24]
                               for k, v in novo["tickers"].items()
                               if k in TICKERS_PADRAO})
    if isinstance(novo.get("bases"), dict):
        cfg["bases"].update({k: v for k, v in novo["bases"].items()
                             if k in BASES_PADRAO
                             and v in ("futuro", "indice")})
    if "dias_max" in novo:
        try:
            cfg["dias_max"] = max(0, int(novo["dias_max"]))
        except (TypeError, ValueError):
            pass
    if "grafico" in novo:
        cfg["grafico"] = str(novo["grafico"])
    open(CONFIG, "w", encoding="utf-8").write(
        json.dumps(cfg, indent=2, ensure_ascii=False))
    return cfg


# -------------------------------------------------------------------- gamma

def calcular_gamma(indice, fut_nome, fut_yahoo, dias_max):
    G.DIAS_MAX = dias_max
    dados = G.baixar(indice)
    spot, todas, usaveis, com_gamma, com_oi, venc, ivm = G.analisar(dados)
    if not usaveis:
        return {"indice": indice, "dias_max": dias_max,
                "erro": ("nenhum contrato vence em " + str(dias_max)
                         + " dia(s). Escolha uma janela de vencimento maior "
                         + "no seletor acima do grafico.")}

    por_strike, call_gex, put_gex, _ = G.gex_por_strike(spot, usaveis)
    if not por_strike:
        return {"indice": indice, "erro": "nao foi possivel calcular gamma"}

    net = sum(por_strike.values())
    zg = G.achar_zero_gamma(spot, usaveis)
    cw, pw = G.paredes(spot, call_gex, put_gex)

    perto = [(k, v) for k, v in sorted(por_strike.items())
             if abs(k - spot) / spot <= 0.035]
    barras = [{"k": k, "v": v,
               "c": call_gex.get(k, 0.0), "p": put_gex.get(k, 0.0)}
              for k, v in perto]

    saida = {
        "indice": indice, "spot": spot, "net_gex": net,
        "regime": "POSITIVO" if net > 0 else "NEGATIVO",
        "zero_gamma": zg, "call_wall": cw, "put_wall": pw,
        "contratos": len(usaveis), "dias_max": dias_max,
        "barras": barras, "futuro": None,
    }

    if fut_yahoo:
        c = fontes.cotacao(fut_yahoo)
        if c and spot:
            base = c["preco"] - spot
            saida["futuro"] = {
                "nome": fut_nome, "simbolo": fut_yahoo,
                "preco": c["preco"], "pct": c["pct"], "basis": base,
                "zero_gamma": (zg + base) if zg else None,
                "call_wall": (cw + base) if cw else None,
                "put_wall": (pw + base) if pw else None,
            }
    return saida


def niveis_para_grafico(simbolo_grafico):
    """Converte os niveis de cada indice para a escala do ativo do grafico.

    NDX -> NQ e exato (basta somar o basis).
    QQQ e SPX entram por proporcao, o que e aproximado: serve de referencia
    visual, nao de nivel preciso.
    """
    gam = CACHE["gamma"]
    base_indice = "NDX" if simbolo_grafico in ("NQ=F", "^NDX") else "SPX"
    principal = gam.get(base_indice)
    if not principal or principal.get("erro") or not principal.get("spot"):
        return []

    fut = principal.get("futuro") or {}
    basis = fut.get("basis", 0.0) if simbolo_grafico.endswith("=F") else 0.0
    spot_base = principal["spot"]
    niveis = []

    def junta(origem, fator, exato):
        d = gam.get(origem)
        if not d or d.get("erro"):
            return
        for campo, rotulo, cor in (("call_wall", "CALL WALL", "call_wall"),
                                   ("put_wall", "PUT WALL", "put_wall"),
                                   ("zero_gamma", "INVERSAO", "inversao")):
            v = d.get(campo)
            if not v:
                continue
            niveis.append({
                "preco": v * fator + basis,
                "rotulo": origem + " " + rotulo,
                "cor": cor,
                "exato": exato,
            })

    junta(base_indice, 1.0, True)

    # Alem do indice principal, plota apenas o par natural do mesmo mercado
    # (o ETF equivalente). Jogar os quatro ativos no grafico daria 12 linhas
    # e viraria uma zebra ilegivel.
    par = {"NDX": "QQQ", "SPX": "SPY"}.get(base_indice)
    d = gam.get(par) if par else None
    if d and not d.get("erro") and d.get("spot"):
        junta(par, spot_base / d["spot"], False)

    niveis.sort(key=lambda n: n["preco"])
    return niveis


# ------------------------------------------------------------------ rotas

def rota_gamma(args):
    pedido = (args.get("simbolo") or [""])[0].upper()
    cfg = ler_config()
    dias = int((args.get("dias") or [cfg["dias_max"]])[0])
    for indice, fut, yh, desc in ATIVOS:
        if indice == pedido:
            try:
                r = calcular_gamma(indice, fut, yh, dias)
            except Exception as e:
                r = {"indice": indice, "erro": str(e)}
            with TRAVA:
                CACHE["gamma"][indice] = r
                CACHE["atualizado"] = datetime.now(timezone.utc).isoformat(
                    timespec="seconds")
            r = dict(r)
            r["leitura"] = leitura.leitura_mm(r)
            return r
    return {"erro": "simbolo invalido: " + pedido}


def rota_candles(args):
    simbolo = (args.get("simbolo") or [GRAFICO_PADRAO])[0]
    intervalo = (args.get("intervalo") or ["15m"])[0]
    janela = (args.get("janela") or ["5d"])[0]
    velas = fontes.candles(simbolo, intervalo, janela)
    with TRAVA:
        CACHE["candles"][simbolo] = velas
    return {"simbolo": simbolo, "intervalo": intervalo,
            "candles": velas, "niveis": niveis_para_grafico(simbolo)}


def rota_calendario(args):
    ev = fontes.calendario()
    with TRAVA:
        CACHE["calendario"] = ev
    agora = int(datetime.now(timezone.utc).timestamp())
    passados = [e for e in ev if e["ts"] <= agora]
    futuros = [e for e in ev if e["ts"] > agora]
    return {"agora": agora, "antes": passados[-3:], "depois": futuros[:3],
            "todos": ev}


def rota_noticias(args):
    n = fontes.noticias(16)
    with TRAVA:
        CACHE["noticias"] = n
    return {"noticias": n}


def rota_panorama(args):
    p = fontes.panorama()
    with TRAVA:
        CACHE["panorama"] = p
    return {"panorama": p}


def rota_morningcall(args):
    with TRAVA:
        gammas = [CACHE["gamma"].get(a[0]) for a in ATIVOS]
        mc = leitura.morning_call(CACHE["panorama"], CACHE["calendario"],
                                  CACHE["noticias"], gammas)
    return mc


def rota_exportar(args):
    """Linha de dados pronta para colar no indicador da plataforma."""
    cfg = ler_config()
    destino = (args.get("destino") or ["texto"])[0]
    simbolo = (args.get("simbolo") or [cfg["grafico"]])[0]
    ticker = cfg["tickers"].get(destino, "")
    dias = int((args.get("dias") or [cfg["dias_max"]])[0])

    indice = "NDX" if simbolo in ("NQ=F", "^NDX") else "SPX"

    try:
        dados = G.baixar(indice)
    except Exception as e:
        return {"destino": destino, "erro": "nao foi possivel baixar a CBOE: "
                + str(e)}

    calc = exportar.calcular(G, dados, dias_padrao=dias)
    if not calc:
        return {"destino": destino,
                "erro": "sem contratos usaveis para " + indice}

    # Base de preco da plataforma de destino. Quem cota o indice a vista nao
    # leva o basis; quem cota o futuro leva.
    base = cfg["bases"].get(destino, "futuro")
    basis = 0.0
    preco_futuro = None
    if simbolo.endswith("=F"):
        c = fontes.cotacao(simbolo)
        if c and calc["spot"]:
            preco_futuro = c["preco"]
            if base == "futuro":
                basis = c["preco"] - calc["spot"]

    # Niveis do ativo irmao do mesmo mercado. Aproveita o que o painel ja
    # calculou em vez de baixar de novo: sao 4 a 13 MB por ativo.
    nome_par = {"NDX": "QQQ", "SPX": "SPY"}.get(indice)
    par = None
    with TRAVA:
        bruto = CACHE["gamma"].get(nome_par) if nome_par else None
    if bruto and not bruto.get("erro") and bruto.get("spot"):
        par = {"nome": nome_par, "spot": bruto["spot"],
               "call_wall": bruto.get("call_wall"),
               "put_wall": bruto.get("put_wall"),
               "zero_gamma": bruto.get("zero_gamma")}

    linha, valores = exportar.montar(ticker, calc, basis=basis, par=par)

    with TRAVA:
        CACHE["exportado"] = {"linha": linha, "quando":
                              datetime.now(timezone.utc).isoformat(timespec="seconds")}

    aviso = ""
    if not calc["tem_0dte"]:
        aviso = ("Nenhum contrato vence hoje, entao os campos 0DTE ficaram de "
                 "fora da linha. Normal em fim de semana e depois do "
                 "fechamento.")

    return {
        "destino": destino, "simbolo": simbolo, "indice": indice,
        "ticker": ticker, "linha": linha, "valores": valores,
        "spot": calc["spot"], "basis": basis, "iv": calc["iv"],
        "base": base, "preco_futuro": preco_futuro,
        "contratos": calc["contratos"], "contratos_0dte": calc["contratos_0dte"],
        "dias": dias, "niveis": niveis_para_grafico(simbolo),
        "par": (par or {}).get("nome", ""),
        "pronto": True, "aviso": aviso,
    }


ROTAS = {
    "/api/gamma": rota_gamma,
    "/api/candles": rota_candles,
    "/api/calendario": rota_calendario,
    "/api/noticias": rota_noticias,
    "/api/panorama": rota_panorama,
    "/api/morningcall": rota_morningcall,
    "/api/exportar": rota_exportar,
}


class Handler(BaseHTTPRequestHandler):

    def log_message(self, formato, *args):
        pass

    def _envia(self, codigo, corpo, tipo):
        dados = corpo.encode("utf-8") if isinstance(corpo, str) else corpo
        self.send_response(codigo)
        self.send_header("Content-Type", tipo + "; charset=utf-8")
        self.send_header("Content-Length", str(len(dados)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(dados)

    def _json(self, obj, codigo=200):
        self._envia(codigo, json.dumps(obj, ensure_ascii=False), "application/json")

    def do_GET(self):
        url = urlparse(self.path)
        caminho = url.path
        args = parse_qs(url.query)

        if caminho in ("/", "/index.html"):
            arq = os.path.join(BASE, "painel.html")
            if not os.path.exists(arq):
                self._envia(500, "painel.html nao encontrado", "text/plain")
                return
            self._envia(200, open(arq, encoding="utf-8").read(), "text/html")
            return

        if caminho == "/api/config":
            self._json(ler_config())
            return

        if caminho == "/api/estado":
            with TRAVA:
                self._json({"atualizado": CACHE["atualizado"],
                            "ativos": list(CACHE["gamma"].keys())})
            return

        fn = ROTAS.get(caminho)
        if fn:
            nome = caminho.split("/")[-1]
            print("  >", nome, args.get("simbolo", [""])[0])
            try:
                self._json(fn(args))
            except Exception as e:
                self._json({"erro": str(e)}, 200)
            return

        self._envia(404, "nao encontrado", "text/plain")

    def do_POST(self):
        url = urlparse(self.path)
        if url.path != "/api/config":
            self._envia(404, "nao encontrado", "text/plain")
            return
        tamanho = int(self.headers.get("Content-Length") or 0)
        bruto = self.rfile.read(tamanho).decode("utf-8") if tamanho else "{}"
        try:
            novo = json.loads(bruto)
        except json.JSONDecodeError:
            self._json({"erro": "json invalido"}, 400)
            return
        self._json(gravar_config(novo))


def main():
    endereco = "http://localhost:" + str(PORTA)
    servidor = ThreadingHTTPServer(("127.0.0.1", PORTA), Handler)
    print("Terminal GEX no ar em", endereco)
    print("para parar: CTRL+C")
    threading.Timer(1.0, lambda: webbrowser.open(endereco)).start()
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("")
        print("encerrado.")


if __name__ == "__main__":
    main()
