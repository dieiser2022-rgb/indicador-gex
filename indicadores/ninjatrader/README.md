# GEX no NinjaTrader — plano e base de informação

Documento de partida para levar os níveis de gamma para o NinjaTrader. Escrito
no fim da sessão de 01/11/2026, antes de abrir uma sessão nova só para isso.
Nada aqui foi implementado ainda.

## O que se aproveita, e o que não

**Aproveita tudo do cálculo.** O Python continua sendo o cérebro: baixa a
CBOE, calcula paredes, HVL, key levels e converte para a escala do MNQ. O lado
NinjaTrader só **lê e desenha**. Nenhuma fórmula é reescrita em C#.

Isso não é só conveniência: reescrever Black-Scholes, a varredura de zero gamma
e o parsing OSI em C# seria duplicar a parte difícil, e as duas cópias
divergiriam na primeira correção.

**Não aproveita a interface.** O `painel.html` é HTML, CSS e JavaScript; o
NinjaTrader é C# com WPF. Não existe conversão automática. Essa é a única
parte que precisa nascer de novo — e o caminho A abaixo contorna até isso.

## As duas fontes de dados, e a armadilha entre elas

O painel desenhado pelo usuário mistura dois mundos, e eles têm atrasos
diferentes. Confundir isso produz níveis errados.

| | Opções / gamma | Futuro em tempo real |
|---|---|---|
| Fonte | CBOE, `delayed_quotes` | CME, dentro do NinjaTrader |
| Custo | grátis | assinatura do usuário, ~US$ 4/mês |
| Atraso | ~15 minutos | tempo real |
| Entrega | nosso Python, `/api/exportar` | só o NinjaTrader tem |
| Alimenta | heatmap, paredes, HVL, key levels, GEX líquido | tape, volume delta, preço do gráfico, status de conexão |

A assinatura da CME dá **futuros**, não opções. A cadeia de opções continua
vindo da CBOE, de graça e com atraso. Os dois mundos continuam existindo; o que
muda é que o lado do futuro passa a ser confiável e em tempo real.

### A armadilha do basis

O basis é `preço do futuro − spot do índice`, e é ele que converte os níveis do
NDX para a escala do MNQ. Hoje os dois lados vêm **atrasados em ~15 min**
(Yahoo para o `NQ=F`, CBOE para o NDX), então formam um par coerente.

Com a assinatura da CME, surge a tentação de usar o preço do NQ em tempo real
para calcular o basis. **Não fazer isso.** Um futuro ao vivo menos um índice de
15 minutos atrás não é o basis: é o basis mais o movimento do índice nesses 15
minutos. No Nasdaq isso desloca todos os níveis de uma vez, em dezenas de
pontos, e o erro é silencioso.

Regra: **basis sempre com os dois lados do mesmo instante.** O preço ao vivo da
CME serve para o gráfico e para o tape, não para converter níveis.

### Como o tape chega no painel

Se o painel for HTML dentro de um WebView2 (caminho A), a página não tem acesso
aos ticks do NinjaTrader. Quem tem é o C#. A ligação se faz com
`PostWebMessageAsJson` do WebView2: o AddOn empurra o tape e o volume delta
para dentro da página, e o JavaScript escuta.

Isso preserva a vantagem de poder testar a página no navegador: sem o
hospedeiro C#, ela simplesmente mostra a área de tape como indisponível, do
mesmo jeito que o `fontes.py` devolve vazio quando uma fonte está fora do ar.

Nota sobre a licença: dado de CME é licenciado para exibição ao assinante. Usar
dentro da máquina dele — NinjaTrader, e uma página local que o próprio
NinjaTrader hospeda — é uso normal. O que não se faz é o servidor Python
reemitir esse dado para fora da máquina.

## O contrato de dados

O NinjaTrader roda na mesma máquina que o terminal, então basta um GET em:

```
http://localhost:8777/api/exportar?ativo=MNQ&plataforma=ninjatrader&simbolo=NQ%3DF&dias=45
```

Resposta medida de verdade (valores de um teste, não inventados):

