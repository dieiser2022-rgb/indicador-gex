"""Relatorio do estado do atalho e do icone, para colar no chat.

Responde de uma vez as perguntas que levariam varias rodadas de tentativa:
o Windows consegue ler o nosso .ico? o atalho existe? para onde ele aponta?
qual icone esta configurado nele? o terminal esta no ar?

Uso:
    python diagnostico.py
"""

import json
import os
import platform
import socket
import struct
import subprocess
import sys

PASTA = os.path.dirname(os.path.abspath(__file__))
ICONE = os.path.join(PASTA, "gex.ico")


def titulo(t):
    print("")
    print("=== " + t + " " + "=" * max(0, 46 - len(t)))


def ler_ico(caminho):
    """Confere a estrutura do .ico sem depender de biblioteca de imagem."""
    try:
        d = open(caminho, "rb").read()
    except OSError as e:
        return "nao consegui abrir: " + str(e)
    if len(d) < 6:
        return "arquivo muito pequeno"
    reservado, tipo, n = struct.unpack("<HHH", d[:6])
    if reservado != 0 or tipo != 1:
        return "cabecalho nao e de icone (reservado=%d tipo=%d)" % (reservado, tipo)
    tamanhos = []
    off = 6
    for _ in range(n):
        if off + 16 > len(d):
            return "lista de imagens truncada"
        w, h, _c, _r, _p, bits, tam, pos = struct.unpack("<BBBBHHII", d[off:off + 16])
        lado = w or 256
        if pos + tam > len(d):
            return "imagem %dx%d aponta para fora do arquivo" % (lado, lado)
        tamanhos.append("%dx%d/%dbits" % (lado, lado, bits))
        off += 16
    return "ok, %d imagens: %s" % (n, ", ".join(tamanhos))


def windows_le_o_icone(caminho):
    """Pergunta ao proprio Windows se ele consegue carregar o icone.

    Se o LoadImage falhar, o problema esta no arquivo e nao no atalho - e a
    unica forma de saber isso sem ficar no chute.
    """
    if os.name != "nt":
        return "nao testado (nao e Windows)"
    if not os.path.exists(caminho):
        return "arquivo nao existe"
    try:
        import ctypes
        user32 = ctypes.windll.user32
        IMAGE_ICON = 1
        LR_LOADFROMFILE = 0x00000010
        resultados = []
        for lado in (16, 32, 48, 256):
            h = user32.LoadImageW(None, caminho, IMAGE_ICON, lado, lado,
                                  LR_LOADFROMFILE)
            if h:
                resultados.append("%d:ok" % lado)
                user32.DestroyIcon(h)
            else:
                # GetLastError pelo kernel32: o ctypes.get_last_error() so
                # funciona em funcao declarada com use_last_error.
                erro = ctypes.windll.kernel32.GetLastError()
                resultados.append("%d:FALHOU(erro %d)" % (lado, erro))
        return " ".join(resultados)
    except Exception as e:
        return "erro ao testar: " + str(e)


def pastas_de_atalho():
    if os.name != "nt":
        return []
    appdata = os.environ.get("APPDATA", "")
    perfil = os.environ.get("USERPROFILE", "")
    candidatos = [
        ("area de trabalho", os.path.join(perfil, "Desktop")),
        ("area de trabalho (OneDrive)", os.path.join(perfil, "OneDrive", "Desktop")),
        ("menu iniciar", os.path.join(appdata, "Microsoft", "Windows",
                                      "Start Menu", "Programs")),
        ("barra de tarefas", os.path.join(appdata, "Microsoft", "Internet Explorer",
                                          "Quick Launch", "User Pinned", "TaskBar")),
    ]
    return [(nome, p) for nome, p in candidatos if p and os.path.isdir(p)]


def detalhes_do_lnk(caminhos):
    """Le alvo, argumentos e icone de cada atalho, via PowerShell."""
    if not caminhos:
        return {}
    linhas = ["$w = New-Object -ComObject WScript.Shell", "$saida = @()"]
    for c in caminhos:
        lit = "'" + c.replace("'", "''") + "'"
        linhas.append(
            "try{$s=$w.CreateShortcut(" + lit + ");"
            "$saida += [pscustomobject]@{arquivo=" + lit + ";"
            "alvo=$s.TargetPath;args=$s.Arguments;icone=$s.IconLocation}}"
            "catch{$saida += [pscustomobject]@{arquivo=" + lit + ";erro=$_.Exception.Message}}")
    linhas.append("$saida | ConvertTo-Json -Compress")
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-Command",
                            "; ".join(linhas)],
                           capture_output=True, text=True, timeout=90)
        if r.returncode != 0:
            return {"erro": (r.stderr or "").strip()[:400]}
        texto = (r.stdout or "").strip()
        if not texto:
            return {}
        dados = json.loads(texto)
        return dados if isinstance(dados, list) else [dados]
    except Exception as e:
        return {"erro": str(e)}


def main():
    titulo("computador")
    print("sistema :", platform.system(), platform.release(), platform.version())
    print("python  :", sys.version.split()[0])
    print("exe     :", sys.executable)
    print("pasta   :", PASTA)

    titulo("arquivos da pasta")
    for nome in ("abrir.py", "terminal.py", "painel.html", "gex.ico",
                 "GEX.bat", "CRIAR_ATALHO.bat", "criar_atalho.py"):
        p = os.path.join(PASTA, nome)
        if os.path.exists(p):
            print("  ok     %-22s %d bytes" % (nome, os.path.getsize(p)))
        else:
            print("  FALTA  %s" % nome)

    titulo("o arquivo de icone")
    print("estrutura        :", ler_ico(ICONE))
    print("o Windows carrega:", windows_le_o_icone(ICONE))

    titulo("atalhos encontrados")
    achados = []
    for nome, pasta in pastas_de_atalho():
        lnks = [f for f in os.listdir(pasta) if f.lower().endswith(".lnk")]
        nossos = [f for f in lnks if "gex" in f.lower() or "terminal" in f.lower()]
        print("  %-28s %d atalhos, nossos: %s"
              % (nome, len(lnks), ", ".join(nossos) if nossos else "nenhum"))
        achados += [os.path.join(pasta, f) for f in nossos]
    if not achados and os.name == "nt":
        print("  nenhum atalho nosso encontrado")

    if achados:
        titulo("para onde cada atalho aponta")
        info = detalhes_do_lnk(achados)
        if isinstance(info, dict) and "erro" in info:
            print("  nao consegui ler:", info["erro"])
        else:
            for item in info:
                print("")
                print("  arquivo:", item.get("arquivo"))
                if item.get("erro"):
                    print("    erro :", item["erro"])
                    continue
                print("    alvo :", item.get("alvo") or "(vazio)")
                print("    args :", item.get("args") or "(vazio)")
                print("    icone:", item.get("icone") or "(vazio)")

    titulo("o terminal esta no ar?")
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.8)
            no_ar = s.connect_ex(("127.0.0.1", 8777)) == 0
        print("porta 8777:", "respondendo" if no_ar else "sem resposta")
    except OSError as e:
        print("porta 8777: erro ao testar -", e)

    print("")
    print("=== fim do relatorio ===")
    return 0


if __name__ == "__main__":
    import relatorio

    with relatorio.capturar("relatorio_diagnostico.txt"):
        codigo = main()

    if os.name == "nt":
        try:
            input("aperte ENTER para fechar...")
        except (EOFError, KeyboardInterrupt):
            pass
    sys.exit(codigo)
