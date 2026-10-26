"""Lista todos os vencimentos que a CBOE esta entregando, e checa o 0DTE.

Serve para responder uma pergunta especifica: os contratos que vencem hoje
estao chegando no arquivo da CBOE, e eles sobrevivem aos nossos filtros?

Mostra, para cada data de vencimento, quantos contratos existem, quantos tem
open interest, e quantos sobram depois do filtro de faixa de strike. Assim da
para ver se o 0DTE sumiu porque nao existe, porque esta sem open interest, ou
porque algum filtro nosso o derrubou.

Uso:
    python ver_vencimentos.py              (NDX, o indice do Nasdaq)
    python ver_vencimentos.py SPX
    python ver_vencimentos.py QQQ SPY
"""

import sys
from datetime import date

import gamma_cboe as G

DIAS_SEMANA = ("segunda", "terca", "quarta", "quinta", "sexta",
               "sabado", "domingo")

# O terminal sobrescreve estes dois ao carregar o modulo. Sem repetir aqui, os
# niveis impressos sairiam um pouco diferentes dos do painel, e a comparacao
# perderia o sentido.
G.MARGEM = 0.0
G.PASSOS = 51


def fmt(v):
    """Preco, nao valor de GEX. O G.formatar abrevia em K/M/B e transformaria
    um strike de 25000 em "25.00K"."""
    return "%.2f" % v if v else "N/A"


def tabela(simbolo):
    print("")
    print("=" * 72)
    print(" " + simbolo + "  -  " + G.url_de(simbolo))
    print("=" * 72)

    try:
        dados = G.baixar(simbolo)
    except Exception as e:
        print("  nao consegui baixar:", e)
        return

    bloco = dados.get("data", {})
    spot = float(bloco.get("current_price") or 0)
    opcoes = bloco.get("options", [])
    hoje = date.today()

    print("  spot informado pela CBOE :", spot)
    print("  contratos no arquivo     :", len(opcoes))
    print("  data de hoje na maquina  :", hoje,
          "(" + DIAS_SEMANA[hoje.weekday()] + ")")
    if hoje.weekday() >= 5:
        print("  ATENCAO: fim de semana. Nada vence hoje, e isso e normal.")

    # Agrupa por data de vencimento, contando o que cada filtro deixa passar.
    por_venc = {}
    sem_nome = 0
    for o in opcoes:
        p = G.partes(o.get("option") or "")
        if not p:
            sem_nome += 1
            continue
        _raiz, venc, tipo, strike = p
        oi = float(o.get("open_interest") or 0)
        gam = float(o.get("gamma") or 0)

        d = por_venc.setdefault(venc, {
            "total": 0, "com_oi": 0, "oi_soma": 0.0, "na_faixa": 0,
            "com_gamma": 0, "raizes": set(),
        })
        d["total"] += 1
        d["raizes"].add(_raiz)
        if gam != 0:
            d["com_gamma"] += 1
        if oi > 0:
            d["com_oi"] += 1
            d["oi_soma"] += oi
            # mesmo filtro de faixa de strike que o analisar usa
            if spot > 0 and abs(strike - spot) / spot <= G.FAIXA:
                d["na_faixa"] += 1

    if sem_nome:
        print("  nomes que nao soube ler  :", sem_nome)

    print("")
    print("  %-12s %5s  %8s %8s %8s %12s %10s" %
          ("vencimento", "dias", "contrat.", "com OI", "c/gamma", "OI total",
           "na faixa"))
    print("  " + "-" * 68)

    tem_hoje = False
    for venc in sorted(por_venc):
        d = por_venc[venc]
        dias = (venc - hoje).days
        if dias == 0:
            tem_hoje = True
        marca = "  <== 0DTE" if dias == 0 else (" (vencido)" if dias < 0 else "")
        print("  %-12s %5d  %8d %8d %8d %12.0f %10d%s" %
              (venc.isoformat(), dias, d["total"], d["com_oi"],
               d["com_gamma"], d["oi_soma"], d["na_faixa"], marca))

    print("")
    if not tem_hoje:
        print("  >>> NENHUM contrato vence hoje (" + hoje.isoformat() + ").")
        proximos = [v for v in sorted(por_venc) if (v - hoje).days > 0]
        if proximos:
            p = proximos[0]
            print("      O vencimento mais proximo e",
                  p.isoformat(), "em", (p - hoje).days, "dia(s).")
        return

    d = por_venc[next(v for v in por_venc if (v - hoje).days == 0)]
    print("  >>> O 0DTE existe no arquivo:", d["total"], "contratos,",
          d["com_oi"], "com open interest,", d["na_faixa"], "na faixa de strike.")
    print("      raizes:", ", ".join(sorted(d["raizes"])))

    if d["na_faixa"] == 0:
        print("")
        if d["com_oi"] == 0:
            # Caso tipico de pre-abertura: os contratos de hoje ja aparecem no
            # arquivo, mas o open interest do dia ainda nao foi publicado.
            print("      Mas NENHUM tem open interest, e o nosso filtro exige")
            print("      open interest maior que zero. Isso e comum antes da")
            print("      abertura: a CBOE publica o open interest do dia")
            print("      depois que o mercado abre. Tente de novo mais tarde.")
        else:
            print("      Mas nenhum sobrou depois do filtro de faixa: todos os")
            print("      strikes com open interest estao a mais de",
                  "%.0f%%" % (G.FAIXA * 100), "do preco.")
        return

    # Agora calcula os niveis so com os contratos de hoje, do mesmo jeito que
    # o terminal faz, para ver se eles realmente saem.
    import exportar

    calc = exportar.calcular(G, dados, dias_padrao=45, dias_0dte=0)
    if not calc:
        print("      O calculo nao devolveu nada.")
        return

    print("")
    print("  NIVEIS CALCULADOS")
    print("    contratos usaveis (todos) :", calc["contratos"])
    print("    contratos usaveis (0DTE)  :", calc["contratos_0dte"])
    print("    tem_0dte                  :", calc["tem_0dte"])

    hj = calc.get("hoje") or {}
    if not hj:
        print("")
        print("    Os contratos de hoje existem, mas os niveis 0DTE sairam")
        print("    vazios. Isso acontece quando nenhum strike tem gamma")
        print("    utilizavel - me mande esta tela que eu investigo.")
        return

    print("")
    print("    Call Resistance 0DTE :", fmt(hj.get("call_wall")))
    print("    Put Support 0DTE     :", fmt(hj.get("put_wall")))
    print("    HVL 0DTE             :", fmt(hj.get("zero_gamma")))
    print("    Gamma Wall 0DTE      :", fmt(hj.get("gamma_wall")))


def main():
    simbolos = [s.upper() for s in sys.argv[1:] if not s.startswith("-")]
    if not simbolos:
        simbolos = ["NDX"]
    for s in simbolos:
        tabela(s)
    print("")
    print("=== fim. copie tudo acima e cole no chat ===")
    return 0


if __name__ == "__main__":
    codigo = main()
    import os
    if os.name == "nt":
        try:
            input("aperte ENTER para fechar...")
        except (EOFError, KeyboardInterrupt):
            pass
    sys.exit(codigo)
