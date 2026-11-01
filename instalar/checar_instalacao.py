"""Confere se a maquina esta pronta para rodar o Terminal GEX.

Roda antes do primeiro uso numa maquina nova e diz, item por item, o que esta
certo e o que falta. A ideia e descobrir o problema aqui, com mensagem clara,
em vez de ver o terminal falhar depois sem explicacao.

Uso:
    python checar_instalacao.py
"""

import os
import socket
import sys
import urllib.request

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)          # a pasta do projeto, um nivel acima

# Minimo real: ThreadingHTTPServer e subprocess(capture_output) sao de 3.7.
# Nada no codigo usa recurso mais novo que isso.
MINIMO = (3, 7)
RECOMENDADO = (3, 10)

ARQUIVOS = [
    "terminal.py", "painel.html", "abrir.py", "gamma_cboe.py", "exportar.py",
    "fontes.py", "leitura.py", "relatorio.py",
    "indicadores/tradingview_gex.pine",
    "GEX.bat", "CRIAR_ATALHO.bat",
]

# Tudo da biblioteca padrao. Se algum faltar, a instalacao do Python esta
# incompleta - nenhum deles vem de pacote externo.
MODULOS = ["json", "math", "os", "socket", "ssl", "struct", "subprocess",
           "sys", "threading", "time", "urllib.request", "webbrowser",
           "xml.etree.ElementTree", "csv", "datetime", "http.server",
           "concurrent.futures"]

SITES = [
    ("CBOE (cadeia de opcoes)",
     "https://cdn.cboe.com/api/global/delayed_quotes/options/_NDX.json"),
    ("Yahoo (precos e candles)",
     "https://query1.finance.yahoo.com/v8/finance/chart/NQ%3DF?interval=15m&range=1d"),
]

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/131.0.0.0 Safari/537.36"

falhas = []
avisos = []


def titulo(t):
    print("")
    print("=== " + t + " " + "=" * max(0, 50 - len(t)))


def ok(texto):
    print("  [ok]    " + texto)


def erro(texto):
    print("  [FALTA] " + texto)
    falhas.append(texto)


def aviso(texto):
    print("  [aviso] " + texto)
    avisos.append(texto)


def checar_python():
    titulo("1. Python")
    v = sys.version_info
    atual = "%d.%d.%d" % (v[0], v[1], v[2])
    print("  versao instalada :", atual)
    print("  executavel       :", sys.executable)
    if v < MINIMO:
        erro("Python %s e antigo. Precisa de %d.%d ou mais novo."
             % (atual, MINIMO[0], MINIMO[1]))
    elif v < RECOMENDADO:
        ok("versao suficiente")
        aviso("Python %s funciona, mas o recomendado e %d.%d ou mais novo."
              % (atual, RECOMENDADO[0], RECOMENDADO[1]))
    else:
        ok("versao boa")


def checar_modulos():
    titulo("2. Biblioteca padrao do Python")
    faltando = []
    for m in MODULOS:
        try:
            __import__(m)
        except Exception:
            faltando.append(m)
    if faltando:
        erro("faltam modulos da biblioteca padrao: " + ", ".join(faltando))
        print("          Reinstale o Python marcando a instalacao completa.")
    else:
        ok("os %d modulos usados pelo projeto estao presentes" % len(MODULOS))
    print("  (nenhum pacote externo e necessario: nada de pip install)")


def checar_arquivos():
    titulo("3. Arquivos do projeto")
    print("  pasta do projeto :", RAIZ)
    for rel in ARQUIVOS:
        p = os.path.join(RAIZ, rel.replace("/", os.sep))
        if os.path.exists(p):
            ok("%-34s %d bytes" % (rel, os.path.getsize(p)))
        else:
            erro(rel + " nao encontrado")


def checar_nossos_modulos():
    titulo("4. O codigo carrega sem erro")
    if RAIZ not in sys.path:
        sys.path.insert(0, RAIZ)
    anterior = os.getcwd()
    try:
        os.chdir(RAIZ)
        for m in ("gamma_cboe", "exportar", "fontes", "leitura", "terminal"):
            try:
                __import__(m)
                ok(m + ".py carregou")
            except Exception as e:
                erro(m + ".py deu erro ao carregar: " + str(e))
    finally:
        os.chdir(anterior)


def checar_internet():
    titulo("5. Acesso as fontes de dados")
    for nome, url in SITES:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=30) as r:
                # Le so um pedaco: o arquivo da CBOE passa de 4 MB e baixar
                # tudo aqui seria desperdicio.
                pedaco = r.read(2048)
                if r.status == 200 and pedaco:
                    ok("%-28s respondeu (HTTP %d)" % (nome, r.status))
                else:
                    aviso("%s respondeu HTTP %s mas sem conteudo"
                          % (nome, r.status))
        except Exception as e:
            aviso(nome + " nao respondeu: " + str(e)[:90])


def checar_porta():
    titulo("6. A porta 8777 esta livre")
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.8)
            if s.connect_ex(("127.0.0.1", 8777)) == 0:
                aviso("alguem ja esta usando a porta 8777 - provavelmente um"
                      " terminal aberto. Se for, esta tudo bem.")
            else:
                ok("livre")
    except OSError as e:
        aviso("nao consegui testar a porta: " + str(e))


def veredito():
    titulo("RESULTADO")
    if falhas:
        print("  NAO ESTA PRONTO. Resolva primeiro:")
        for f in falhas:
            print("    - " + f)
        print("")
        print("  Releia o LEIA-ME-PRIMEIRO.txt desta pasta.")
        return 1

    print("  TUDO PRONTO para rodar.")
    if avisos:
        print("")
        print("  Pontos de atencao (nao impedem de rodar):")
        for a in avisos:
            print("    - " + a)
    print("")
    print("  Proximo passo: volte para a pasta de cima e de")
    print("  duplo clique em GEX.bat")
    return 0


def main():
    print("")
    print("  CHECAGEM DE INSTALACAO - Terminal GEX")
    checar_python()
    checar_modulos()
    checar_arquivos()
    if not falhas:
        checar_nossos_modulos()
    checar_internet()
    checar_porta()
    return veredito()


def _rodar_capturando():
    """Roda a checagem copiando o resultado para a area de transferencia.

    O relatorio.py mora na pasta de cima. Se ele nao estiver la - caso de
    quem copiou so a pasta instalar - a checagem roda normal, sem a copia.
    """
    if RAIZ not in sys.path:
        sys.path.insert(0, RAIZ)
    try:
        import relatorio
    except Exception:
        return main()
    with relatorio.capturar("relatorio_instalacao.txt"):
        return main()


if __name__ == "__main__":
    codigo = _rodar_capturando()
    print("")
    if os.name == "nt":
        try:
            input("  aperte ENTER para fechar...")
        except (EOFError, KeyboardInterrupt):
            pass
    sys.exit(codigo)