| Campo | Tipo | Exemplo | Para que serve |
|---|---|---|---|
| `pronto` | bool | `true` | se vier `false` ou faltar, ignorar o resto |
| `erro` | string | ausente | só aparece quando algo falhou |
| `valores` | objeto | ver abaixo | **o que importa**: nome do nível -> preço |
| `linha` | string | `$MNQ: Call Resistance, 29817.47, ...` | mesma coisa em texto, para colar à mão |
| `spot` | float | `28957.53` | preço do índice (NDX) |
| `preco_futuro` | float | `29175.0` | preço do futuro (NQ) |
| `basis` | float | `217.47` | `preco_futuro - spot`, já aplicado em `valores` |
| `indice` | string | `NDX` | de qual índice os níveis vieram |
| `contratos` | int | `556` | contratos usados no cálculo |
| `contratos_0dte` | int | `146` | quantos vencem hoje |
| `iv` | float | `0.19` | IV mediana |
| `aviso` | string | `""` | texto a exibir, ex. fim de semana sem 0DTE |

Os níveis em `valores` já vêm **na escala do MNQ** (basis somado). São 25 no
total quando tudo está disponível:

```
Call Resistance        Put Support
Call Resistance 2      Put Support 2
HVL
1D Min                 1D Max
Call Resistance 0DTE   Put Support 0DTE
HVL 0DTE               Gamma Wall 0DTE
GEX 1 .. GEX 10
GEX 1 0DTE .. GEX 5 0DTE
```

Regra para o C#: **não assumir que todos existem.** Em fim de semana os campos
0DTE não vêm; o `HVL` sai vazio quando a varredura não acha troca de sinal.
Percorrer o dicionário e desenhar o que chegou, como o indicador do
TradingView já faz.

Outras rotas úteis: `/api/estado` (teste rápido de "o terminal está no ar?") e
`/api/gamma?simbolo=NDX` (Net GEX, regime e o perfil por strike, caso o painel
no NinjaTrader queira mostrar isso).

## O que o usuário decidiu (01/11/2026)

Escopo definido por ele, em palavras dele: *"criar um terminal dentro do ninja
do 0, usando a nossa base pronta, e ele carrega automaticamente a cada 10 min,
ele plota automático no gráfico do ninja. Porém para o MT5 e o TradingView ele
vai funcionar igual o nosso terminal, a gente clica no botão para gerar o
código. Mas no NinjaTrader é tudo automático."*

Traduzindo em requisitos:

1. **Painel novo dentro do NinjaTrader**, desenhado do zero — não é o
   `painel.html` embutido como está. O visual vai ser diferente, e **ele vai
   mandar o desenho** do layout que quer.
2. **Atualização automática a cada 10 minutos**, sem clique.
3. **Plotagem automática no gráfico do NinjaTrader**, sem colar nada.
4. **MT5 e TradingView continuam como são hoje**: botão no nosso terminal gera
   a linha, o usuário cola. Nada muda nesse fluxo.

Consequência: são **dois artefatos** de NinjaScript, não um. Um `Indicator`
para desenhar no gráfico e uma janela de AddOn para o painel. Ambos leem a
mesma rota `/api/exportar`.

## O heatmap de GEX, alinhado ao gráfico

O usuário pediu uma grade de GEX **parelha com o gráfico**: cada linha é um
strike, e a linha do strike 18.600 tem que ficar na mesma altura que 18.600 no
gráfico de preço, com a linha de preço por cima.

**Os dados já existem.** Basta agrupar `usaveis` por `(dias, strike)` em vez de
só por `strike`, e aplicar a mesma fórmula de GEX em dólares que o
`gex_por_strike` usa. Protótipo rodado em 01/11/2026 produziu 21 strikes × 10
vencimentos, 210 células. Falta apenas uma rota que devolva a matriz e o
desenho na tela.

### A pergunta que define o trabalho: o que são as colunas?

| Colunas | O que mostra | Precisa de histórico? |
|---|---|---|
| **Vencimento** | como o gamma se distribui entre 0DTE, 1d, 2d, 7d... | não — pronto hoje |
| **Hora do dia** | como o GEX de cada strike mudou ao longo da sessão | **sim** |

No esboço dele a linha de preço atravessa a grade da esquerda para a direita, o
que sugere **hora do dia**. Isso traz a mesma dependência da área 6: o terminal
precisa coletar desde a abertura, senão as colunas da manhã ficam vazias.

