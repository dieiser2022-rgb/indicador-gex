import json
import os
import threading
import types
import urllib.request
import webbrowser
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer

BASE = os.path.dirname(os.path.abspath(__file__))


def carregar_gamma():
    # Aproveita as funcoes do gamma_cboe.py sem disparar a coleta dele.
    # Funciona do jeito que o arquivo estiver: com main() solto no fim
    # ou protegido por if __name__ == "__main__".
    caminho = os.path.join(BASE, "gamma_cboe.py")
    if not os.path.exists(caminho):
        raise SystemExit("gamma_cboe.py nao encontrado na pasta " + BASE)
    texto = open(caminho, encoding="utf-8").read()
    uteis = []
    for linha in texto.splitlines():
        if linha.strip() == "main()":
            # troca por pass em vez de apagar: se a linha estiver dentro
            # de um if, apagar deixaria o bloco vazio e quebraria
            recuo = linha[:len(linha) - len(linha.lstrip())]
            uteis.append(recuo + "pass")
        else:
            uteis.append(linha)
    mod = types.ModuleType("gamma_cboe")
    exec(compile(chr(10).join(uteis), "gamma_cboe.py", "exec"), mod.__dict__)
    return mod


G = carregar_gamma()

PORTA = 8777

# sem margem: assim o Put Wall bate com a convencao dos sites de referencia
G.MARGEM = 0.0
G.PASSOS = 61

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/131.0.0.0 Safari/537.36"

# indice da CBOE -> futuro equivalente no Yahoo
ATIVOS = [
    ("NDX", "NQ", "NQ%3DF", "Nasdaq-100"),
    ("SPX", "ES", "ES%3DF", "S&P 500"),
    ("QQQ", "", "", "ETF Nasdaq"),
    ("SPY", "", "", "ETF S&P 500"),
]


def preco_yahoo(simbolo):
    url = ("https://query1.finance.yahoo.com/v8/finance/chart/" + simbolo
           + "?interval=15m&range=1d")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=30) as r:
            d = json.loads(r.read().decode("utf-8", "ignore"))
        res = d.get("chart", {}).get("result")
        if not res:
            return None
        q = (res[0].get("indicators", {}).get("quote") or [{}])[0]
        fech = [x for x in (q.get("close") or []) if x]
        return float(fech[-1]) if fech else None
    except Exception:
        return None


def calcular(indice, fut_nome, fut_yahoo):
    dados = G.baixar(indice)
    spot, todas, usaveis, com_gamma, com_oi, venc, ivm = G.analisar(dados)
    if not usaveis:
        return {"erro": "sem contratos usaveis para " + indice}

    por_strike, call_gex, put_gex, _ = G.gex_por_strike(spot, usaveis)
    if not por_strike:
        return {"erro": "nao foi possivel calcular gamma de " + indice}

    net = sum(por_strike.values())
    zg = G.achar_zero_gamma(spot, usaveis)
    cw, pw = G.paredes(spot, call_gex, put_gex)

    strikes = sorted(por_strike.items(), key=lambda kv: kv[0])
    perto = [kv for kv in strikes if abs(kv[0] - spot) / spot <= 0.04]
    barras = [{"k": k, "v": v} for k, v in perto]

    saida = {
        "indice": indice,
        "spot": spot,
        "net_gex": net,
        "regime": "POSITIVO" if net > 0 else "NEGATIVO",
        "zero_gamma": zg,
        "call_wall": cw,
        "put_wall": pw,
        "contratos": len(usaveis),
        "barras": barras,
        "futuro": None,
    }

    if fut_yahoo:
        pf = preco_yahoo(fut_yahoo)
        if pf and spot:
            base = pf - spot
            saida["futuro"] = {
                "nome": fut_nome,
                "preco": pf,
                "basis": base,
                "zero_gamma": (zg + base) if zg else None,
                "call_wall": (cw + base) if cw else None,
                "put_wall": (pw + base) if pw else None,
            }
    return saida


