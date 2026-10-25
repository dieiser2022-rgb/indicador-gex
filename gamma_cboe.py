import csv
import json
import math
import urllib.request
from datetime import datetime, date

SIMBOLO = "SPX"        # SPX, SPY, QQQ, NDX...
DIAS_MAX = 45          # considerar expiracoes ate N dias; 0 = todas
INCLUIR_0DTE = False   # True so faz sentido com o mercado aberto
FAIXA = 0.12           # strikes dentro de +/- 12% do spot
MARGEM = 0.005         # parede precisa estar a 0.5% do preco, no minimo
VARRE = 0.10           # varredura de preco para achar o Zero Gamma
PASSOS = 81            # resolucao da varredura

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/131.0.0.0 Safari/537.36"
TAXA = 0.04


def url_de(simbolo):
    s = simbolo.upper()
    indices = ("SPX", "NDX", "VIX", "RUT", "DJX")
    alvo = "_" + s if s in indices else s
    return "https://cdn.cboe.com/api/global/delayed_quotes/options/" + alvo + ".json"


def baixar(simbolo):
    req = urllib.request.Request(url_de(simbolo), headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8", "ignore"))


def partes(nome):
    if len(nome) < 16:
        return None
    try:
        strike = int(nome[-8:]) / 1000.0
        tipo = nome[-9].upper()
        aa = int(nome[-15:-13])
        mm = int(nome[-13:-11])
        dd = int(nome[-11:-9])
        venc = date(2000 + aa, mm, dd)
    except Exception:
        return None
    if tipo not in ("C", "P"):
        return None
    return (nome[:-15], venc, tipo, strike)


def pdf(x):
    return math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)


def gamma_bs(spot, strike, anos, iv):
    if spot <= 0 or strike <= 0 or anos <= 0 or iv <= 0:
        return 0.0
    vt = iv * math.sqrt(anos)
    d1 = (math.log(spot / strike) + (TAXA + 0.5 * iv * iv) * anos) / vt
    return pdf(d1) / (spot * vt)


