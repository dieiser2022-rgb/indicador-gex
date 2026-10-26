"""Captura o que o script imprime e deixa pronto para colar no chat.

Motivo: copiar texto da janela preta do Windows e chato e pouco obvio - tem
que selecionar com o mouse e apertar ENTER, e quem nao sabe disso fica preso.
Entao o proprio script joga o relatorio na area de transferencia e grava num
arquivo de texto, e o usuario so precisa dar CTRL+V.

Uso:

    import relatorio
    with relatorio.capturar("relatorio_gex.txt"):
        print("...")      # sai na tela e vai para o buffer tambem
"""

import contextlib
import io
import os
import subprocess
import sys

PASTA = os.path.dirname(os.path.abspath(__file__))


class _Tee:
    """Escreve na tela e guarda uma copia."""

    def __init__(self, real):
        self.real = real
        self.buffer_texto = io.StringIO()

    def write(self, s):
        self.real.write(s)
        self.buffer_texto.write(s)
        return len(s)

    def flush(self):
        self.real.flush()

    def isatty(self):
        return getattr(self.real, "isatty", lambda: False)()


def para_area_de_transferencia(texto):
    """Copia para a area de transferencia do Windows. Devolve se deu certo."""
    if os.name != "nt":
        return False
    try:
        # O clip espera bytes na pagina de codigo do console. Os relatorios
        # sao escritos sem acento de proposito, entao cp1252 da conta; o
        # replace evita explodir se escapar algum caractere.
        subprocess.run(["clip"], input=texto.encode("cp1252", "replace"),
                       timeout=30, check=True)
        return True
    except (OSError, subprocess.SubprocessError):
        return False


@contextlib.contextmanager
def capturar(nome_arquivo="relatorio_gex.txt"):
    """Captura a saida, grava em arquivo e copia para a area de transferencia."""
    original = sys.stdout
    tee = _Tee(original)
    sys.stdout = tee
    try:
        yield
    finally:
        sys.stdout = original
        texto = tee.buffer_texto.getvalue()

        destino = os.path.join(PASTA, nome_arquivo)
        gravou = False
        try:
            with open(destino, "w", encoding="utf-8") as f:
                f.write(texto)
            gravou = True
        except OSError:
            pass

        copiou = para_area_de_transferencia(texto)

        print("")
        print("-" * 60)
        if copiou:
            print(" O relatorio JA ESTA COPIADO.")
            print(" Va no chat e aperte CTRL+V.")
        else:
            print(" Nao consegui copiar automaticamente.")
        if gravou:
            print("")
            print(" Tambem salvei em:")
            print("   " + destino)
            print(" Se precisar, abra esse arquivo e copie de la.")
        print("-" * 60)