PAGINA = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<title>Terminal GEX</title>
<style>
 * { box-sizing: border-box; }
 body { margin:0; background:#0b1120; color:#e2e8f0;
        font-family: Segoe UI, Arial, sans-serif; }
 header { padding:18px 24px; border-bottom:1px solid #1e293b;
          display:flex; align-items:center; gap:20px; flex-wrap:wrap; }
 h1 { margin:0; font-size:20px; letter-spacing:1px; }
 #atualizar { background:#2563eb; color:#fff; border:0; border-radius:10px;
              padding:16px 34px; font-size:17px; font-weight:bold; cursor:pointer; }
 #atualizar:hover { background:#1d4ed8; }
 #atualizar:disabled { background:#334155; cursor:wait; }
 #status { color:#94a3b8; font-size:14px; }
 .grade { display:grid; gap:16px; padding:20px 24px;
          grid-template-columns: repeat(auto-fit, minmax(330px, 1fr)); }
 .card { background:#111c33; border:1px solid #1e293b; border-radius:12px;
         padding:16px 18px; }
 .topo { display:flex; justify-content:space-between; align-items:baseline; }
 .tic { font-size:22px; font-weight:bold; }
 .sub { color:#64748b; font-size:12px; }
 .tag { font-size:11px; font-weight:bold; padding:4px 9px; border-radius:20px; }
 .neg { background:#7f1d1d; color:#fecaca; }
 .pos { background:#14532d; color:#bbf7d0; }
 .linha { display:flex; justify-content:space-between; padding:6px 0;
          border-bottom:1px solid #16213a; font-size:14px; }
 .rot { color:#94a3b8; }
 .val { font-weight:bold; font-variant-numeric: tabular-nums; }
 .cw { color:#f87171; } .pw { color:#4ade80; }
 .zg { color:#fbbf24; } .sp { color:#e2e8f0; }
 .fut { margin-top:12px; padding-top:10px; border-top:1px dashed #334155; }
 .barras { margin-top:14px; }
 .bl { display:flex; align-items:center; gap:6px; height:17px;
       font-size:11px; font-variant-numeric: tabular-nums; }
 .bl .kk { width:62px; text-align:right; color:#94a3b8; }
 .bl .zona { flex:1; display:flex; align-items:center; }
 .bl .meio { width:1px; background:#475569; height:17px; }
 .bar { height:9px; border-radius:2px; }
 .bpos { background:#22c55e; } .bneg { background:#ef4444; }
 .aqui { outline:1px solid #38bdf8; border-radius:3px; }
 footer { padding:10px 24px 30px; color:#475569; font-size:12px; }
</style>
</head>
<body>
<header>
  <h1>TERMINAL GEX</h1>
  <button id="atualizar">ATUALIZAR REGIOES</button>
  <span id="status">clique para buscar os dados</span>
</header>
<div class="grade" id="grade"></div>
<footer>
  Dados de opcoes: CBOE (atraso de ~15 min). Precos de futuros: Yahoo Finance.
  Niveis calculados localmente. Nao e recomendacao de investimento.
</footer>

<script>
const ATIVOS = ["NDX", "SPX", "QQQ", "SPY"];

function fmt(v, dec) {
  if (v === null || v === undefined) return "N/A";
  return Number(v).toLocaleString("pt-BR",
    {minimumFractionDigits: dec, maximumFractionDigits: dec});
}

function bi(v) {
  if (v === null || v === undefined) return "N/A";
  const a = Math.abs(v);
  if (a >= 1e9) return (v/1e9).toFixed(2) + " B";
  if (a >= 1e6) return (v/1e6).toFixed(0) + " M";
  if (a >= 1e3) return (v/1e3).toFixed(0) + " K";
  return v.toFixed(0);
}

function barras(d) {
  if (!d.barras || !d.barras.length) return "";
  let maior = 0;
  for (const b of d.barras) maior = Math.max(maior, Math.abs(b.v));
  if (maior <= 0) return "";
  let h = '<div class="barras">';
  const ordenado = d.barras.slice().sort((a,b) => b.k - a.k);
  for (const b of ordenado) {
    const larg = Math.abs(b.v) / maior * 46;
    const pos = b.v > 0;
    const perto = Math.abs(b.k - d.spot) / d.spot < 0.0015;
    h += '<div class="bl' + (perto ? ' aqui' : '') + '">';
    h += '<span class="kk">' + fmt(b.k, 0) + '</span>';
    h += '<span class="zona">';
    h += pos ? '<span style="flex:1"></span><span class="meio"></span>'
             : '<span style="flex:1;display:flex;justify-content:flex-end">'
               + '<span class="bar bneg" style="width:' + larg + '%"></span></span>'
               + '<span class="meio"></span>';
    h += pos ? '<span class="bar bpos" style="width:' + larg + '%"></span>' : '';
    h += '</span></div>';
  }
  return h + '</div>';
}

function card(d) {
  if (d.erro) {
    return '<div class="card"><div class="tic">' + d.indice +
           '</div><div class="sub">' + d.erro + '</div></div>';
  }
  const dec = d.spot > 2000 ? 0 : 2;
  let h = '<div class="card"><div class="topo"><div>';
  h += '<div class="tic">' + d.indice + '</div>';
  h += '<div class="sub">' + d.contratos + ' contratos</div></div>';
  h += '<span class="tag ' + (d.regime === "POSITIVO" ? "pos" : "neg") + '">GAMA ' +
       d.regime + '</span></div>';
  h += '<div class="linha"><span class="rot">Spot</span><span class="val sp">' +
       fmt(d.spot, dec) + '</span></div>';
  h += '<div class="linha"><span class="rot">Inversao gama</span><span class="val zg">' +
       fmt(d.zero_gamma, dec) + '</span></div>';
  h += '<div class="linha"><span class="rot">Parede de call</span><span class="val cw">' +
       fmt(d.call_wall, dec) + '</span></div>';
  h += '<div class="linha"><span class="rot">Parede de put</span><span class="val pw">' +
       fmt(d.put_wall, dec) + '</span></div>';
  h += '<div class="linha"><span class="rot">GEX liquido</span><span class="val">US$ ' +
       bi(d.net_gex) + '</span></div>';

  if (d.futuro) {
    const f = d.futuro;
    h += '<div class="fut"><div class="topo"><div class="tic" style="font-size:17px">' +
         f.nome + '</div><div class="sub">basis ' + fmt(f.basis, 2) + '</div></div>';
    h += '<div class="linha"><span class="rot">Preco</span><span class="val sp">' +
         fmt(f.preco, 2) + '</span></div>';
    h += '<div class="linha"><span class="rot">Inversao gama</span><span class="val zg">' +
         fmt(f.zero_gamma, 0) + '</span></div>';
    h += '<div class="linha"><span class="rot">Parede de call</span><span class="val cw">' +
         fmt(f.call_wall, 0) + '</span></div>';
    h += '<div class="linha"><span class="rot">Parede de put</span><span class="val pw">' +
         fmt(f.put_wall, 0) + '</span></div></div>';
  }
  h += barras(d);
  return h + '</div>';
}

const botao = document.getElementById("atualizar");
const status = document.getElementById("status");
const grade = document.getElementById("grade");

async function atualizar() {
  botao.disabled = true;
  grade.innerHTML = "";
  const t0 = Date.now();
  for (let i = 0; i < ATIVOS.length; i++) {
    const a = ATIVOS[i];
    status.textContent = "buscando " + a + " ... (" + (i+1) + " de " +
                         ATIVOS.length + ")";
    try {
      const r = await fetch("/api/dados?simbolo=" + a);
      const d = await r.json();
      grade.insertAdjacentHTML("beforeend", card(d));
    } catch (e) {
      grade.insertAdjacentHTML("beforeend",
        '<div class="card"><div class="tic">' + a +
        '</div><div class="sub">falhou: ' + e + '</div></div>');
    }
  }
  const seg = ((Date.now() - t0)/1000).toFixed(1);
  const agora = new Date().toLocaleTimeString("pt-BR");
  status.textContent = "atualizado as " + agora + " (levou " + seg + "s)";
  botao.disabled = false;
}

botao.addEventListener("click", atualizar);
atualizar();
</script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):

    def log_message(self, formato, *args):
        pass

    def responder(self, codigo, corpo, tipo):
        dados = corpo.encode("utf-8")
        self.send_response(codigo)
        self.send_header("Content-Type", tipo + "; charset=utf-8")
        self.send_header("Content-Length", str(len(dados)))
        self.end_headers()
        self.wfile.write(dados)

    def do_GET(self):
        caminho = self.path.split("?")[0]

        if caminho == "/":
            self.responder(200, PAGINA, "text/html")
            return

        if caminho == "/api/dados":
            pedido = ""
            if "simbolo=" in self.path:
                pedido = self.path.split("simbolo=")[1].split("&")[0].upper()
            escolhido = None
            for indice, fut, yh, desc in ATIVOS:
                if indice == pedido:
                    escolhido = (indice, fut, yh)
                    break
            if not escolhido:
                self.responder(400, json.dumps({"erro": "simbolo invalido"}),
                               "application/json")
                return
            print("  calculando", pedido, "...")
            try:
                r = calcular(escolhido[0], escolhido[1], escolhido[2])
            except Exception as e:
                r = {"indice": pedido, "erro": str(e)}
            self.responder(200, json.dumps(r), "application/json")
            return

        self.responder(404, "nao encontrado", "text/plain")


def main():
    endereco = "http://localhost:" + str(PORTA)
    servidor = HTTPServer(("127.0.0.1", PORTA), Handler)
    print("terminal no ar em", endereco)
    print("abrindo o navegador... (para parar, feche esta janela ou CTRL+C)")
    threading.Timer(1.0, lambda: webbrowser.open(endereco)).start()
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("")
        print("encerrado.")


if __name__ == "__main__":
    main()
