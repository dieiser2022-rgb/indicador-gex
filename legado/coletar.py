"""
PASSO 2 - O COLETOR
====================

Le os niveis de gamma e guarda o historico. Funciona em dois modos:

  modo "pagina"  -> abre o site num navegador e le os numeros da tela.
                    Funciona sem saber nada da API. E o padrao.

  modo "api"     -> chama direto o endpoint JSON que o descobrir.py achou.
                    Muito mais rapido e estavel. Prefira este quando souber a URL.

Como usar:
    python coletar.py                 # coleta uma vez e mostra na tela
    python coletar.py --loop          # fica rodando, coleta a cada 15 min
    python coletar.py --intervalo 5   # muda o intervalo (minutos)
    python coletar.py --silencioso    # sem prints, bom pra cron

Onde os dados ficam:
    dados/leituras.csv        -> uma linha por (horario, nome do nivel, valor)
    dados/leituras.db         -> mesmo conteudo em SQLite, pra consultar com SQL
    dados/brutos/*.json       -> snapshot cru de cada coleta (auditoria)
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parent
CONFIG = BASE / "config.json"
ESTADO = BASE / "estado.json"
DADOS = BASE / "dados"
BRUTOS = DADOS / "brutos"
CSV_ARQ = DADOS / "leituras.csv"
DB_ARQ = DADOS / "leituras.db"

UA_REAL = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)

CONFIG_PADRAO = {
    "modo": "pagina",
    "url_pagina": "https://www.gexmetrix.com/gamma_dashboard",
    "url_api": "",
    "metodo_api": "GET",
    "headers_api": {},
    "api_via_navegador": True,
    "espera_segundos": 25,
    "headless": True,
    "rotulos": [
        "Gamma Flip", "Zero Gamma", "Flip Point",
        "Call Wall", "Put Wall",
        "Net GEX", "Total Gamma", "Total GEX", "Net Gamma",
        "Spot", "Spot Price", "Last Price", "Price",
        "Max Pain", "Max Gamma", "Regime",
        "Support", "Resistance",
        "Upper Bound", "Lower Bound",
    ],
}


# ----------------------------------------------------------------- utilidades

def carregar_config() -> dict:
    cfg = dict(CONFIG_PADRAO)
    if CONFIG.exists():
        try:
            cfg.update(json.loads(CONFIG.read_text(encoding="utf-8")))
        except json.JSONDecodeError as e:
            sys.exit(f"config.json invalido: {e}")
    else:
        CONFIG.write_text(json.dumps(CONFIG_PADRAO, indent=2, ensure_ascii=False),
                          encoding="utf-8")
        print(f"-> criei um {CONFIG.name} com os valores padrao. Pode editar.")
    return cfg


def agora_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def para_numero(txt: str):
    """'$6,123.45' -> 6123.45 ; '-2.3%' -> -2.3 ; 'Positive' -> None"""
    if txt is None:
        return None
    s = str(txt).strip()
    neg = s.startswith("(") and s.endswith(")")
    s = re.sub(r"[^0-9.,\-+kKmMbB]", "", s)
    if not s:
        return None
    mult = 1.0
    if s and s[-1] in "kK":
        mult, s = 1e3, s[:-1]
    elif s and s[-1] in "mM":
        mult, s = 1e6, s[:-1]
    elif s and s[-1] in "bB":
        mult, s = 1e9, s[:-1]
    # 1.234,56 (pt) vs 1,234.56 (en)
    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "," in s:
        s = s.replace(",", "") if len(s.split(",")[-1]) == 3 else s.replace(",", ".")
    try:
        v = float(s) * mult
    except ValueError:
        return None
    return -v if neg else v


def achatar(obj, prefixo: str = "") -> dict:
    """{'a': {'b': 1}, 'c': [2,3]} -> {'a.b': 1, 'c[0]': 2, 'c[1]': 3}"""
    saida: dict = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            saida.update(achatar(v, f"{prefixo}.{k}" if prefixo else str(k)))
    elif isinstance(obj, list):
        for i, v in enumerate(obj[:500]):
            saida.update(achatar(v, f"{prefixo}[{i}]"))
    else:
        saida[prefixo or "valor"] = obj
    return saida


# ------------------------------------------------------------------- captura

def ler_via_api(cfg: dict) -> tuple[dict, str]:
    """Chama o endpoint JSON. Retorna (leituras, texto_bruto)."""
    url = cfg.get("url_api") or ""
    if not url:
        raise RuntimeError("modo 'api' exige 'url_api' no config.json")

    metodo = (cfg.get("metodo_api") or "GET").upper()
    headers = {"User-Agent": UA_REAL, "Accept": "application/json, text/plain, */*"}
    headers.update(cfg.get("headers_api") or {})

    if cfg.get("api_via_navegador", True):
        # passa pelo navegador: herda cookies e driblar Cloudflare fica mais facil
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            nav = p.chromium.launch(headless=cfg.get("headless", True))
            ctx = nav.new_context(
                user_agent=UA_REAL,
                storage_state=str(ESTADO) if ESTADO.exists() else None,
            )
            resp = ctx.request.fetch(url, method=metodo, headers=headers)
            bruto = resp.text()
            status = resp.status
            nav.close()
        if status >= 400:
            raise RuntimeError(f"API respondeu {status}: {bruto[:200]}")
    else:
        import requests
        r = requests.request(metodo, url, headers=headers, timeout=30)
        r.raise_for_status()
        bruto = r.text

    dados = json.loads(bruto)
    plano = achatar(dados)
    leituras = {k: v for k, v in plano.items()
                if isinstance(v, (int, float, str, bool)) or v is None}
    return leituras, bruto


def ler_via_pagina(cfg: dict) -> tuple[dict, str]:
    """Abre o dashboard e garimpa 'rotulo -> numero' do texto da tela."""
    from playwright.sync_api import sync_playwright

    url = cfg.get("url_pagina")
    with sync_playwright() as p:
        nav = p.chromium.launch(
            headless=cfg.get("headless", True),
            args=["--disable-blink-features=AutomationControlled"],
        )
        ctx = nav.new_context(
            user_agent=UA_REAL,
            viewport={"width": 1920, "height": 1080},
            locale="en-US",
            storage_state=str(ESTADO) if ESTADO.exists() else None,
        )
        pg = ctx.new_page()
        pg.goto(url, wait_until="domcontentloaded", timeout=60_000)
        pg.wait_for_timeout(int(cfg.get("espera_segundos", 25)) * 1000)
        texto = pg.inner_text("body")
        try:
            ctx.storage_state(path=str(ESTADO))
        except Exception:
            pass
        nav.close()

    return extrair_rotulos(texto, cfg.get("rotulos", [])), texto


def extrair_rotulos(texto: str, rotulos: list) -> dict:
    """Garimpa 'rotulo -> numero' de um texto solto.

    Dois cuidados importantes:
      1) o separador aceita ':' e travessao, mas NAO hifen simples, senao
         'Net GEX -1.25B' perderia o sinal negativo;
      2) rotulos mais longos sao testados primeiro e as posicoes casadas
         ficam reservadas, pra 'Price' nao roubar o valor de 'Spot Price'.
    """
    leituras: dict = {}
    ocupado: list[tuple[int, int]] = []

    for rotulo in sorted(rotulos, key=len, reverse=True):
        padrao = (
            re.escape(rotulo)
            + r"\s*[:\u2013\u2014]?\s*\$?\s*(-?\(?[\d][\d.,]*\)?\s*[kKmMbB%]?)"
        )
        for m in re.finditer(padrao, texto, flags=re.IGNORECASE):
            ini, fim = m.span()
            if any(ini < o_fim and o_ini < fim for o_ini, o_fim in ocupado):
                continue  # esse trecho do texto ja pertence a um rotulo maior
            ocupado.append((ini, fim))
            # guarda o texto cru; a conversao pra numero acontece na gravacao
            leituras[rotulo] = m.group(1).strip()
            break

    return leituras


# ---------------------------------------------------------------- persistencia

def iniciar_db() -> sqlite3.Connection:
    DADOS.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_ARQ)
    con.execute("""
        CREATE TABLE IF NOT EXISTS leituras (
            ts          TEXT NOT NULL,
            chave       TEXT NOT NULL,
            valor_num   REAL,
            valor_texto TEXT,
            origem      TEXT,
            PRIMARY KEY (ts, chave)
        )
    """)
    con.execute("CREATE INDEX IF NOT EXISTS idx_chave ON leituras(chave)")
    con.commit()
    return con


def gravar(leituras: dict, bruto: str, origem: str) -> str:
    ts = agora_iso()
    DADOS.mkdir(parents=True, exist_ok=True)
    BRUTOS.mkdir(parents=True, exist_ok=True)

    # snapshot cru
    carimbo = ts.replace(":", "").replace("-", "")
    ext = "json" if origem == "api" else "txt"
    (BRUTOS / f"{carimbo}.{ext}").write_text(bruto, encoding="utf-8")

    # csv formato longo (nunca quebra se o site mudar de colunas)
    novo = not CSV_ARQ.exists()
    with CSV_ARQ.open("a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if novo:
            w.writerow(["ts", "chave", "valor_num", "valor_texto", "origem"])
        for k, v in leituras.items():
            num = v if isinstance(v, (int, float)) and not isinstance(v, bool) else para_numero(v)
            w.writerow([ts, k, num if num is not None else "", v, origem])

    # sqlite
    con = iniciar_db()
    with con:
        for k, v in leituras.items():
            num = v if isinstance(v, (int, float)) and not isinstance(v, bool) else para_numero(v)
            con.execute(
                "INSERT OR REPLACE INTO leituras VALUES (?,?,?,?,?)",
                (ts, str(k), num, str(v), origem),
            )
    con.close()
    return ts


# -------------------------------------------------------------------- execucao

def coletar_uma_vez(cfg: dict, silencioso: bool = False) -> dict:
    modo = cfg.get("modo", "pagina")
    if modo == "api":
        leituras, bruto = ler_via_api(cfg)
    elif modo == "pagina":
        leituras, bruto = ler_via_pagina(cfg)
    else:
        raise RuntimeError(f"modo desconhecido: {modo}")

    if not leituras:
        if not silencioso:
            print("!! nenhum valor reconhecido.")
            print("   Rode 'python descobrir.py' e ajuste 'rotulos' no config.json")
        gravar({}, bruto, modo)
        return {}

    ts = gravar(leituras, bruto, modo)
    if not silencioso:
        print(f"\n[{ts}]  modo={modo}  {len(leituras)} valores")
        print("-" * 56)
        for k, v in list(leituras.items())[:40]:
            print(f"  {str(k)[:34]:<34} {str(v)[:20]}")
        if len(leituras) > 40:
            print(f"  ... e mais {len(leituras) - 40}")
        print(f"\n  -> {CSV_ARQ}")
    return leituras


def segundos_ate_proximo(intervalo_min: int) -> float:
    """Alinha no relogio: :00, :15, :30, :45 para intervalo de 15."""
    agora = datetime.now()
    passados = (agora.minute % intervalo_min) * 60 + agora.second
    falta = intervalo_min * 60 - passados
    return falta if falta > 5 else falta + intervalo_min * 60


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--loop", action="store_true", help="repetir pra sempre")
    ap.add_argument("--intervalo", type=int, default=15, help="minutos entre coletas")
    ap.add_argument("--silencioso", action="store_true", help="sem prints")
    ap.add_argument("--modo", choices=["pagina", "api"], help="sobrescreve o config")
    args = ap.parse_args()

    cfg = carregar_config()
    if args.modo:
        cfg["modo"] = args.modo

    if not args.loop:
        try:
            coletar_uma_vez(cfg, args.silencioso)
            return 0
        except Exception as e:
            print(f"!! erro: {e}", file=sys.stderr)
            return 1

    if not args.silencioso:
        print(f"-> loop ativo: coletando a cada {args.intervalo} min. Ctrl+C para parar.")
    while True:
        try:
            coletar_uma_vez(cfg, args.silencioso)
        except KeyboardInterrupt:
            print("\n-> encerrado.")
            return 0
        except Exception as e:
            print(f"!! erro nesta rodada (segue tentando): {e}", file=sys.stderr)

        espera = segundos_ate_proximo(args.intervalo)
        if not args.silencioso:
            prox = datetime.now().timestamp() + espera
            print(f"-> proxima coleta em {espera/60:.1f} min "
                  f"({datetime.fromtimestamp(prox).strftime('%H:%M:%S')})")
        try:
            time.sleep(espera)
        except KeyboardInterrupt:
            print("\n-> encerrado.")
            return 0


if __name__ == "__main__":
    raise SystemExit(main())
