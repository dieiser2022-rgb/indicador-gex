"""
GEX - leitor de niveis de gamma do gexmetrix.  Arquivo unico.

Instalar (uma vez):
    pip install playwright
    playwright install chromium

Usar:
    python gex.py descobrir        # etapa 1: descobre de onde vem o dado
    python gex.py coletar          # etapa 2: coleta uma vez
    python gex.py coletar --loop   # coleta a cada 15 min (alinhado em :00 :15 :30 :45)

Gera, na mesma pasta:
    resumo.txt        ranking das respostas de rede + texto da pagina
    leituras.csv      historico: ts, chave, valor_num, valor_texto
    leituras.db       o mesmo em SQLite
    estado.json       cookies/sessao (reaproveitado nas coletas)
"""
from __future__ import annotations
import argparse, csv, json, re, sqlite3, sys, time
from datetime import datetime, timezone
from pathlib import Path

URL = "https://www.gexmetrix.com/gamma_dashboard"
B = Path(__file__).resolve().parent
ESTADO, CSV_ARQ, DB_ARQ = B / "estado.json", B / "leituras.csv", B / "leituras.db"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")

ROTULOS = ["Gamma Flip", "Zero Gamma", "Flip Point", "Call Wall", "Put Wall",
           "Net GEX", "Total Gamma", "Total GEX", "Net Gamma", "Spot Price",
           "Last Price", "Spot", "Price", "Max Pain", "Max Gamma", "Regime",
           "Support", "Resistance", "Upper Bound", "Lower Bound"]
OURO = ("gamma", "gex", "flip", "wall", "strike", "exposure", "spot", "pain", "regime")
LIXO = (".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".ico", ".woff",
        ".woff2", ".ttf", ".eot", ".css", ".map")


def pw():
    try:
        from playwright.sync_api import sync_playwright
        return sync_playwright
    except ImportError:
        sys.exit("Falta o Playwright. Rode:\n  pip install playwright\n"
                 "  playwright install chromium")


def num(t):
    """'$6,123.45'->6123.45  '(1,500)'->-1500  '-1.25B'->-1.25e9  '12k'->12000"""
    if t is None:
        return None
    s = str(t).strip()
    neg = s.startswith("(") and s.endswith(")")
    s = re.sub(r"[^0-9.,\-+kKmMbB]", "", s)
    if not s:
        return None
    m = 1.0
    if s[-1] in "kK":
        m, s = 1e3, s[:-1]
    elif s[-1] in "mM":
        m, s = 1e6, s[:-1]
    elif s[-1] in "bB":
        m, s = 1e9, s[:-1]
    if "," in s and "." in s:
        s = (s.replace(".", "").replace(",", ".") if s.rfind(",") > s.rfind(".")
             else s.replace(",", ""))
    elif "," in s:
        s = s.replace(",", "") if len(s.split(",")[-1]) == 3 else s.replace(",", ".")
    try:
        v = float(s) * m
    except ValueError:
        return None
    return -v if neg else v


def achatar(o, p=""):
    r = {}
    if isinstance(o, dict):
        for k, v in o.items():
            r.update(achatar(v, f"{p}.{k}" if p else str(k)))
    elif isinstance(o, list):
        for i, v in enumerate(o[:500]):
            r.update(achatar(v, f"{p}[{i}]"))
    else:
        r[p or "valor"] = o
    return r


def extrair(texto, rotulos=ROTULOS):
    """Garimpa 'rotulo -> valor'. Rotulo longo tem prioridade (pra 'Price' nao
    roubar 'Spot Price') e o separador nao aceita hifen (senao '-1.25B' perde
    o sinal negativo)."""
    out, usado = {}, []
    for r in sorted(rotulos, key=len, reverse=True):
        pat = re.escape(r) + r"\s*[:\u2013\u2014]?\s*\$?\s*(-?\(?[\d][\d.,]*\)?\s*[kKmMbB%]?)"
        for m in re.finditer(pat, texto, re.I):
            a, z = m.span()
            if any(a < y and x < z for x, y in usado):
                continue
            usado.append((a, z))
            out[r] = m.group(1).strip()
            break
    return out


def abrir(headless=True):
    p = pw()().start()
    nav = p.chromium.launch(headless=headless,
                            args=["--disable-blink-features=AutomationControlled"])
    ctx = nav.new_context(user_agent=UA, locale="en-US",
                          viewport={"width": 1920, "height": 1080},
                          storage_state=str(ESTADO) if ESTADO.exists() else None)
    return p, nav, ctx