def mediana(vals):
    if not vals:
        return 0.0
    v = sorted(vals)
    n = len(v)
    return v[n // 2] if n % 2 else (v[n // 2 - 1] + v[n // 2]) / 2.0


def analisar(dados):
    bloco = dados.get("data", {})
    spot = float(bloco.get("current_price") or 0)
    opcoes = bloco.get("options", [])
    hoje = date.today()

    com_gamma = 0
    com_oi = 0
    vencidas = 0
    usaveis = []
    ivs = []

    minimo = 1 if not INCLUIR_0DTE else 0

    for o in opcoes:
        p = partes(o.get("option") or "")
        if not p:
            continue
        raiz, venc, tipo, strike = p

        oi = float(o.get("open_interest") or 0)
        g = float(o.get("gamma") or 0)
        iv = float(o.get("iv") or 0)

        if g != 0:
            com_gamma = com_gamma + 1
        if oi > 0:
            com_oi = com_oi + 1

        dias = (venc - hoje).days
        if dias < minimo:
            if oi > 0:
                vencidas = vencidas + 1
            continue
        if oi <= 0:
            continue
        if DIAS_MAX and dias > DIAS_MAX:
            continue
        if spot > 0 and abs(strike - spot) / spot > FAIXA:
            continue

        if 0 < iv < 3:
            ivs.append(iv)
        usaveis.append({"dias": dias, "tipo": tipo, "strike": strike,
                        "oi": oi, "gamma": g, "iv": iv})

    iv_padrao = mediana(ivs)
    for u in usaveis:
        if not (0 < u["iv"] < 3):
            u["iv"] = iv_padrao

    return spot, opcoes, usaveis, com_gamma, com_oi, vencidas, iv_padrao


def gex_por_strike(spot, usaveis):
    por_strike = {}
    call_gex = {}
    put_gex = {}
    usou_bs = 0

    for u in usaveis:
        g = u["gamma"]
        if g == 0:
            g = gamma_bs(spot, u["strike"], max(u["dias"], 1) / 365.0, u["iv"])
            if g != 0:
                usou_bs = usou_bs + 1
        if g == 0:
            continue

        valor = g * u["oi"] * 100.0 * spot * spot * 0.01
        if u["tipo"] == "P":
            valor = -valor

        k = u["strike"]
        por_strike[k] = por_strike.get(k, 0.0) + valor
        if u["tipo"] == "C":
            call_gex[k] = call_gex.get(k, 0.0) + valor
        else:
            put_gex[k] = put_gex.get(k, 0.0) + valor

    return por_strike, call_gex, put_gex, usou_bs


def net_em(preco, usaveis):
    # recalcula o gamma de toda a carteira supondo o indice nesse preco
    total = 0.0
    for u in usaveis:
        g = gamma_bs(preco, u["strike"], max(u["dias"], 1) / 365.0, u["iv"])
        if g == 0:
            continue
        v = g * u["oi"] * 100.0 * preco * preco * 0.01
        total = total - v if u["tipo"] == "P" else total + v
    return total


def achar_zero_gamma(spot, usaveis):
    ini = spot * (1.0 - VARRE)
    fim = spot * (1.0 + VARRE)
    passo = (fim - ini) / (PASSOS - 1)

    ant_p = None
    ant_v = None
    for i in range(PASSOS):
        p = ini + passo * i
        v = net_em(p, usaveis)
        if ant_v is not None and ant_v != 0 and (ant_v > 0) != (v > 0):
            t = abs(ant_v) + abs(v)
            if t > 0:
                return ant_p + (p - ant_p) * (abs(ant_v) / t)
            return p
        ant_p = p
        ant_v = v
    return None


def paredes(spot, call_gex, put_gex):
    # A parede de call fica ACIMA do preco e a de put ABAIXO, com uma
    # distancia minima: um strike colado no spot nao serve de barreira.
    teto = spot * (1.0 + MARGEM)
    piso = spot * (1.0 - MARGEM)
    acima = {k: v for k, v in call_gex.items() if k >= teto and v > 0}
    abaixo = {k: v for k, v in put_gex.items() if k <= piso and v < 0}
    cw = max(acima, key=lambda k: acima[k]) if acima else None
    pw = min(abaixo, key=lambda k: abaixo[k]) if abaixo else None
    return cw, pw


def formatar(v):
    if v is None:
        return "N/A"
    a = abs(v)
    if a >= 1e9:
        return "%.2fB" % (v / 1e9)
    if a >= 1e6:
        return "%.2fM" % (v / 1e6)
    if a >= 1e3:
        return "%.2fK" % (v / 1e3)
    return "%.2f" % v


def main():
    print("baixando dados da CBOE para", SIMBOLO, "...")
    dados = baixar(SIMBOLO)
    spot, todas, usaveis, com_gamma, com_oi, vencidas, iv_med = analisar(dados)

    print("")
    print("DIAGNOSTICO")
    print("  spot price            ", spot)
    print("  contratos no arquivo  ", len(todas))
    print("  com open interest     ", com_oi)
    print("  com gamma da CBOE     ", com_gamma)
    print("  descartados (vencidos)", vencidas)
    print("  usaveis (filtrados)   ", len(usaveis))
    print("  iv mediana            ", "%.4f" % iv_med)

    if not usaveis:
        print("")
        print("nenhum contrato usavel - aumente DIAS_MAX ou FAIXA")
        return

    por_strike, call_gex, put_gex, usou_bs = gex_por_strike(spot, usaveis)
    if usou_bs:
        print("  gamma estimado por BS ", usou_bs)

    if not por_strike:
        print("")
        print("nao foi possivel calcular gamma")
        return

    net = sum(por_strike.values())
    cw, pw = paredes(spot, call_gex, put_gex)
    print("")
    print("calculando o Zero Gamma (varrendo precos)...")
    zg = achar_zero_gamma(spot, usaveis)

    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    print("")
    print("NIVEIS DE GAMMA -", SIMBOLO, "-", ts)
    print("  Spot Price       ", "%.2f" % spot)
    print("  Net GEX          ", formatar(net), "por 1% de movimento")
    print("  Regime           ", "POSITIVO (dealers estabilizam)" if net > 0
          else "NEGATIVO (dealers amplificam)")
    print("  Zero Gamma       ", "%.2f" % zg if zg else "N/A (fora da faixa varrida)")
    if cw:
        print("  Call Wall        ", "%.2f" % cw, " ", formatar(call_gex[cw]))
    else:
        print("  Call Wall         N/A")
    if pw:
        print("  Put Wall         ", "%.2f" % pw, " ", formatar(put_gex[pw]))
    else:
        print("  Put Wall          N/A")

    pos = sorted([kv for kv in por_strike.items() if kv[1] > 0],
                 key=lambda kv: kv[1], reverse=True)[:5]
    neg = sorted([kv for kv in por_strike.items() if kv[1] < 0],
                 key=lambda kv: kv[1])[:5]

    print("")
    print("  maior gamma POSITIVO (resistencia / freio):")
    for k, v in pos:
        print("    %10.2f  %12s" % (k, formatar(v)))
    print("  maior gamma NEGATIVO (suporte / acelerador):")
    for k, v in neg:
        print("    %10.2f  %12s" % (k, formatar(v)))

    linhas = [
        [ts, SIMBOLO, "Spot Price", "%.2f" % spot],
        [ts, SIMBOLO, "Net GEX", "%.0f" % net],
        [ts, SIMBOLO, "Regime", "POSITIVO" if net > 0 else "NEGATIVO"],
        [ts, SIMBOLO, "Zero Gamma", "%.2f" % zg if zg else ""],
        [ts, SIMBOLO, "Call Wall", "%.2f" % cw if cw else ""],
        [ts, SIMBOLO, "Put Wall", "%.2f" % pw if pw else ""],
    ]
    for k, v in pos:
        linhas.append([ts, SIMBOLO, "GEX+ " + ("%.2f" % k), "%.0f" % v])
    for k, v in neg:
        linhas.append([ts, SIMBOLO, "GEX- " + ("%.2f" % k), "%.0f" % v])

    novo = False
    try:
        open("gamma.csv", "r").close()
    except Exception:
        novo = True
    with open("gamma.csv", "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if novo:
            w.writerow(["ts", "simbolo", "campo", "valor"])
        for l in linhas:
            w.writerow(l)

    print("")
    print("gravado em gamma.csv")


if __name__ == "__main__":
    main()
