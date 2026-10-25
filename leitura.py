"""Interpretacao dos numeros em texto.

Tudo aqui e deduzido por regras a partir da mecanica de hedge dos dealers.
Nao ha previsao de preco: o texto descreve como o hedge tende a funcionar
em cada regime, e onde estao os niveis que importam.
"""

from datetime import datetime, timezone


def _fmt(v, dec=0):
    """Numero no padrao brasileiro: 29796.5 -> 29.796,50"""
    if v is None:
        return "N/A"
    texto = format(float(v), "," + "." + str(dec) + "f")
    # troca os separadores: vírgula de milhar vira ponto, ponto decimal vira vírgula
    return texto.replace(",", "@").replace(".", ",").replace("@", ".")


def _pct(a, b):
    if not a or not b:
        return None
    return (a - b) / b * 100.0


def leitura_mm(d):
    """Como o market maker tende a se comportar. Recebe um ativo calculado."""
    if not d or d.get("erro") or not d.get("spot"):
        return {"regime": "", "titulo": "sem dados", "frases": [], "alertas": []}

    spot = d["spot"]
    net = d.get("net_gex") or 0.0
    zg = d.get("zero_gamma")
    cw = d.get("call_wall")
    pw = d.get("put_wall")
    dec = 0 if spot > 2000 else 2

    positivo = net > 0
    frases = []
    alertas = []

    if positivo:
        titulo = "GAMMA POSITIVO"
        frases.append(
            "Os dealers estao comprados em gamma: vendem quando sobe e compram "
            "quando cai. Isso freia o mercado.")
        frases.append(
            "Leitura pratica: tendencia a ficar preso em faixa, com movimentos "
            "contidos e mais reversao a media.")
    else:
        titulo = "GAMMA NEGATIVO"
        frases.append(
            "Os dealers estao vendidos em gamma: compram quando sobe e vendem "
            "quando cai. Isso empurra o movimento.")
        frases.append(
            "Leitura pratica: movimentos tendem a esticar, com menos reversao. "
            "Quando anda, anda forte.")

    if zg:
        dist = _pct(spot, zg)
        if spot < zg:
            frases.append(
                "Preco em " + _fmt(spot, dec) + ", abaixo da inversao gama ("
                + _fmt(zg, dec) + ", " + ("%.2f" % abs(dist)) + "% acima). "
                "O regime so vira positivo se superar esse nivel.")
        else:
            frases.append(
                "Preco em " + _fmt(spot, dec) + ", acima da inversao gama ("
                + _fmt(zg, dec) + ", " + ("%.2f" % abs(dist)) + "% abaixo). "
                "Perder esse nivel joga o mercado no regime negativo.")
        if abs(dist) < 0.3:
            alertas.append("Preco quase na inversao gama: regime pode trocar a qualquer momento.")

    if cw:
        dc = _pct(cw, spot)
        frases.append(
            "Parede de call em " + _fmt(cw, dec) + " (" + ("%.2f" % dc)
            + "% acima): costuma travar a alta, porque o hedge dos dealers "
            "aumenta a venda conforme o preco chega la.")
        if dc is not None and dc < 0.3:
            alertas.append("Preco colado na parede de call: espere resistencia.")

    if pw:
        dp = _pct(pw, spot)
        frases.append(
            "Parede de put em " + _fmt(pw, dec) + " (" + ("%.2f" % abs(dp))
            + "% abaixo): funciona como suporte, mas se romper a queda tende "
            "a acelerar.")
        if dp is not None and abs(dp) < 0.3:
            alertas.append("Preco colado na parede de put: suporte em teste.")

    if cw and pw:
        frases.append(
            "Faixa que a estrutura de gamma sugere para hoje: "
            + _fmt(pw, dec) + " a " + _fmt(cw, dec) + ".")

    return {
        "regime": "POSITIVO" if positivo else "NEGATIVO",
        "titulo": titulo,
        "frases": frases,
        "alertas": alertas,
    }


def _grupo(panorama, simbolos):
    saida = []
    for p in panorama:
        if p["simbolo"] in simbolos and p.get("pct") is not None:
            saida.append(p["nome"] + " " + ("%+.2f" % p["pct"]) + "%")
    return saida


def morning_call(panorama, eventos, noticias, gammas):
    """Resumo factual do dia. Nenhuma estimativa de direcao."""
    blocos = []
    agora = datetime.now(timezone.utc)

    fut = _grupo(panorama, ["NQ=F", "ES=F", "YM=F"])
    if fut:
        blocos.append({"titulo": "Futuros EUA", "texto": "   ".join(fut)})

    eur = _grupo(panorama, ["^STOXX50E", "^GDAXI"])
    asia = _grupo(panorama, ["^N225", "^HSI"])
    if eur or asia:
        partes = []
        if eur:
            partes.append("Europa: " + "   ".join(eur))
        if asia:
            partes.append("Asia: " + "   ".join(asia))
        blocos.append({"titulo": "Exterior", "texto": " | ".join(partes)})

    risco = _grupo(panorama, ["^VIX", "^TNX", "DX-Y.NYB"])
    if risco:
        blocos.append({"titulo": "Risco e juros", "texto": "   ".join(risco)})

    commod = _grupo(panorama, ["CL=F", "GC=F", "BTC-USD"])
    if commod:
        blocos.append({"titulo": "Commodities e cripto", "texto": "   ".join(commod)})

    # eventos de hoje, com destaque para alto impacto
    hoje = agora.date()
    do_dia = [e for e in eventos
              if datetime.fromtimestamp(e["ts"], timezone.utc).date() == hoje]
    fortes = [e for e in do_dia if e["peso"] >= 3]
    if fortes:
        itens = []
        for e in fortes[:5]:
            h = datetime.fromtimestamp(e["ts"], timezone.utc)
            itens.append(h.strftime("%H:%M") + " UTC " + e["titulo"]
                         + (" (" + e["moeda"] + ")" if e["moeda"] else ""))
        blocos.append({"titulo": "Eventos de alto impacto hoje",
                       "texto": " | ".join(itens)})
    elif do_dia:
        blocos.append({"titulo": "Eventos de hoje",
                       "texto": str(len(do_dia)) + " eventos na agenda, nenhum de alto impacto"})
    else:
        blocos.append({"titulo": "Eventos de hoje",
                       "texto": "nada de alto impacto na agenda"})

    # estrutura de gamma
    linhas_gamma = []
    for g in gammas:
        if not g or g.get("erro") or not g.get("spot"):
            continue
        dec = 0 if g["spot"] > 2000 else 2
        reg = "positivo" if (g.get("net_gex") or 0) > 0 else "negativo"
        txt = g["indice"] + ": gamma " + reg
        if g.get("zero_gamma"):
            txt += ", inversao em " + _fmt(g["zero_gamma"], dec)
        if g.get("put_wall") and g.get("call_wall"):
            txt += ", faixa " + _fmt(g["put_wall"], dec) + " a " + _fmt(g["call_wall"], dec)
        linhas_gamma.append(txt)
    if linhas_gamma:
        blocos.append({"titulo": "Estrutura de gamma",
                       "texto": " | ".join(linhas_gamma)})

    manchetes = [n["titulo"] for n in (noticias or [])[:4]]
    if manchetes:
        blocos.append({"titulo": "Manchetes", "texto": " // ".join(manchetes)})

    return {
        "gerado": agora.isoformat(timespec="seconds"),
        "blocos": blocos,
        "aviso": ("Resumo factual montado a partir de cotacoes, agenda e manchetes. "
                  "Nao contem projecao de preco."),
    }