# --------------------------------------------------------------- descobrir
def descobrir(args):
    caps, vistos = [], set()
    p, nav, ctx = abrir(headless=args.headless)
    pg = ctx.new_page()

    def on_resp(r):
        u = r.url
        base = u.lower().split("?")[0]
        if u.startswith(("data:", "blob:")) or any(base.endswith(e) for e in LIXO):
            return
        try:
            ct = r.header_value("content-type") or ""
        except Exception:
            ct = ""
        if not ("json" in ct.lower() or "text/plain" in ct.lower()
                or "csv" in ct.lower() or (ct == "" and "/api" in base)):
            return
        k = f"{r.request.method} {u}"
        if k in vistos:
            return
        vistos.add(k)
        try:
            corpo = r.text()
        except Exception as e:
            corpo = f"<corpo ilegivel: {e}>"
        caps.append({"u": u, "m": r.request.method, "s": r.status, "ct": ct,
                     "c": corpo, "post": r.request.post_data})

    pg.on("response", on_resp)
    print(f"-> abrindo {URL}")
    try:
        pg.goto(URL, wait_until="domcontentloaded", timeout=60_000)
    except Exception as e:
        print(f"!! erro ao abrir: {e}")
    print(f"-> esperando {args.espera}s (se houver captcha, resolva na janela)")
    pg.wait_for_timeout(args.espera * 1000)
    try:
        for _ in range(4):
            pg.mouse.wheel(0, 1200)
            pg.wait_for_timeout(1000)
    except Exception:
        pass

    texto = ""
    try:
        texto = pg.inner_text("body")
        (B / "pagina.html").write_text(pg.content(), encoding="utf-8")
        pg.screenshot(path=str(B / "pagina.png"), full_page=True)
    except Exception as e:
        print(f"!! nao salvei a pagina: {e}")
    try:
        ctx.storage_state(path=str(ESTADO))
    except Exception:
        pass
    nav.close()
    p.stop()

    for c in caps:
        t = (c["c"][:200_000] + " " + c["u"]).lower()
        c["n"] = sum(t.count(w) for w in OURO) + min(
            len(re.findall(r"\b\d{3,5}(?:\.\d+)?\b", t)), 50)
    caps.sort(key=lambda c: c["n"], reverse=True)

    L = [f"Coletado: {datetime.now(timezone.utc).isoformat()}",
         f"Respostas candidatas: {len(caps)}", "",
         "RANKING (nota alta = provavel fonte dos numeros)", "=" * 72]
    amostras = B / "amostras"
    amostras.mkdir(exist_ok=True)
    for i, c in enumerate(caps, 1):
        nome = f"{i:03d}-" + re.sub(r"[^a-zA-Z0-9._-]+", "_",
                                    re.sub(r"^https?://", "", c["u"]))[:80]
        ext = ".json" if "json" in c["ct"].lower() else ".txt"
        (amostras / (nome + ext)).write_text(c["c"], encoding="utf-8")
        preview = re.sub(r"\s+", " ", c["c"][:400])
        L += ["", f"[{i:03d}] nota={c['n']} status={c['s']} {c['m']}",
              f"      url: {c['u']}", f"      tipo: {c['ct']}  bytes: {len(c['c'])}",
              f"      arquivo: amostras/{nome}{ext}",
              f"      preview: {preview}"]
        if c["post"]:
            L.append(f"      post: {str(c['post'])[:200]}")

    achados = extrair(texto)
    L += ["", "RECONHECIDO NO TEXTO DA PAGINA", "=" * 72]
    L += [f"  {k:<16} {v}" for k, v in achados.items()] or ["  (nada)"]
    L += ["", "TEXTO VISIVEL (3000 primeiros caracteres)", "=" * 72, texto[:3000]]
    (B / "resumo.txt").write_text("\n".join(L), encoding="utf-8")

    print("\n" + "=" * 64)
    if caps:
        print("TOP 5 CANDIDATOS A API:")
        for c in caps[:5]:
            print(f"  nota={c['n']:<5} {c['s']} {c['u'][:90]}")
    else:
        print("Nenhum JSON capturado -> o dado deve vir no proprio HTML.")
    print(f"\nReconhecido direto na tela: {len(achados)} niveis")
    for k, v in list(achados.items())[:12]:
        print(f"  {k:<16} {v}")
    print(f"\nDetalhes em: {B / 'resumo.txt'}")
    print("=" * 64)


