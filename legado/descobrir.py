"""
PASSO 1 - O DETETIVE
=====================

Abre o dashboard em um navegador de verdade e espiona TODO o trafego de rede.
O objetivo e descobrir DE ONDE a pagina puxa os numeros de gamma.

Quase todo dashboard moderno nao tem os numeros escritos no HTML: ele chama
um endereco que devolve JSON e desenha os graficos com JavaScript. Se a gente
achar esse endereco, a coleta fica trivial e muito mais estavel.

Como usar:
    python descobrir.py                 # abre o navegador na sua tela (recomendado)
    python descobrir.py --headless      # sem janela, pode ser bloqueado
    python descobrir.py --espera 45     # espera mais tempo pela pagina carregar

O que ele gera na pasta 'amostras/':
    - resumo.txt          -> ranking dos candidatos mais promissores
    - pagina.html         -> o HTML final renderizado
    - pagina.txt          -> todo o texto visivel da pagina
    - pagina.png          -> screenshot
    - NNN-*.json/.txt     -> corpo de cada resposta de rede capturada
    - ../estado.json      -> cookies/sessao, reaproveitados pelo coletor
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sys.exit(
        "Playwright nao instalado. Rode:\n"
        "    pip install -r requirements.txt\n"
        "    playwright install chromium"
    )

URL = "https://www.gexmetrix.com/gamma_dashboard"

BASE = Path(__file__).resolve().parent
AMOSTRAS = BASE / "amostras"
ESTADO = BASE / "estado.json"

# Extensoes que com certeza nao tem dado util (imagem, fonte, estilo).
IGNORAR_EXT = (
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".ico",
    ".woff", ".woff2", ".ttf", ".eot", ".css", ".map",
)

# Palavras que, se aparecerem no CORPO da resposta, indicam dado de gamma.
PALAVRAS_OURO = (
    "gamma", "gex", "flip", "call_wall", "callwall", "call wall",
    "put_wall", "putwall", "put wall", "strike", "exposure",
    "net_gex", "netgex", "spot", "max_pain", "maxpain", "regime",
)

UA_REAL = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)


def eh_candidato(url: str, content_type: str) -> bool:
    """Decide se vale a pena baixar e guardar o corpo dessa resposta."""
    u = url.lower().split("?")[0]
    if any(u.endswith(ext) for ext in IGNORAR_EXT):
        return False
    if url.startswith("data:") or url.startswith("blob:"):
        return False
    ct = content_type.lower()
    if "json" in ct or "text/plain" in ct or "csv" in ct:
        return True
    # XHR que devolve texto sem content-type claro
    if ct == "" and "/api" in u:
        return True
    return False


def pontuar(corpo: str, url: str) -> int:
    """Nota de 0 pra cima: quanto mais palavras de gamma, mais promissor."""
    texto = (corpo[:200_000] + " " + url).lower()
    nota = sum(texto.count(p) for p in PALAVRAS_OURO)
    # numeros com cara de preco/strike ajudam
    nota += min(len(re.findall(r"\b\d{3,5}(?:\.\d+)?\b", texto)), 50)
    return nota


def slug(url: str) -> str:
    s = re.sub(r"^https?://", "", url)
    s = re.sub(r"[^a-zA-Z0-9._-]+", "_", s)
    return s[:90]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default=URL, help="pagina a inspecionar")
    ap.add_argument("--headless", action="store_true", help="rodar sem janela")
    ap.add_argument("--espera", type=int, default=30,
                    help="segundos esperando a pagina terminar de carregar")
    args = ap.parse_args()

    AMOSTRAS.mkdir(parents=True, exist_ok=True)

    capturas: list[dict] = []
    vistos: set[str] = set()

    with sync_playwright() as p:
        navegador = p.chromium.launch(
            headless=args.headless,
            args=["--disable-blink-features=AutomationControlled"],
        )
        contexto = navegador.new_context(
            user_agent=UA_REAL,
            viewport={"width": 1920, "height": 1080},
            locale="en-US",
        )
        pagina = contexto.new_page()

        def ao_responder(resposta):
            url = resposta.url
            try:
                ct = resposta.header_value("content-type") or ""
            except Exception:
                ct = ""
            if not eh_candidato(url, ct):
                return
            chave = f"{resposta.request.method} {url}"
            if chave in vistos:
                return
            vistos.add(chave)
            try:
                corpo = resposta.text()
            except Exception as e:
                corpo = f"<nao foi possivel ler o corpo: {e}>"
            capturas.append({
                "metodo": resposta.request.method,
                "url": url,
                "status": resposta.status,
                "content_type": ct,
                "tamanho": len(corpo),
                "corpo": corpo,
                "request_headers": dict(resposta.request.headers),
                "post_data": resposta.request.post_data,
            })

        pagina.on("response", ao_responder)

        print(f"-> abrindo {args.url}")
        try:
            pagina.goto(args.url, wait_until="domcontentloaded", timeout=60_000)
        except Exception as e:
            print(f"!! erro ao abrir: {e}")

        print(f"-> esperando {args.espera}s (deixe o grafico carregar; "
              f"se aparecer captcha, resolva agora na janela)")
        pagina.wait_for_timeout(args.espera * 1000)

        # rolar a pagina pode disparar carregamentos preguicosos
        try:
            for _ in range(4):
                pagina.mouse.wheel(0, 1200)
                pagina.wait_for_timeout(1200)
        except Exception:
            pass

        # salvar o estado da pagina
        try:
            (AMOSTRAS / "pagina.html").write_text(pagina.content(), encoding="utf-8")
            texto = pagina.inner_text("body")
            (AMOSTRAS / "pagina.txt").write_text(texto, encoding="utf-8")
            pagina.screenshot(path=str(AMOSTRAS / "pagina.png"), full_page=True)
            print(f"-> HTML, texto e screenshot salvos em {AMOSTRAS}")
        except Exception as e:
            print(f"!! nao consegui salvar o estado da pagina: {e}")
            texto = ""

        # guardar cookies/sessao para o coletor reaproveitar
        try:
            contexto.storage_state(path=str(ESTADO))
            print(f"-> sessao salva em {ESTADO}")
        except Exception as e:
            print(f"!! nao consegui salvar a sessao: {e}")

        navegador.close()

    # ----- ranquear e gravar -----
    for c in capturas:
        c["nota"] = pontuar(c["corpo"], c["url"])
    capturas.sort(key=lambda c: c["nota"], reverse=True)

    linhas = [
        f"Coletado em: {datetime.now(timezone.utc).isoformat()}",
        f"Pagina: {args.url}",
        f"Respostas candidatas capturadas: {len(capturas)}",
        "",
        "RANKING (nota alta = mais chance de ser a fonte dos numeros de gamma)",
        "=" * 78,
    ]

    for i, c in enumerate(capturas, start=1):
        nome = f"{i:03d}-{slug(c['url'])}"
        ext = ".json" if "json" in c["content_type"].lower() else ".txt"
        (AMOSTRAS / (nome + ext)).write_text(c["corpo"], encoding="utf-8")

        preview = re.sub(r"\s+", " ", c["corpo"][:400])
        linhas += [
            "",
            f"[{i:03d}] nota={c['nota']}  status={c['status']}  {c['metodo']}",
            f"      url: {c['url']}",
            f"      tipo: {c['content_type']}  bytes: {c['tamanho']}",
            f"      arquivo: amostras/{nome}{ext}",
            f"      preview: {preview}",
        ]
        if c["post_data"]:
            linhas.append(f"      post_data: {str(c['post_data'])[:300]}")

    if texto:
        linhas += ["", "TEXTO VISIVEL DA PAGINA (primeiros 3000 caracteres)",
                   "=" * 78, texto[:3000]]

    (AMOSTRAS / "resumo.txt").write_text("\n".join(linhas), encoding="utf-8")

    print()
    print("=" * 70)
    if capturas:
        print("TOP 5 CANDIDATOS:")
        for c in capturas[:5]:
            print(f"  nota={c['nota']:<5} {c['status']} {c['url'][:95]}")
    else:
        print("Nenhuma resposta JSON capturada.")
        print("Pode ser que os numeros venham direto no HTML -> veja amostras/pagina.txt")
    print()
    print(f"Leia o detalhe em: {AMOSTRAS / 'resumo.txt'}")
    print("Me mande o resumo.txt que eu monto o extrator exato.")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
