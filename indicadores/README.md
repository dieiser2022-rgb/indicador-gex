# Indicadores

Indicadores próprios para plotar os níveis de gamma na plataforma de gráficos.
Eles recebem a linha de dados gerada pelo terminal — não calculam nada por
conta própria, e não dependem de nenhum serviço de terceiros.

## TradingView — `tradingview_gex.pine`

### Instalar (uma vez)

1. Abra o TradingView e clique em **Pine Editor**, no rodapé da tela.
2. Apague o conteúdo que vier por padrão.
3. Cole todo o conteúdo de `tradingview_gex.pine`.
4. Clique em **Salvar**, dê um nome, e depois em **Adicionar ao gráfico**.

### Usar (a cada atualização dos níveis)

1. No terminal, escolha o ticker (`NQ1!` para o TradingView) e clique em
   **TradingView** na caixa *Gerar GEX*.
2. Clique em **copiar a linha**.
3. No TradingView, abra as configurações do indicador (ícone de engrenagem).
4. Cole no campo **Cole os dados aqui** e confirme.

As linhas aparecem no gráfico com o rótulo à direita.

### Formato aceito

```
$NQ1!: Call Resistance, 30100, Put Support, 30000, HVL, 30075, 1D Min, 29691.92, ...
```

Pares `nome, valor` separados por vírgula. O prefixo do ticker é opcional.

Três coisas que o indicador tolera de propósito:

- **A ordem não importa.** Ele procura cada nível pelo nome, não pela posição.
- **Campo faltando é ignorado.** Em fim de semana não existem contratos 0DTE,
  então esses campos não vêm — e os outros continuam corretos.
- **Espaços e maiúsculas não importam.** `call resistance` e
  `Call Resistance` são lidos igual.

### Níveis reconhecidos

| Nome no texto | O que é | Cor padrão |
|---|---|---|
| `Call Resistance` | parede de call | verde, linha cheia |
| `Put Support` | parede de put | vermelho, linha cheia |
| `HVL` | inversão gama | amarelo, tracejada |
| `Call Resistance 0DTE` | parede de call de hoje | verde, pontilhada |
| `Put Support 0DTE` | parede de put de hoje | vermelho, pontilhada |
| `HVL 0DTE` | inversão gama de hoje | amarelo, pontilhada |
| `Gamma Wall 0DTE` | maior concentração de hoje | roxo, linha cheia |
| `1D Min` e `1D Max` | faixa esperada do dia | cinza, pontilhada |
| `GEX 1` a `GEX 10` | strikes de maior concentração | azul, pontilhada |

### O que dá para configurar

São 48 ajustes, agrupados nas opções do indicador.

**Por tipo de nível** — paredes, HVL, 0DTE, faixa do dia e GEX cada um tem o
seu grupo, com cor, estilo da linha (cheia, tracejada ou pontilhada),
espessura, e se mostra ou não o rótulo. Paredes e HVL deixam trocar o texto
também: se preferir chamar `HVL` de `Inversão`, é só escrever.

**Linhas, em geral** — quanto a linha se estende para trás e para frente, se
estende até a borda do gráfico (direita, os dois lados, ou nenhum) e a
transparência.

**Rótulos, em geral** — posição (direita ou esquerda), forma (etiqueta com
fundo ou somente o texto), distância, tamanho (de `tiny` a `large`), se mostra
o preço junto do nome, transparência do fundo, e a cor do texto.

O texto dos rótulos vem **preto** por padrão (opção *Usar uma cor única para
todo texto*, ligada). Para voltar ao comportamento antigo, em que cada rótulo
sai na cor da própria linha, desligue essa opção. Para outra cor fixa, troque
em *Cor única do texto*.

**Zona entre as paredes** — sombreia a região entre a parede de call e a de
put. Vem desligado; ligue em *Zona entre as paredes* se quiser o efeito.

**Aviso de tela** — a mensagem que aparece quando falta colar os dados pode ser
desligada.

### Se não compilar

O Pine Script só é validado pelo próprio TradingView, então pode haver algum
ajuste de sintaxe na primeira vez. O editor aponta a linha do erro — mande a
mensagem e a linha que o ajuste é rápido.

Dois pontos que são os candidatos mais prováveis:

- `input.text_area` pode não existir em versões antigas do Pine. A alternativa
  é trocar por `input.string`.
- Se `array.new_line()` reclamar, a forma nova é `array.new<line>()`.

## MetaTrader 5 e NinjaTrader

Ainda não feitos. O terminal já gera a linha de dados para eles — falta
escrever o indicador de cada plataforma, em MQL5 e em C#.
