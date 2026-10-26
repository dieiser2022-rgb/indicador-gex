"""Limpa o cache de icones do Windows e reinicia o Explorer.

Para que serve: o Windows guarda os icones em um banco proprio, indexado pelo
caminho do arquivo. Se um atalho e criado apontando para um .bat (icone de
cmd) e depois recriado com o mesmo nome e outro icone, o Explorer continua
mostrando o icone antigo, porque le do cache e nao do arquivo.

O ie4uinit, que o criar_atalho.py chama, resolve os casos leves. Quando nao
resolve, o unico jeito e apagar os arquivos de cache - e eles so podem ser
apagados com o Explorer fechado, porque ficam em uso.

A tela pisca: a barra de tarefas e os icones desaparecem por uns segundos e
voltam. Nenhum arquivo seu e tocado, o cache se refaz sozinho.

Uso:
    python limpar_cache_icone.py
"""

import glob
import os
import subprocess
import sys
import time

LOCAL = os.environ.get("LOCALAPPDATA", "")


def arquivos_de_cache():
    padroes = [
        os.path.join(LOCAL, "IconCache.db"),
        os.path.join(LOCAL, "Microsoft", "Windows", "Explorer", "iconcache_*.db"),
    ]
    achados = []
    for p in padroes:
        achados += glob.glob(p)
    return achados


def rodar(*comando):
    try:
        return subprocess.run(comando, capture_output=True, text=True,
                              timeout=60).returncode
    except (OSError, subprocess.SubprocessError) as e:
        print("   falhou:", e)
        return 1


def main():
    if os.name != "nt":
        print("Este script e do Windows, e aqui nao e Windows.")
        return 1

    print("")
    print("   Limpando o cache de icones do Windows")
    print("")
    print("   A barra de tarefas vai desaparecer por alguns segundos")
    print("   e voltar sozinha. Nenhum arquivo seu e alterado.")
    print("")
    try:
        input("   aperte ENTER para comecar, ou feche a janela para desistir...")
    except (EOFError, KeyboardInterrupt):
        return 1

    alvos = arquivos_de_cache()
    print("")
    print("   arquivos de cache encontrados:", len(alvos))

    # A tentativa leve primeiro: as vezes resolve sem fechar o Explorer.
    print("   pedindo ao Windows para reler os icones...")
    rodar("ie4uinit.exe", "-show")

    print("   fechando o Explorer...")
    rodar("taskkill", "/f", "/im", "explorer.exe")
    time.sleep(1.5)

    # O try/finally garante que o Explorer volta mesmo se o apagar falhar.
    # Sem isso o usuario ficaria sem area de trabalho.
    apagados = 0
    try:
        for a in alvos:
            try:
                os.remove(a)
                apagados += 1
            except OSError:
                pass
        print("   apagados:", apagados, "de", len(alvos))
    finally:
        print("   reabrindo o Explorer...")
        try:
            subprocess.Popen(["explorer.exe"])
        except OSError:
            print("")
            print("   NAO CONSEGUI REABRIR O EXPLORER.")
            print("   Aperte CTRL+SHIFT+ESC, menu Arquivo,")
            print("   Executar nova tarefa, digite explorer e OK.")
            return 1

    time.sleep(2.5)
    print("")
    print("   Pronto.")
    print("")
    print("   Agora refaca o atalho e fixe de novo:")
    print("")
    print("   1. duplo clique em CRIAR_ATALHO.bat")
    print("   2. botao direito no atalho da area de trabalho")
    print("   3. Fixar na barra de tarefas")
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