Vale notar por que a versão por hora tem conteúdo real: o open interest é fixo
durante o dia, mas o GEX em dólares depende do spot (`gamma × OI × 100 ×
spot² × 0,01`) e da distância do strike ao preço. Conforme o preço anda, o mapa
de calor muda de verdade — não é redundante.

### O conflito de escala vertical

O gráfico de preço cobre a faixa do dia, algo como 1% a 2%. Os strikes que
calculamos cobrem ±12% (`FAIXA` no `gamma_cboe.py`). Dividir o mesmo eixo entre
os dois obriga a escolher:

1. **Mostrar só os strikes que cabem na janela do gráfico** — recomendado. É o
   que o esboço parece mostrar, e mantém as duas partes legíveis.
2. Mostrar todos os strikes e comprimir o gráfico numa faixa fina — o preço
   viraria uma linha quase reta, perdendo utilidade.

O alinhamento em si é a parte fácil: o painel já desenha candles e níveis em
canvas com uma função própria de preço para pixel. Usar a mesma função nas duas
metades resolve, desde que a conversão do basis seja aplicada antes (os strikes
estão na escala do índice, o gráfico na do futuro).

## Três caminhos

| | O que é | Esforço | Risco | Reescreve a interface? |
|---|---|---|---|---|
| **C** | Indicador que desenha os níveis no gráfico | pequeno | baixo | não tem interface |
| **A** | Janela de AddOn com WebView2 abrindo uma página nossa | pequeno | médio | não, só uma página HTML nova |
| **B** | Painel nativo em WPF | grande | alto | sim, do zero em XAML |

**A decisão de "painel do zero" não implica em WPF.** Como o visual vai ser
diferente, a opção A deixa de ser "mostrar o `painel.html`" e passa a ser
"mostrar uma página nova, feita para o desenho dele" — por exemplo
`painel_ninja.html`, servida pelo mesmo servidor Python numa rota nova.

Comparando as duas formas de fazer o painel novo:

| | WebView2 + HTML novo (A) | WPF nativo (B) |
|---|---|---|
| Linguagem da tela | HTML/CSS/JS, que já dominamos neste projeto | XAML e data binding, do zero |
| Posso testar? | sim, abrindo no navegador | não, só o NinjaTrader diz |
| C# necessário | janela fina hospedando o WebView2 | todo o painel |
| Dependência extra | referência do WebView2 no compilador | nenhuma |
| Gráfico e barras dentro do painel | canvas, como já fazemos | desenhar na mão em WPF |

**Recomendação: A.** O ganho decisivo é poder **testar a tela no navegador**
antes de levar para o NinjaTrader. O C# fica reduzido a uma janela fina, que é
pouca coisa para escrever às cegas. Em WPF, cada ajuste de visual exigiria uma
rodada de compilação no computador do usuário — e o histórico do projeto mostra
o que isso custa (quatro rodadas no Pine, quatro no ícone da barra).

O preço de A é a referência do WebView2 no compilador do NinjaTrader. Se isso
se mostrar inviável, B continua possível, mas aí vale reduzir o escopo do
painel.

**C — indicador de gráfico.** Uma classe que herda de `Indicator`, busca o
JSON e desenha linhas horizontais com rótulo. C# puro, nenhuma biblioteca
externa. É o que mais serve para operar, porque os níveis aparecem no gráfico
do MNQ onde a decisão acontece.

**A — AddOn com navegador embutido.** `AddOnBase` cria o item no menu "Novo",
abre uma `NTWindow` e dentro dela um WebView2 apontando para
`http://localhost:8777`. O painel aparece dentro do NinjaTrader exatamente como
é hoje, com robôs e animações. O risco mora em adicionar a referência do
WebView2 ao compilador do NinjaTrader — o runtime em si já vem com o Edge no
Windows 10 e 11.

**B — WPF nativo.** Mais leve e sem navegador, mas joga fora todo o visual já
construído. Só vale se A se mostrar inviável.

**Ordem recomendada: C primeiro, depois A.** Fazer A de cara significa que, se
der erro, há três suspeitos ao mesmo tempo: o nosso código, a referência do
WebView2 e o NinjaTrader. O C isola o problema no nosso código — e entrega
logo o requisito 3, que é o que mexe com a operação.

