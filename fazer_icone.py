"""Gera gex.ico, o icone do atalho da barra de tarefas.

Python puro, so com struct. Nenhuma biblioteca de imagem envolvida.

O desenho e simples de proposito: fundo escuro arredondado com tres linhas -
verde em cima (parede de call), ambar no meio (inversao gama) e vermelha
embaixo (parede de put). Em 16 pixels qualquer detalhe fino desaparece, e tres
barras coloridas ainda sao reconheciveis.

Para refazer o icone:
    python fazer_icone.py
"""

import os
import struct

TAMANHOS = (16, 20, 24, 32, 40, 48, 64, 128, 256)

FUNDO = (13, 20, 35)
BORDA = (56, 189, 248)
VERDE = (74, 222, 128)
AMBAR = (251, 191, 36)
VERMELHO = (248, 113, 113)
PRECO = (226, 232, 240)

AMOSTRAS = 4  # subpixels por lado, para suavizar a borda arredondada


def dentro_arredondado(x, y, lado, raio):
    """Diz se o ponto esta dentro de um quadrado de cantos arredondados."""
    menor = raio
    maior = lado - raio
    cx = menor if x < menor else (maior if x > maior else x)
    cy = menor if y < menor else (maior if y > maior else y)
    if cx == x and cy == y:
        return True
    dx = x - cx
    dy = y - cy
    return dx * dx + dy * dy <= raio * raio


def faixa(n, de, ate):
    """Converte fracao da altura em linhas de pixel, sempre com 1 no minimo."""
    a = int(round(de * n))
    b = int(round(ate * n))
    if b <= a:
        b = a + 1
    return a, b


def desenhar(n):
    """Devolve a imagem como lista de linhas de (R, G, B, A), de cima para baixo."""
    raio = max(2.0, n * 0.22)
    img = []

    # Linhas do desenho, em fracao da altura. Ordem: de cima para baixo.
    linhas = [
        (faixa(n, 0.25, 0.32), VERDE),
        (faixa(n, 0.46, 0.53), AMBAR),
        (faixa(n, 0.67, 0.74), VERMELHO),
    ]
    x_de = int(round(n * 0.17))
    x_ate = int(round(n * 0.83))

    # Coluna de preco no meio, ligando as duas paredes. Some em icone pequeno,
    # onde ela viraria uma sujeira de um pixel.
    col = n >= 32
    col_de = int(round(n * 0.47))
    col_ate = int(round(n * 0.53))
    col_topo = int(round(n * 0.22))
    col_base = int(round(n * 0.78))

    # Tracejado so faz sentido com largura suficiente para o olho separar.
    tracejar = n >= 40
    passo = max(2, int(round(n * 0.07)))

    for y in range(n):
        linha = []
        for x in range(n):
            # cobertura do fundo, por amostragem, para a borda nao serrilhar
            cobertos = 0
            for sy in range(AMOSTRAS):
                for sx in range(AMOSTRAS):
                    px = x + (sx + 0.5) / AMOSTRAS
                    py = y + (sy + 0.5) / AMOSTRAS
                    if dentro_arredondado(px, py, n, raio):
                        cobertos += 1
            alfa = cobertos / float(AMOSTRAS * AMOSTRAS)
            if alfa == 0:
                linha.append((0, 0, 0, 0))
                continue

            cor = FUNDO

            # borda clara de 1 pixel, so nos icones maiores
            if n >= 32 and 0 < alfa < 1:
                cor = BORDA

            if col and col_de <= x < col_ate and col_topo <= y < col_base:
                cor = PRECO

            for (a, b), c in linhas:
                if a <= y < b and x_de <= x < x_ate:
                    vago = tracejar and c == AMBAR and ((x - x_de) // passo) % 2
                    if not vago:
                        cor = c

            linha.append((cor[0], cor[1], cor[2], int(round(alfa * 255))))
        img.append(linha)
    return img


def bmp_de(img):
    """Empacota a imagem como DIB de 32 bits, do jeito que o .ico espera.

    Tres detalhes do formato que, se faltarem, o Windows mostra icone branco:
    a altura do cabecalho e o dobro da real, os pixels vao de baixo para cima
    em BGRA, e a mascara AND tem que existir mesmo sem uso, com as linhas
    completadas para multiplo de 4 bytes.
    """
    n = len(img)
    cabecalho = struct.pack("<IiiHHIIiiII", 40, n, n * 2, 1, 32, 0,
                            n * n * 4, 0, 0, 0, 0)
    corpo = bytearray()
    for y in range(n - 1, -1, -1):
        for (r, g, b, a) in img[y]:
            corpo += bytes((b, g, r, a))

    bytes_linha = ((n + 31) // 32) * 4  # 1 bit por pixel, linha alinhada em 4
    mascara = bytes(bytes_linha * n)
    return cabecalho + bytes(corpo) + mascara


def main():
    imagens = [(n, bmp_de(desenhar(n))) for n in TAMANHOS]

    saida = bytearray(struct.pack("<HHH", 0, 1, len(imagens)))
    deslocamento = 6 + 16 * len(imagens)
    for n, dados in imagens:
        # 256 nao cabe em um byte: o formato usa 0 para dizer 256
        lado = 0 if n >= 256 else n
        saida += struct.pack("<BBBBHHII", lado, lado, 0, 0, 1, 32,
                             len(dados), deslocamento)
        deslocamento += len(dados)
    for _, dados in imagens:
        saida += dados

    destino = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gex.ico")
    with open(destino, "wb") as f:
        f.write(saida)
    print("gex.ico gerado:", len(saida), "bytes,", len(imagens), "tamanhos")


if __name__ == "__main__":
    main()
