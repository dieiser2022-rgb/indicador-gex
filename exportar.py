"""Gera a linha de dados que os indicadores de GEX esperam receber colada.

O formato e o mesmo publicado pelo GEX ECOSYSTEM:

    $NQ1!: Call Resistance, 30100, Put Support, 30000, HVL, 30075,
    1D Min, 29691.92, 1D Max, 30464.58, Call Resistance 0DTE, 30100, ...

Ou seja: o ticker com cifrao e dois pontos, seguido de pares "nome, valor"
separados por virgula. Os niveis saem na escala do ativo do grafico, ja
convertidos do indice para o futuro quando for o caso.
"""

import math

# ordem em que os campos aparecem na linha, igual ao formato original
ORDEM = [
    "Call Resistance", "Put Support", "HVL", "1D Min", "1D Max",
    "Call Resistance 0DTE", "Put Support 0DTE", "HVL 0DTE", "Gamma Wall 0DTE",
    "GEX 1", "GEX 2", "GEX 3", "GEX 4", "GEX 5",
    "GEX 6", "GEX 7", "GEX 8", "GEX 9", "GEX 10",
]

DIAS_UTEIS_ANO = 252


def numero(v):
    """30100.0 -> '30100'   29691.9231 -> '29691.92'"""
    if v is None:
        return ""
    if abs(v - round(v)) < 0.005:
        return str(int(round(v)))
    return "%.2f" % v


def faixa_do_dia(spot, iv):
    """Movimento esperado para um dia: spot x (1 +/- iv / raiz(252)).

    E a conta padrao de expected move. Conferida contra os valores do
    GEX ECOSYSTEM: para spot 30075 e faixa 29691.92 a 30464.58, a IV
    implicita sai em 20,4% ao ano, que e plausivel para o Nasdaq.
    """
    if not spot or not iv or iv <= 0:
        return None, None
    passo = spot * iv / math.sqrt(DIAS_UTEIS_ANO)
    return spot - passo, spot + passo


SEPARACAO_MINIMA = 0.0025   # 0,25% do preco entre um GEX e outro
QUANTOS_GEX = 10


def escolher_gex(spot, por_strike, evitar=(), quantos=QUANTOS_GEX,
                 separacao=SEPARACAO_MINIMA):
    """Escolhe os strikes de maior concentracao, mas espalhados.

    Pegar simplesmente os dez maiores nao serve: o gamma e sempre mais alto
    perto do dinheiro, entao os dez maiores sao sempre os dez vizinhos do
    preco, e no grafico viram um amontoado de linhas coladas.

    Aqui os candidatos continuam ordenados por tamanho, mas um strike so entra
    se estiver a uma distancia minima dos que ja entraram e dos niveis que o
    formato ja publica em campo proprio (as paredes e a inversao). O resultado
    e um perfil legivel em vez de um bloco.
    """
    if not por_strike or not spot:
        return []
    minimo = spot * separacao
    escolhidos = []
    bloqueados = [v for v in evitar if v]

    candidatos = sorted(por_strike.items(), key=lambda kv: abs(kv[1]),
                        reverse=True)
    for strike, _ in candidatos:
        if len(escolhidos) >= quantos:
            break
        perto_de_outro = any(abs(strike - j) < minimo
                             for j in escolhidos + bloqueados)
        if perto_de_outro:
            continue
        escolhidos.append(strike)

    # Se a separacao foi exigente demais e sobrou pouco, completa com os
    # maiores que ainda nao entraram, para nao devolver meia lista.
    if len(escolhidos) < quantos:
        for strike, _ in candidatos:
            if len(escolhidos) >= quantos:
                break
            if strike not in escolhidos and strike not in bloqueados:
                escolhidos.append(strike)

    return escolhidos