Dentro de A, a mesma lógica: montar e aprovar o `painel_ninja.html` **no
navegador** primeiro, com o desenho dele na mão. Só depois embrulhar na janela
do NinjaTrader. Assim o visual já está resolvido quando o C# entrar em cena.

## Riscos conhecidos, antes de começar

**NinjaScript não compila no sandbox do agente.** Mesma situação do Pine
Script: o código é escrito às cegas e só o NinjaTrader diz se compila. No Pine
foram quatro rodadas de erro. C# é mais rigoroso que Pine, então esperar
algumas idas e vindas é realista — e vale escrever em pedaços pequenos,
compilando cada um, em vez de entregar tudo de uma vez.

**Onde o erro aparece:** no menu do NinjaTrader em português, o editor é
*Ferramentas > Editor NinjaScript*, e as mensagens de compilação saem em
*Saída NinjaScript*. É de lá que a mensagem de erro deve ser copiada.

**Onde o arquivo mora:** os fontes do usuário ficam em
`Documents\NinjaTrader 8\bin\Custom\Indicators\` (indicadores) e
`...\bin\Custom\AddOns\` (AddOns). Vale confirmar com ele, porque a pasta muda
se o NinjaTrader foi instalado em outro lugar.

**Chamada de rede não pode travar a interface.** Buscar o JSON na thread do
gráfico congela o NinjaTrader. Tem que ser assíncrono, com timeout curto, e
falhar em silêncio quando o terminal estiver fechado — mesma filosofia do
`fontes.py`, onde fonte fora do ar devolve vazio em vez de derrubar tudo.

## Já respondido pelo usuário

- **Automático**, sem colar nada, tanto no gráfico quanto no painel.
- **A cada 15 minutos**, decidido em 01/11/2026. Casa com o ritmo de publicação
  da CBOE: buscar mais vezes traria o mesmo dado.
- **Mesmo repositório**, nesta pasta.
- **MT5 e TradingView ficam manuais**, como já são.

## Perguntas abertas

1. **O desenho do layout.** Ele disse que vai mandar. Sem isso o painel não
   começa — e é bom que seja assim: no painel web, construir a partir do
   desenho dele numerado por área funcionou muito melhor que adivinhar.
2. **Indicador do MT5.** Ele falou que no MT5 "funciona igual ao nosso
   terminal, clica no botão para gerar o código". Hoje o terminal gera a linha
   de texto para MT5, mas **o indicador de MQL5 não existe** — só o do
   TradingView. Confirmar se ele espera esse indicador também, ou se a linha de
   texto basta por enquanto.
3. **O que o painel do NinjaTrader mostra.** O desenho vai dizer, mas vale
   perguntar se ele quer tudo o que o painel web tem (agenda, notícias, morning
   call, juros, relógio) ou só a parte de gamma. O painel web ficou com nove
   áreas; repetir as nove dentro do NinjaTrader pode ser desnecessário, já que
   o painel web continua existindo.
4. **Terminal Python fechado.** A plotagem automática depende do
   `localhost:8777` estar no ar. Decidir o comportamento: o indicador fica
   quieto, mostra um aviso no gráfico, ou tenta subir o terminal sozinho.
   Sugestão: aviso discreto no gráfico, sem tentar subir nada.
5. **Como classificar os níveis do desenho.** O esboço traz `GEX EXTREMO`,
   `ALTO`, `MÉDIO`, `NEUTRO` e `BAIXO`, que não existem no projeto — hoje são
   Call Wall, Put Wall, HVL e key levels. Parecem faixas de intensidade.
   Falta o usuário dizer o critério: tamanho do GEX, distância do preço, ou
   outro conceito.
6. **Histórico intraday.** As áreas de GEX por hora e acumulado exigem guardar
   medições ao longo do dia, o que implica deixar o terminal ligado desde a
   abertura. O `agendador.py` é a peça inicial. Confirmar se ele aceita esse
   custo.

## Pendência relacionada

O painel de terceiros que o usuário usa como referência mostra **0DTE do QQQ**
(`QQQ Call Wall 0DTE`, `QQQ Key Level 0DTE`), que ainda não temos: os campos
`Par *` usam as paredes normais, porque `calcular_gamma` em `terminal.py` não
liga `INCLUIR_0DTE`. Vale resolver no lado Python antes ou junto do
NinjaTrader, já que os dois consomem o mesmo `exportar.py`.
