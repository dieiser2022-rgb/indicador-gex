"""Conserta o icone de um atalho JA fixado na barra de tarefas.

Por que existe: o Windows nao deixa um programa fixar nada na barra de
tarefas - isso e proposital, para evitar que instaladores se enfiem la. Mas
quando o usuario fixa, o Windows grava um .lnk numa pasta conhecida. Esse
arquivo da para editar.

Entao a divisao de trabalho fica assim:

    o usuario fixa (com qualquer icone que o Windows escolher)
    este script reescreve o icone do atalho fixado e manda o Explorer reler

Isso funciona independente do motivo pelo qual o icone saiu errado, o que e
melhor que tentar adivinhar o motivo.

Uso:
    python arrumar_icone.py
"""

import glob
import json
import os
import subprocess
import sys
import time

PASTA = os.path.dirname(os.path.abspath(__file__))
ICONE = os.path.join(PASTA, "gex.ico")
APPDATA = os.environ.get("APPDATA", "")
LOCAL = os.environ.get("LOCALAPPDATA", "")
PERFIL = os.environ.get("USERPROFILE", "")

FIXADOS = os.path.join(APPDATA, "Microsoft", "Internet Explorer",
                       "Quick Launch", "User Pinned", "TaskBar")


def ps(*linhas):
    """Roda PowerShell e devolve (codigo, saida, erro)."""
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy",
                            "Bypass", "-Command", "; ".join(linhas)],
                           capture_output=True, text=True, timeout=120)
        return r.returncode, (r.stdout or "").strip(), (r.stderr or "").strip()
    except (OSError, subprocess.SubprocessError) as e:
        return 1, "", str(e)


def lit(s):
    return "'" + str(s).replace("'", "''") + "'"


def pastas_de_atalho():
    candidatos = [
        ("barra de tarefas", FIXADOS),
        ("area de trabalho", os.path.join(PERFIL, "Desktop")),
        ("area de trabalho (OneDrive)", os.path.join(PERFIL, "OneDrive", "Desktop")),
        ("menu iniciar", os.path.join(APPDATA, "Microsoft", "Windows",
                                      "Start Menu", "Programs")),
    ]
    return [(n, p) for n, p in candidatos if p and os.path.isdir(p)]


def ler_atalhos(caminhos):
    """Alvo, argumentos e icone de cada .lnk, de uma vez."""
    if not caminhos:
        return []
    linhas = ["$w = New-Object -ComObject WScript.Shell", "$r = @()"]
    for c in caminhos:
        linhas.append(
            "try{$s=$w.CreateShortcut(" + lit(c) + ");"
            "$r += [pscustomobject]@{arquivo=" + lit(c) + ";alvo=$s.TargetPath;"
            "args=$s.Arguments;icone=$s.IconLocation}}catch{}")
    linhas.append("$r | ConvertTo-Json -Compress")
    codigo, saida, erro = ps(*linhas)
    if codigo != 0 or not saida:
        if erro:
            print("   aviso ao ler atalhos:", erro[:200])
        return []
    try:
        d = json.loads(saida)
    except ValueError:
        return []
    return d if isinstance(d, list) else [d]


def e_nosso(item):
    """Decide se o atalho e do Terminal GEX.

    Casa por tres sinais, porque o atalho pode ter sido criado pela versao que
    apontava para o .bat, pela que aponta para o python.exe, ou na mao pelo
    usuario com outro nome.
    """
    alvo = (item.get("alvo") or "").lower()
    args = (item.get("args") or "").lower()
    arq = os.path.basename(item.get("arquivo") or "").lower()
    pasta = PASTA.lower().replace("/", "\\")

    if "abrir.py" in args or "terminal.py" in args:
        return True
    if "gex.bat" in args or "gex.bat" in alvo:
        return True
    if pasta and pasta in args:
        return True
    if pasta and pasta in alvo:
        return True
    if "gex" in arq or "terminal gex" in arq:
        return True
    return False


def escrever_icone(caminhos):
    """Grava o IconLocation em cada atalho."""
    linhas = ["$ErrorActionPreference='Stop'",
              "$w = New-Object -ComObject WScript.Shell"]
    for c in caminhos:
        linhas += [
            "$s=$w.CreateShortcut(" + lit(c) + ")",
            "$s.IconLocation=" + lit(ICONE + ",0"),
            "$s.Save()",
            "Write-Host ('  icone gravado: ' + " + lit(c) + ")",
        ]
    return ps(*linhas)