def _niveis_de(G, spot, contratos, com_zero_gamma=True):
    """Calcula paredes, inversao e perfil para um conjunto de contratos."""
    if not contratos:
        return None
    por_strike, call_gex, put_gex, _ = G.gex_por_strike(spot, contratos)
    if not por_strike:
        return None
    cw, pw = G.paredes(spot, call_gex, put_gex)
    zg = G.achar_zero_gamma(spot, contratos) if com_zero_gamma else None
    # parede de gamma: o strike de maior concentracao em modulo
    muro = max(por_strike.items(), key=lambda kv: abs(kv[1]))[0]
    return {"call_wall": cw, "put_wall": pw, "zero_gamma": zg,
            "gamma_wall": muro, "por_strike": por_strike}


def calcular(G, dados_cboe, dias_padrao=45, dias_0dte=0):
    """Monta todos os niveis, na escala do indice (sem basis ainda).

    Faz um unico analisar com janela ampla e depois separa os contratos por
    vencimento em memoria, em vez de baixar e analisar duas vezes.
    """
    antes_dias, antes_0dte = G.DIAS_MAX, G.INCLUIR_0DTE
    try:
        G.DIAS_MAX = max(dias_padrao, 1)
        G.INCLUIR_0DTE = True
        spot, todas, usaveis, com_gamma, com_oi, venc, iv = G.analisar(dados_cboe)
    finally:
        G.DIAS_MAX, G.INCLUIR_0DTE = antes_dias, antes_0dte

    if not usaveis or not spot:
        return None

    padrao = _niveis_de(G, spot, [u for u in usaveis if u["dias"] >= 1])
    if padrao is None:
        padrao = _niveis_de(G, spot, usaveis)

    curtos = [u for u in usaveis if u["dias"] <= dias_0dte]
    hoje = _niveis_de(G, spot, curtos) if curtos else None

    mn, mx = faixa_do_dia(spot, iv)

    ja_usados = []
    for chave in ("call_wall", "put_wall", "zero_gamma"):
        v = (padrao or {}).get(chave)
        if v:
            ja_usados.append(v)
    perfil = escolher_gex(spot, (padrao or {}).get("por_strike", {}), ja_usados)

    return {
        "spot": spot,
        "iv": iv,
        "contratos": len(usaveis),
        "contratos_0dte": len(curtos),
        "tem_0dte": hoje is not None,
        "padrao": padrao,
        "hoje": hoje,
        "min_dia": mn,
        "max_dia": mx,
        "gex_top": perfil,
    }


def montar(ticker, calc, basis=0.0, fator=1.0):
    """Devolve (linha_pronta, dicionario_de_niveis).

    basis e fator convertem do indice para o ativo do grafico: o NQ e o NDX
    mais o basis, e um ETF entra por proporcao.
    """
    if not calc:
        return "", {}

    def conv(v):
        return (v * fator + basis) if v else None

    padrao = calc.get("padrao") or {}
    hoje = calc.get("hoje") or {}

    valores = {
        "Call Resistance": conv(padrao.get("call_wall")),
        "Put Support": conv(padrao.get("put_wall")),
        "HVL": conv(padrao.get("zero_gamma")),
        "1D Min": conv(calc.get("min_dia")),
        "1D Max": conv(calc.get("max_dia")),
        "Call Resistance 0DTE": conv(hoje.get("call_wall")),
        "Put Support 0DTE": conv(hoje.get("put_wall")),
        "HVL 0DTE": conv(hoje.get("zero_gamma")),
        "Gamma Wall 0DTE": conv(hoje.get("gamma_wall")),
    }
    for i, strike in enumerate(calc.get("gex_top") or [], start=1):
        valores["GEX " + str(i)] = conv(strike)

    nome = (ticker or "").strip().upper()
    if nome and not nome.startswith("$"):
        nome = "$" + nome

    partes = []
    for campo in ORDEM:
        v = valores.get(campo)
        if v is None:
            continue
        partes.append(campo + ", " + numero(v))

    linha = (nome + ": " if nome else "") + ", ".join(partes)
    # devolve so o que entrou na linha, para a tabela de conferencia do painel
    # nao exibir campo vazio
    presentes = {k: v for k, v in valores.items() if v is not None}
    return linha, presentes
