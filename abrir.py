"""Partida do Terminal GEX.

Este arquivo existe por um motivo bem especifico: o Windows nao aceita icone
proprio em atalho de .bat. Ele resolve o atalho ate o cmd.exe e fixa o icone
do cmd na barra de tarefas, ignorando o que foi configurado. Atalho que aponta
para o python.exe, sim, respeita o icone.

Entao toda a inteligencia que estava no GEX.bat mudou para ca:

- se o terminal ja esta no ar, nao tenta subir um segundo (daria erro de porta
  ocupada); so reabre o painel no navegador
- se algo falhar, mostra o erro e espera uma tecla, em vez de a janela fechar
  junto com a mensagem
- coloca titulo e icone na janela, quando o Windows permite

Uso:
    python abrir.py
"""

import os
import socket
import sys
import time
import traceback
import webbrowser

PORTA = 8777
ENDERECO = "http://localhost:" + str(PORTA)
PASTA = os.path.dirname(os.path.abspath(__file__))


def ja_esta_no_ar(porta=PORTA, segundos=0.6):
    """Abre uma conexao de verdade na porta para saber se alguem atende.

    Mais confiavel que ler a saida do netstat, que muda conforme o idioma do
    Windows e lista tambem conexoes que estao se encerrando.
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(segundos)
            return s.connect_ex(("127.0.0.1", porta)) == 0
    except OSError:
        return False


def enfeitar_janela():
    """Titulo e icone na janela do console. Silencioso se nao der.

    Usa ctypes, que vem com o Python. No Windows Terminal do Windows 11 o
    icone pode nao mudar, porque a janela real nao e mais a do console - mas
    a tentativa nao custa nada e nao quebra nada.
    """
    if os.name != "nt":
        return
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        user32 = ctypes.windll.user32
        kernel32.SetConsoleTitleW("Terminal GEX - niveis de gamma")

        ico = os.path.join(PASTA, "gex.ico")
        if not os.path.exists(ico):
            return
        janela = kernel32.GetConsoleWindow()
        if not janela:
            return

        IMAGE_ICON = 1
        LR_LOADFROMFILE = 0x00000010
        WM_SETICON = 0x0080
        ICON_SMALL, ICON_BIG = 0, 1
        for tamanho, qual in ((16, ICON_SMALL), (32, ICON_BIG)):
            h = user32.LoadImageW(None, ico, IMAGE_ICON, tamanho, tamanho,
                                  LR_LOADFROMFILE)
            if h:
                user32.SendMessageW(janela, WM_SETICON, qual, h)
    except Exception:
        pass


def esperar_tecla():
    """Segura a janela aberta para dar tempo de ler o erro."""
    print("")
    try:
        input("   aperte ENTER para fechar esta janela...")
    except (EOFError, KeyboardInterrupt):
        pass


def main():
    os.chdir(PASTA)
    if PASTA not in sys.path:
        sys.path.insert(0, PASTA)
    enfeitar_janela()

    print("")
    print("   ========================================")
    print("     TERMINAL GEX - niveis de gamma")
    print("   ========================================")
    print("")

    if ja_esta_no_ar():
        print("   O terminal ja estava rodando.")
        print("   Abrindo o painel no navegador...")
        webbrowser.open(ENDERECO)
        time.sleep(2)
        return 0

    print("   Deixe esta janela aberta: ela e o motor do painel.")
    print("   Se fechar, o painel para de responder.")
    print("")

    try:
        import terminal
    except Exception:
        print("   Nao consegui carregar o terminal.py:")
        print("")
        traceback.print_exc()
        esperar_tecla()
        return 1

    terminal.main()
    return 0


if __name__ == "__main__":
    try:
        codigo = main()
    except KeyboardInterrupt:
        print("")
        print("   encerrado.")
        codigo = 0
    except Exception:
        print("")
        print("   O terminal fechou com erro:")
        print("")
        traceback.print_exc()
        esperar_tecla()
        codigo = 1
    sys.exit(codigo)