def reiniciar_explorer():
    """Apaga o cache de icones e reabre o Explorer.

    Reescrever o .lnk nao basta: o Explorer le o icone do cache dele, nao do
    arquivo. O cache so pode ser apagado com o Explorer fechado.
    """
    alvos = glob.glob(os.path.join(LOCAL, "IconCache.db"))
    alvos += glob.glob(os.path.join(LOCAL, "Microsoft", "Windows", "Explorer",
                                    "iconcache_*.db"))
    try:
        subprocess.run(["taskkill", "/f", "/im", "explorer.exe"],
                       capture_output=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        pass
    time.sleep(1.5)
    apagados = 0
    try:
        for a in alvos:
            try:
                os.remove(a)
                apagados += 1
            except OSError:
                pass
    finally:
        # O Explorer precisa voltar de qualquer jeito, senao o usuario fica
        # sem barra de tarefas e sem area de trabalho.
        try:
            subprocess.Popen(["explorer.exe"])
        except OSError:
            print("")
            print("   NAO CONSEGUI REABRIR O EXPLORER.")
            print("   CTRL+SHIFT+ESC, menu Arquivo, Executar nova tarefa,")
            print("   digite explorer e OK.")
            return apagados, False
    time.sleep(3)
    return apagados, True


def main():
    if os.name != "nt":
        print("Este script e do Windows, e aqui nao e Windows.")
        return 1

    if not os.path.exists(ICONE):
        print("Nao achei o gex.ico em", PASTA)
        print("Rode:  python fazer_icone.py")
        return 1

    print("")
    print("   Procurando atalhos do Terminal GEX...")
    print("")

    todos = []
    for nome, pasta in pastas_de_atalho():
        lnks = sorted(glob.glob(os.path.join(pasta, "*.lnk")))
        todos += [(nome, c) for c in lnks]

    itens = ler_atalhos([c for _, c in todos])
    por_arquivo = {}
    for it in itens:
        por_arquivo[(it.get("arquivo") or "").lower()] = it

    nossos = []
    for nome, caminho in todos:
        it = por_arquivo.get(caminho.lower())
        if not it:
            continue
        if e_nosso(it):
            nossos.append((nome, caminho, it))

    if not nossos:
        print("   Nao achei nenhum atalho nosso.")
        print("")
        print("   Na barra de tarefas:", "existe" if os.path.isdir(FIXADOS)
              else "pasta nao encontrada")
        print("")
        print("   Fixe primeiro, depois rode este script de novo:")
        print("")
        print("   1. duplo clique em CRIAR_ATALHO.bat")
        print("   2. botao direito no atalho da area de trabalho")
        print("   3. Fixar na barra de tarefas")
        print("   4. duplo clique em ARRUMAR_ICONE.bat")
        print("")
        return 1

    fixado = False
    for nome, caminho, it in nossos:
        print("   [" + nome + "]", os.path.basename(caminho))
        print("      alvo :", it.get("alvo") or "(vazio)")
        print("      icone:", it.get("icone") or "(vazio)")
        if nome == "barra de tarefas":
            fixado = True

    print("")
    codigo, saida, erro = escrever_icone([c for _, c, _ in nossos])
    if saida:
        print(saida)
    if codigo != 0:
        print("   Falhou ao gravar o icone:")
        print(erro[:800])
        return 1

    print("")
    print("   Agora preciso fechar e reabrir o Explorer para ele")
    print("   reler os icones. A tela vai piscar por alguns segundos.")
    print("")
    try:
        input("   ENTER para continuar, ou feche a janela para parar aqui...")
    except (EOFError, KeyboardInterrupt):
        return 0

    apagados, ok = reiniciar_explorer()
    print("")
    print("   arquivos de cache apagados:", apagados)

    if not ok:
        return 1

    print("")
    if fixado:
        print("   Pronto. Olhe a barra de tarefas.")
    else:
        print("   Os atalhos foram corrigidos, mas nenhum esta fixado ainda.")
        print("   Fixe agora: botao direito no atalho da area de trabalho,")
        print("   Fixar na barra de tarefas. Se o icone vier errado, rode")
        print("   este script mais uma vez.")
    print("")
    return 0


if __name__ == "__main__":
    codigo = main()
    if os.name == "nt":
        try:
            input("   aperte ENTER para fechar...")
        except (EOFError, KeyboardInterrupt):
            pass
    sys.exit(codigo)
