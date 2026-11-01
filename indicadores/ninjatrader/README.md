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

## Três caminhos

| | O que é | Esforço | Risco | Reescreve a interface? |
|---|---|---|---|---|
| **C** | Indicador que desenha os níveis no gráfico | pequeno | baixo | não tem interface |
| **A** | Janela de AddOn com WebView2 abrindo o `painel.html` | pequeno | médio | não |
| **B** | Painel nativo em WPF | grande | alto | sim, do zero |

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
WebView2 e o NinjaTrader. O C isola o problema no nosso código.

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

## Perguntas abertas para o usuário

1. **Automático ou colado à mão?** O indicador pode buscar os níveis do
   terminal sozinho (atualiza só, e é quase o mesmo trabalho) ou receber a
   linha de texto colada, como no TradingView. O automático parece melhor, mas
   confirmar.
2. **De quanto em quanto tempo atualizar?** A CBOE tem atraso de ~15 min, então
   buscar a cada 1 min é desperdício. Sugestão: a cada 5 min, mais um botão de
   atualizar agora.
3. **Mesmo repositório?** Este plano assume que sim, nesta pasta. O lado C# só
   depende da API do terminal, então ficar junto evita versões divergentes.

## Pendência relacionada

O painel de terceiros que o usuário usa como referência mostra **0DTE do QQQ**
(`QQQ Call Wall 0DTE`, `QQQ Key Level 0DTE`), que ainda não temos: os campos
`Par *` usam as paredes normais, porque `calcular_gamma` em `terminal.py` não
liga `INCLUIR_0DTE`. Vale resolver no lado Python antes ou junto do
NinjaTrader, já que os dois consomem o mesmo `exportar.py`.