# ----------------------------------------------------------------- coletar
def ler_api(url, headless=True):
    p, nav, ctx = abrir(headless)
    r = ctx.request.fetch(url, headers={"User-Agent": UA,
                                        "Accept": "application/json, text/plain, */*"})
    bruto, st = r.text(), r.status
    nav.close()
    p.stop()
    if st >= 400:
        raise RuntimeError(f"API respondeu {st}: {bruto[:200]}")
    plano = achatar(json.loads(bruto))
    return {k: v for k, v in plano.items()
            if v is None or isinstance(v, (int, float, str, bool))}, bruto


def ler_pagina(espera=25, headless=True):
    p, nav, ctx = abrir(headless)
    pg = ctx.new_page()
    pg.goto(URL, wait_until="domcontentloaded", timeout=60_000)
    pg.wait_for_timeout(espera * 1000)
    texto = pg.inner_text("body")
    try:
        ctx.storage_state(path=str(ESTADO))
    except Exception:
        pass
    nav.close()
    p.stop()
    return extrair(texto), texto


def gravar(leituras, bruto, origem):
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    brutos = B / "brutos"
    brutos.mkdir(exist_ok=True)
    (brutos / (ts.replace(":", "").replace("-", "") +
               (".json" if origem == "api" else ".txt"))).write_text(bruto, encoding="utf-8")

    novo = not CSV_ARQ.exists()
    with CSV_ARQ.open("a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if novo:
            w.writerow(["ts", "chave", "valor_num", "valor_texto", "origem"])
        for k, v in leituras.items():
            n = v if isinstance(v, (int, float)) and not isinstance(v, bool) else num(v)
            w.writerow([ts, k, "" if n is None else n, v, origem])

    con = sqlite3.connect(DB_ARQ)
    con.execute("""CREATE TABLE IF NOT EXISTS leituras(
        ts TEXT, chave TEXT, valor_num REAL, valor_texto TEXT, origem TEXT,
        PRIMARY KEY(ts, chave))""")
    with con:
        for k, v in leituras.items():
            n = v if isinstance(v, (int, float)) and not isinstance(v, bool) else num(v)
            con.execute("INSERT OR REPLACE INTO leituras VALUES(?,?,?,?,?)",
                        (ts, str(k), n, str(v), origem))
    con.close()
    return ts


def uma_coleta(args):
    if args.api:
        origem = "api"
        leituras, bruto = ler_api(args.api, args.headless)
    else:
        origem = "pagina"
        leituras, bruto = ler_pagina(args.espera, args.headless)
    if not leituras:
        print("!! nada reconhecido. Rode 'python gex.py descobrir' e veja resumo.txt")
        gravar({}, bruto, origem)
        return
    ts = gravar(leituras, bruto, origem)
    print(f"\n[{ts}] {len(leituras)} valores ({origem})")
    print("-" * 52)
    for k, v in list(leituras.items())[:40]:
        print(f"  {str(k)[:30]:<30} {str(v)[:18]}")
    print(f"\n  -> {CSV_ARQ}")


def falta(minutos):
    a = datetime.now()
    f = minutos * 60 - ((a.minute % minutos) * 60 + a.second)
    return f if f > 5 else f + minutos * 60


def coletar(args):
    if not args.loop:
        uma_coleta(args)
        return
    print(f"-> loop: a cada {args.intervalo} min. Ctrl+C para parar.")
    while True:
        try:
            uma_coleta(args)
        except KeyboardInterrupt:
            print("\n-> fim.")
            return
        except Exception as e:
            print(f"!! erro nesta rodada (continua): {e}", file=sys.stderr)
        s = falta(args.intervalo)
        print(f"-> proxima em {s/60:.1f} min")
        try:
            time.sleep(s)
        except KeyboardInterrupt:
            print("\n-> fim.")
            return


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("descobrir")
    d.add_argument("--espera", type=int, default=30)
    d.add_argument("--headless", action="store_true")
    d.set_defaults(func=descobrir)
    c = sub.add_parser("coletar")
    c.add_argument("--loop", action="store_true")
    c.add_argument("--intervalo", type=int, default=15)
    c.add_argument("--espera", type=int, default=25)
    c.add_argument("--api", default="", help="URL do JSON, se descoberta")
    c.add_argument("--janela", dest="headless", action="store_false")
    c.set_defaults(func=coletar, headless=True)
    a = ap.parse_args()
    a.func(a)


if __name__ == "__main__":
    main()
