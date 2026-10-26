"""Cria o atalho do Terminal GEX na area de trabalho e no menu iniciar.

Por que em Python e nao em .bat: montar o comando do PowerShell dentro do cmd
exige aspas dentro de aspas e parenteses dentro de "for /f in (...)", que e
onde o interpretador do cmd quebra. Aqui o caminho de cada coisa e conhecido
sem gambiarra - sys.executable diz onde o python.exe esta - e o script do
PowerShell e gravado em arquivo, entao nao existe problema de aspas.

O atalho aponta para o python.exe, nao para o GEX.bat. O Windows resolve
atalho de .bat ate o cmd.exe e fixa o icone do cmd na barra de tarefas,
descartando o icone configurado.

Uso:
    python criar_atalho.py
    python criar_atalho.py --simular    (mostra o que faria, sem fazer)
"""

import os
import subprocess
import sys
import tempfile

PASTA = os.path.dirname(os.path.abspath(__file__))
ALVO = os.path.join(PASTA, "abrir.py")
ICONE = os.path.join(PASTA, "gex.ico")
NOME = "Terminal GEX"
DESCRICAO = "Terminal GEX - niveis de gamma"


def ps_texto(s):
    """Literal de string do PowerShell. Aspas simples dobram para escapar."""
    return "'" + str(s).replace("'", "''") + "'"


def pasta_do_shell(chave):
    """Caminho de pasta especial lido do registro.

    Nao da para montar na mao como USERPROFILE mais Desktop: quem usa OneDrive
    tem a area de trabalho redirecionada, e o atalho iria para um lugar que o
    usuario nao ve.
    """
    import winreg
    caminhos = [
        (winreg.HKEY_CURRENT_USER,
         r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders"),
        (winreg.HKEY_CURRENT_USER,
         r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders"),
    ]
    for raiz, sub in caminhos:
        try:
            with winreg.OpenKey(raiz, sub) as k:
                valor, _ = winreg.QueryValueEx(k, chave)
            valor = os.path.expandvars(valor)
            if valor and os.path.isdir(valor):
                return valor
        except OSError:
            continue
    return None


def area_de_trabalho():
    return (pasta_do_shell("Desktop")
            or os.path.join(os.environ.get("USERPROFILE", ""), "Desktop"))


def menu_iniciar():
    base = pasta_do_shell("Programs")
    if base:
        return base
    appdata = os.environ.get("APPDATA", "")
    return os.path.join(appdata, "Microsoft", "Windows", "Start Menu", "Programs")


def script_powershell(destinos, exe):
    """Monta o .ps1 que cria os atalhos."""
    linhas = [
        "$ErrorActionPreference = 'Stop'",
        "$w = New-Object -ComObject WScript.Shell",
    ]
    for lnk in destinos:
        linhas += [
            "$s = $w.CreateShortcut(" + ps_texto(lnk) + ")",
            "$s.TargetPath = " + ps_texto(exe),
            # as aspas em volta do caminho do script protegem pasta com espaco
            "$s.Arguments = " + ps_texto('"' + ALVO + '"'),
            "$s.WorkingDirectory = " + ps_texto(PASTA),
            "$s.Description = " + ps_texto(DESCRICAO),
            "$s.WindowStyle = 1",
        ]
        if os.path.exists(ICONE):
            linhas.append("$s.IconLocation = " + ps_texto(ICONE + ",0"))
        linhas += [
            "$s.Save()",
            "Write-Host ('  criado: ' + " + ps_texto(lnk) + ")",
        ]
    return "\n".join(linhas) + "\n"


def limpar_cache_de_icone():
    """Pede ao Windows para reler os icones.

    Sem isso o Explorer pode continuar mostrando o icone antigo de um atalho
    que acabou de mudar, porque ele guarda os icones em cache. O ie4uinit vem
    com o Windows.
    """
    for argumento in ("-show", "-ClearIconCache"):
        try:
            subprocess.run(["ie4uinit.exe", argumento], timeout=20,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except (OSError, subprocess.SubprocessError):
            continue
    return False


def main():
    simular = "--simular" in sys.argv

    if os.name != "nt" and not simular:
        print("Este script cria atalho do Windows, e aqui nao e Windows.")
        return 1

    if not os.path.exists(ALVO):
        print("Nao achei o abrir.py em", PASTA)
        return 1

    exe = sys.executable
    # pythonw.exe nao abre janela, e sem janela o usuario nao ve erro nenhum.
    if os.path.basename(exe).lower() == "pythonw.exe":
        candidato = os.path.join(os.path.dirname(exe), "python.exe")
        if os.path.exists(candidato):
            exe = candidato

    if simular and os.name != "nt":
        destinos = [os.path.join("C:\\Users\\voce\\Desktop", NOME + ".lnk"),
                    os.path.join("C:\\Users\\voce\\Menu Iniciar", NOME + ".lnk")]
    else:
        destinos = [os.path.join(area_de_trabalho(), NOME + ".lnk"),
                    os.path.join(menu_iniciar(), NOME + ".lnk")]

    print("")
    print("   Python:  ", exe)
    print("   Script:  ", ALVO)
    print("   Icone:   ", ICONE if os.path.exists(ICONE)
          else "(nao encontrado - o atalho fica sem icone)")
    print("")

    ps = script_powershell(destinos, exe)

    if simular:
        print("   --- script do PowerShell que seria executado ---")
        print(ps)
        return 0

    arquivo = os.path.join(tempfile.gettempdir(), "gex_atalho.ps1")
    # BOM para o PowerShell 5.1 ler como UTF-8, caso o nome do usuario tenha
    # acento no caminho.
    with open(arquivo, "w", encoding="utf-8-sig") as f:
        f.write(ps)

    try:
        r = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy",
                            "Bypass", "-File", arquivo],
                           capture_output=True, text=True, timeout=120)
    except OSError as e:
        print("   Nao consegui chamar o PowerShell:", e)
        return 1
    finally:
        try:
            os.remove(arquivo)
        except OSError:
            pass

    if r.stdout:
        print(r.stdout.rstrip())
    if r.returncode != 0:
        print("   O PowerShell falhou:")
        print((r.stderr or "").rstrip()[:1500])
        return 1

    feitos = [d for d in destinos if os.path.exists(d)]
    if not feitos:
        print("   O PowerShell terminou sem erro, mas o atalho nao apareceu.")
        return 1

    limpar_cache_de_icone()

    print("")
    print("   ========================================")
    print("    AGORA FIXE NA BARRA DE TAREFAS")
    print("   ========================================")
    print("")
    print("   1. Va na area de trabalho")
    print("   2. Botao direito em \"" + NOME + "\"")
    print("   3. No Windows 11, clique em \"Mostrar mais opcoes\"")
    print("   4. Clique em \"Fixar na barra de tarefas\"")
    print("")
    print("   Se voce fixou antes a versao que virou icone de cmd,")
    print("   desafixe aquela primeiro.")
    print("")
    print("   O icone tambem foi para o menu iniciar: da para digitar")
    print("   \"Terminal GEX\" no menu e fixar de la.")
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
