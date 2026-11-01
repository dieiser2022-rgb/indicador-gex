"""Lista quais campos a CBOE entrega por contrato de opcao.

Hoje o projeto le apenas option, gamma, open_interest e iv. O esboco do painel
do NinjaTrader pede colunas de volume e delta, e a pergunta "esses campos vem
no arquivo?" nao pode ser respondida por memoria - tem que ser medida.

Mostra os nomes dos campos, o tipo de cada um e um exemplo de valor, alem de
quantos contratos tem cada campo preenchido. Campo que existe mas vem sempre
zerado e tao inutil quanto campo que nao existe.

Uso:
    python ver_campos_cboe.py          (NDX)
    python ver_campos_cboe.py SPX
"""

import sys

import gamma_cboe as G

USADOS = ("option", "gamma", "open_interest", "iv")


def olhar(simbolo):
    print("")
    print("=" * 70)
    print(" " + simbolo + "  -  " + G.url_de(simbolo))
    print("=" * 70)

    try:
        dados = G.baixar(simbolo)
    except Exception as e:
        print("  nao consegui baixar:", e)
        return

    bloco = dados.get("data", {})
    opcoes = bloco.get("options", [])

    print("  chaves no nivel 'data' :", ", ".join(sorted(bloco.keys())))
    print("  contratos no arquivo   :", len(opcoes))
    if not opcoes:
        print("  arquivo sem contratos.")
        return

    # Junta as chaves de uma amostra: um contrato isolado pode nao ter todas.
    amostra = opcoes[:4000]
    chaves = set()
    for o in amostra:
        chaves.update(o.keys())

    print("")
    print("  %-22s %-9s %-16s %s" % ("campo", "tipo", "exemplo", "preenchidos"))
    print("  " + "-" * 64)

    for c in sorted(chaves):
        exemplo = None
        preenchidos = 0
        for o in amostra:
            v = o.get(c)
            if v not in (None, "", 0, 0.0):
                preenchidos += 1
                if exemplo is None:
                    exemplo = v
        if exemplo is None:
            exemplo = o.get(c)
        marca = "  <== ja usamos" if c in USADOS else ""
        print("  %-22s %-9s %-16s %d de %d%s"
              % (c, type(exemplo).__name__, str(exemplo)[:16], preenchidos,
                 len(amostra), marca))

    print("")
    faltam = [c for c in ("volume", "delta", "theta", "vega", "last_trade_price")
              if c not in chaves]
    if faltam:
        print("  NAO existem no arquivo:", ", ".join(faltam))
    else:
        print("  volume e delta existem no arquivo.")


def main():
    simbolos = [s.upper() for s in sys.argv[1:] if not s.startswith("-")]
    if not simbolos:
        simbolos = ["NDX"]
    for s in simbolos:
        olhar(s)
    print("")
    print("=== fim do relatorio ===")
    return 0


if __name__ == "__main__":
    import os
    import relatorio
    with relatorio.capturar("relatorio_campos.txt"):
        codigo = main()
    if os.name == "nt":
        try:
            input("aperte ENTER para fechar...")
        except (EOFError, KeyboardInterrupt):
            pass
    sys.exit(codigo)
