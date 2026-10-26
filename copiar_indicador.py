"""Copia o indicador do TradingView para a area de transferencia.

Le a versao direto do arquivo .pine em vez de ter o numero escrito aqui. Com o
numero fixo, cada mudanca no indicador exigia lembrar de atualizar este texto
tambem - e foi exatamente o que nao aconteceu: o aviso ficou falando de uma
versao anterior.

Uso:
    python copiar_indicador.py
"""

import os
import re
import sys

PASTA = os.path.dirname(os.path.abspath(__file__))
ARQUIVO = os.path.join(PASTA, "indicadores", "tradingview_gex.pine")


def versao_do_arquivo(texto):
    m = re.search(r'^VERSAO\s*=\s*"([^"]+)"', texto, re.M)
    return m.group(1) if m else None


def main():
    if not os.path.exists(ARQUIVO):
        print("")
        print("   Nao achei o arquivo:")
        print("   " + ARQUIVO)
        print("")
        print("   Rode ATUALIZAR.bat para baixar o codigo mais novo.")
        return 1

    with open(ARQUIVO, encoding="utf-8") as f:
        codigo = f.read()

    import relatorio
    copiou = relatorio.para_area_de_transferencia(codigo)

    versao = versao_do_arquivo(codigo)
    linhas = codigo.count("\n") + 1

    print("")
    print("   ========================================")
    if copiou:
        print("    INDICADOR COPIADO")
    else:
        print("    NAO CONSEGUI COPIAR")
    print("   ========================================")
    print("")
    print("   arquivo :", ARQUIVO)
    print("   tamanho :", linhas, "linhas,", len(codigo), "caracteres")
    print("   versao  :", ("v" + versao) if versao else "(nao identificada)")
    print("")

    if not copiou:
        print("   Abra o arquivo acima no Bloco de Notas,")
        print("   aperte CTRL+A e depois CTRL+C.")
        print("")
        return 1

    print("   Agora no TradingView:")
    print("")
    print("   1. Abra o Pine Editor, no rodape do grafico")
    print("   2. Clique no meio do codigo")
    print("   3. CTRL+A para selecionar tudo, e DELETE")
    print("   4. CTRL+V para colar o novo")
    print("   5. Clique em Save, e depois em Add to chart")
    print("")
    if versao:
        print("   No grafico tem que aparecer o aviso \"GEX v" + versao + "\".")
        print("   Se aparecer um numero menor, a colagem nao pegou:")
        print("   provavelmente sobrou codigo antigo no editor.")
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
