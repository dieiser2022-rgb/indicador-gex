# Terminal GEX — estado do projeto

Atualizado em 26/10/2026. Este arquivo é a memória do projeto: quem pegar o
código depois (ou o assistente numa conversa nova) deve conseguir se situar só
lendo aqui.

## O que é

Terminal local de níveis de gamma para quem opera **Nasdaq (MNQ)**, mais um
indicador próprio de TradingView que recebe esses níveis.

Restrições que o projeto respeita desde o começo:

- só biblioteca padrão do Python, nada de `pip install`
- nenhuma chave de API, nenhum cadastro
- roda offline do ponto de vista de contas: só precisa de internet para baixar
  dados públicos

## Como rodar

No Windows, duplo clique em `GEX.bat` — ou no atalho da barra de tarefas,
criado uma vez por `CRIAR_ATALHO.bat`. Pela linha de comando:

```
cd C:\indicador-gex
git pull origin terminal-completo
python terminal.py
```

Abre em `http://localhost:8777`. Para copiar o indicador para o TradingView,
duplo clique em `COPIAR_INDICADOR.bat`, ou:

```
type indicadores\tradingview_gex.pine | clip
```

Os `.bat` existem porque o usuário queria um ícone na barra de tarefas. O
`.gitattributes` força CRLF neles: com LF o `cmd` engasga em bloco entre
parênteses.

**Armadilha já paga:** o Windows **não** aceita ícone próprio em atalho de
`.bat`. Ele resolve o atalho até o `cmd.exe` e fixa o ícone do `cmd` na barra
de tarefas, jogando fora o `IconLocation`. A primeira tentativa foi assim e
apareceu como um cmd comum. A correção foi apontar o atalho para o
`python.exe` com `abrir.py` como argumento — aí o ícone é respeitado. Por isso
a lógica de partida mora no `abrir.py`, e o `GEX.bat` virou só um chamador.

**Segunda armadilha paga:** a criação do atalho não pode morar no `.bat`. A
versão que usava
`for /f ... in (\`python -c "import sys;print(sys.executable)"\`)` tem
parênteses do `print` dentro dos parênteses do `for /f`, e é aí que o `cmd`
fecha o parêntese no lugar errado. Agora quem cria o atalho é
`criar_atalho.py`: ele conhece `sys.executable` sem perguntar a ninguém, lê a
área de trabalho do registro (`User Shell Folders` — quem usa OneDrive tem a
pasta redirecionada) e grava o script do PowerShell em arquivo, o que elimina
o problema de aspas dentro de aspas.

**Terceira armadilha:** o Explorer guarda ícone em cache indexado pelo caminho
do arquivo. Um atalho criado apontando para `.bat` (ícone de cmd) e depois
recriado com o mesmo nome continua aparecendo como cmd. Por isso
`criar_atalho.py` apaga o `.lnk` antigo antes de gravar e chama
`ie4uinit.exe -show`. Quando nem isso resolve, `limpar_cache_icone.py` fecha o
Explorer, apaga `IconCache.db` e `iconcache_*.db`, e reabre o Explorer num
`finally` — sem o `finally` uma falha deixaria o usuário sem área de trabalho.

Para depurar isso sem rodadas de tentativa e erro existe `diagnostico.py`: ele
pergunta ao próprio Windows se consegue carregar o `.ico`
(`LoadImageW` via `ctypes`, em 4 tamanhos), lista os atalhos nas quatro pastas
possíveis e mostra alvo, argumentos e ícone de cada um.

O `abrir.py` testa a porta abrindo uma conexão TCP de verdade, não lendo
`netstat` — a saída do `netstat` muda com o idioma do Windows e lista também
conexão que está se encerrando. Ele também tenta pôr título e ícone na janela
do console via `ctypes` (`WM_SETICON`); no Windows Terminal do Windows 11 isso
pode não ter efeito, e falha em silêncio de propósito.

O ícone `gex.ico` é gerado por `fazer_icone.py`, em Python puro (struct, sem
biblioteca de imagem). São 9 tamanhos, de 16 a 256 px. Para refazer, rode o
script. Prévia em `gex_previa.png`.

## Arquivos

| Arquivo | O que faz |
|---|---|
| `terminal.py` | servidor em `localhost:8777` e todas as rotas da API |
| `painel.html` | interface inteira (HTML, CSS e JS num arquivo só) |
| `gamma_cboe.py` | baixa a CBOE e calcula os níveis; roda sozinho no terminal de texto |
| `exportar.py` | monta a linha de níveis no formato do GEX ECOSYSTEM |
| `fontes.py` | candles, cotações, calendário, notícias, tradução, relevância |
| `leitura.py` | texto do market maker e do morning call, por regras |
| `agendador.py` | coleta a cada 15 min dentro do horário de mercado |
| `testar_candles.py` | verifica quais fontes de candles respondem |
| `indicadores/tradingview_gex.pine` | o indicador do TradingView |
| `indicadores/README.md` | como instalar e configurar o indicador |
| `abrir.py` | partida: testa a porta, sobe o terminal, segura o erro na tela |
| `GEX.bat` | duplo clique na pasta; só chama o `abrir.py` |
| `CRIAR_ATALHO.bat` | cria o atalho da área de trabalho, com ícone |
| `criar_atalho.py` | cria os atalhos; o `.bat` é só um chamador |
| `diagnostico.py` | relatório de ícone, atalhos e porta, para colar no chat |
| `limpar_cache_icone.py` | apaga o cache de ícones do Explorer |
| `ATUALIZAR.bat` | `git pull` com mensagem em português |
| `COPIAR_INDICADOR.bat` | manda o `.pine` para a área de transferência |
| `fazer_icone.py` | gera `gex.ico` em Python puro |
| `config.json` | cores e preferências (criado no primeiro uso, fora do git) |
| `legado/` | primeiras tentativas raspando site de terceiros (abandonado) |

## Rotas da API

| Rota | Para que |
|---|---|
| `/api/gamma?simbolo=&dias=` | níveis de gamma de um ativo |
| `/api/candles` | candles de 15 min do ativo principal e do futuro |
| `/api/calendario` | agenda econômica, em português |
| `/api/noticias` | manchetes traduzidas, com relevância |
| `/api/panorama` | cotações dos 13 ativos de referência |
| `/api/juros?janela=` | curva do título de 10 anos dos EUA |
| `/api/morningcall` | texto do morning call |
| `/api/exportar?ativo=&plataforma=&simbolo=&dias=` | a linha para colar no indicador |
| `/api/config` | GET e POST das preferências |
| `/api/estado` | diagnóstico: o que respondeu e o que falhou |

## Fontes de dados

**CBOE** — `https://cdn.cboe.com/api/global/delayed_quotes/options/{SIMBOLO}.json`
(índices com underscore: `_SPX`, `_NDX`). Traz `current_price`, `gamma`,
`open_interest` e `iv` prontos. Atraso de ~15 min, sem chave. É o coração do
projeto. Confirmada funcionando: 29.380 contratos no SPX.

**Yahoo** — `https://query1.finance.yahoo.com/v8/finance/chart/{SIMBOLO}?interval=15m&range=1mo`.
Confirmado para `NQ=F`, `ES=F`, `^NDX`, `^SPX`, `QQQ` e `^TNX`.
O endpoint **v7 de opções dá 401** — só o v8 de chart serve.

**Calendário** — `https://nfs.faireconomy.media/ff_calendar_thisweek.json`
(cai para `.xml`). Feed informal, pode sair do ar; se cair, a área fica vazia
sem derrubar o resto.

**Notícias** — 9 feeds RSS: 3 do InfoMoney, 2 do Investing BR, 1 do Money
Times, e MarketWatch, CNBC e Investing em inglês.

**Tradução** — Google `gtx` como principal, MyMemory como reserva, texto
original como último recurso. Nenhum dos dois é serviço contratado.

**Não funciona:** Stooq (devolve página anti-robô), Yahoo v7 de opções (401),
gexmetrix.com (403, exige JS para escolher o instrumento).

Todas as funções de `fontes.py` devolvem vazio em caso de falha, nunca
levantam exceção. Isso é de propósito: uma fonte fora do ar não pode derrubar
o painel.

## Decisões de cálculo

- **Strike vem no nome do contrato**, padrão OSI, não como campo:
  `SPY261023C00500000` = SPY + 261023 + C + strike × 1000.
- **Contratos já vencidos são descartados.** O gamma de uma opção no dia do
  vencimento distorce o total — foi o que inflou a primeira medição (Net GEX
  caiu de −85B para −51B depois da correção).
- **Inversão gama por varredura de preço:** simula 51 preços, recalcula o
  gamma da carteira em cada um e acha onde troca de sinal. Somar strikes dava
  `N/A` sempre que todos tinham o mesmo sinal.
- **Contratos sem IV herdam a IV mediana.**
- **Sem gamma da CBOE, calcula por Black-Scholes** usando só `math`.
- **`MARGEM = 0`**, para a parede bater com a convenção dos sites de referência
  (eles aceitam parede colada no preço).
- **GEX 1-10 com separação mínima de 0,25%.** Sem isso, os dez maiores eram
  sempre os dez vizinhos do preço, espalhados em 0,86%. Com a regra, cobrem
  2,85%.
- **`1D Min/Max` = `spot × (1 ± iv/√252)`**, centrado no **preço**, não no HVL.
  Deduzido da imagem de referência e reproduziu com 0,01 ponto de diferença.
- **Base de preço é por ativo, não por plataforma.** MNQ é futuro sempre;
  USTEC e US100 são CFD e dependem da corretora — dá 215 pontos de diferença.
  Configurável em `terminal.py` (`BASE_ATIVO`) e pela interface.
- **Call wall verde, put wall vermelho**, a pedido do usuário: a cor segue o
  lado da aposta, não o papel de suporte ou resistência.
- **Agenda em português por dicionário** (73 nomes + 9 sufixos + 6 prefixos),
  não por tradutor. Termos técnicos como "Core CPI" um tradutor erra, e a
  lista de eventos é fechada — resolve offline e sempre igual.
- **Feeds de seção, nunca feed geral de portal.** O feed geral do InfoMoney
  trazia Mega Sena e horóscopo; o `mw_topstories` trazia finanças pessoais.

## Validação contra o site de referência (23/10/2026, SPX)

| | nosso | referência |
|---|---|---|
| Spot | 7623,68 | 7624 |
| Zero Gamma | 7730,06 | 7737 |
| Call Wall | 8000 | 8000 |
| Net GEX | −51,14B | −50,98B |

Basis calculado automaticamente: ES = SPX + 48,82 e NQ = NDX + 217,47.

## O painel, área por área

| Área | Situação |
|---|---|
| Agenda econômica (3 antes, 3 depois, semana inteira) | feito, em português, com bolinhas de relevância |
| Regime de gamma em destaque | feito |
| Texto de como o market maker tende a agir | feito |
| Gráfico de candles de 15 min com os níveis | feito |
| Perfil de gamma na lateral | feito |
| Notícias clicáveis com resumo | feito, traduzidas, com bolinhas |
| Morning call factual | feito |
| Caixa "Gerar GEX" (ativo à esquerda, plataforma à direita) | feito |
| Juros de 10 anos dos EUA | feito (`^TNX`, com correção da escala ×10) |
| Relógio de 5 praças com sessões | feito, por fuso real |
| Botão de tela cheia | feito |
| Dois robôs animados, 3 humores, voz opcional | feito, voz desligada por padrão |
| Editor de cores salvo em `config.json` | feito |
| Seletor de vencimento (0DTE / semana / mês / 45 dias) | feito |

Visual futurista: brilho, efeito de vidro, tipografia mono e grade de fundo.
Feito **sem mexer na estrutura** — 37 ids, 33 classes e 21 tags conferidos
idênticos antes e depois.

O que foi **recusado de propósito:** o bloco "COMPRA" do print de referência
(percentuais não verificáveis, e competiria com o gráfico pela atenção), e IA
prevendo preço no morning call.

## O indicador do TradingView

Versão atual: **v4**. O número aparece no aviso em cima do gráfico
(`GEX v4: 14 campos lidos, 11 linhas no grafico`) e serve para conferir se o
código colado é o atual.

Formato que ele lê:

```
$NQ1!: Call Resistance, 30100, Put Support, 30000, HVL, 30075, 1D Min, 29691.92, ...
```

Pares nome/valor. A ordem não importa (busca por nome), campo faltando é
ignorado, maiúsculas e espaços não importam.

Níveis reconhecidos: `Call Resistance`, `Put Support`, `Call Resistance 2`,
`Put Support 2`, `Par Call Resistance`, `Par Put Support`, `Par HVL`, `HVL`,
`Call Resistance 0DTE`, `Put Support 0DTE`, `HVL 0DTE`, `Gamma Wall 0DTE`,
`GEX 1 0DTE` a `GEX 5 0DTE`, `1D Min`, `1D Max`, `GEX 1` a `GEX 10`.

**Key levels 0DTE** (`GEX n 0DTE`): mesmo cálculo do `GEX 1..10`, aplicado só
aos contratos que vencem hoje. Nasceram da comparação com o gráfico do mentor
do usuário, que os chama de *Key Level 0DTE*. Três detalhes de projeto: são 5
no máximo (`QUANTOS_GEX_0DTE`) porque no vencimento do dia o gamma se
concentra num punhado de strikes; os níveis que já têm campo próprio — as duas
paredes 0DTE, o HVL 0DTE e o **Gamma Wall 0DTE** — entram na lista de `evitar`,
senão o primeiro key level seria sempre uma cópia do gamma wall; e o
`completar=False` desliga o preenchimento de sobra do `escolher_gex`, que no
0DTE traria níveis colados nas paredes.

Equivalência com os nomes que o mentor usa: `Call/Put Wall 0DTE` = nosso
`Call Resistance / Put Support 0DTE`; `Put High Gamma-2` = nosso
`Put Support 2`; `Key Level-1/-2` = nosso `GEX 1/2`. Ainda **falta** o 0DTE do
QQQ: os campos `Par` usam as paredes normais, porque `calcular_gamma` (que
alimenta o cache por ativo) não liga `INCLUIR_0DTE`.

São 48 ajustes agrupados. `GEX por strike` vem **desligado** (o usuário quer
só call e put). Texto dos rótulos vem **preto**, rótulo **acima** da linha.

### Pine Script: o que quebra a compilação

Quatro erros já foram pagos. Não repetir:

1. **Nenhuma linha quebrada no meio de uma chamada.** A continuação precisa de
   indentação que não seja múltiplo de 4, e violar isso dá
   `end of line without line continuation`. Linhas longas, mas seguras.
2. **Lista atribuída a variável não existe em Pine.** Dá
   `Syntax error at input '['`.
3. **Nada de acento ou cedilha em nome de função ou variável.**
4. **Só usar funções `str.*` confirmadas.** `str.pos` e `str.trim` foram
   evitadas; para tirar espaço, `str.replace_all(s, " ", "")`.

### Pegadinha ao atualizar o indicador

O TradingView **guarda as configurações salvas** de cada instância. Mudar o
valor padrão de um `input` no código **não muda** o que já está no gráfico do
usuário. Para o padrão novo valer, ele tem que remover o indicador do gráfico
e adicionar de novo — ou mexer na opção na mão.

## Onde paramos (26/10/2026)

**Combinado com o usuário:** o executável/atalho para abrir o terminal fica
para **mais tarde**. Ele pediu para pausar esse assunto depois de atualizar o
indicador para a v5. Não retomar por conta própria — esperar ele trazer.

Feito nesta sessão: `ver_vencimentos.py` (confirmou que o 0DTE chega em NDX e
SPX, raízes `NDXP` e `SPXW`), relatórios que se copiam sozinhos para a área de
transferência, key levels 0DTE no cálculo e no indicador (v5), e
`copiar_indicador.py` lendo a versão do próprio `.pine`.

Pendente de confirmação do usuário: se as linhas ciano dos key levels 0DTE
apareceram no gráfico dele. Ele disse "acho que deu".

**Ícone na barra de tarefas: não resolvido.** Quatro tentativas, nenhuma
funcionou. O que o `diagnostico.py` já provou na máquina do usuário
(Windows 10 19045, Python 3.13 em `AppData\Local`, área de trabalho no
OneDrive):

- o `gex.ico` está **bom**: o Windows carrega nos 4 tamanhos testados
  (`16:ok 32:ok 48:ok 256:ok`) — não é o arquivo
- o atalho da área de trabalho está **correto**: alvo `python.exe`, argumento
  `"C:\indicador-gex\abrir.py"`, ícone `gex.ico,0` — não é a configuração
- **nada nosso aparece fixado** na barra de tarefas nem no menu iniciar

Ou seja: o lançador funciona (duplo clique na área de trabalho abre o painel),
só o "fixar na barra com o ícone certo" que não.

Último estado da conversa: foi sugerido fixar **arrastando com o mouse** o
atalho da área de trabalho até a barra (no Windows 10 isso fixa sem passar por
menu), e foi feita uma pergunta de múltipla escolha para descobrir o que
exatamente falha — se a opção "Fixar na barra de tarefas" não aparece, se fixa
com ícone de cmd, se fixa com ícone do Python, ou se algum script deu erro.
**O usuário ainda não respondeu**, e sem isso não há como escolher a correção.

Aviso para a próxima sessão: não emendar mais scripts sem essa resposta. As
quatro tentativas (ícone no `.bat`, atalho para o `python.exe`,
`criar_atalho.py`, `arrumar_icone.py`) foram feitas às cegas e custaram a
paciência do usuário. O caminho já pronto e não testado por ele é
`ARRUMAR_ICONE.bat`, que reescreve o ícone do `.lnk` **depois** de fixado.

## Pendências

1. **Parede de put divergia** da referência: a nossa ficava 1,4% a 3,3% longe
   do preço, a do site 0,01% a 0,12%. Hipótese: somávamos 45 dias e o site usa
   só o vencimento próximo. O seletor de vencimento permite testar — falta
   comparar com `0DTE` e `semana` e fechar a questão.
2. **Indicadores de MT5 e NinjaTrader.** A linha de dados já é gerada para
   eles; falta escrever o indicador em MQL5 e em C#.
3. **Curva de juros completa** (2, 5, 10 e 30 anos, com o spread 10a−2a).
   Oferecido, usuário não respondeu.
4. **Paredes de múltiplos vencimentos** ao mesmo tempo. Oferecido, usuário não
   respondeu.
5. **PR #1 continua aberto** na branch `terminal-completo`. Nunca foi mesclado
   na `main` — o usuário não disse se quer.

## Nunca testado ao vivo

O assistente trabalha num sandbox **sem rede**, então nada disso pôde ser
verificado de verdade: os dois tradutores, o MyMemory, os feeds do Investing
BR e do Money Times, e a compilação do Pine Script. Tudo foi testado com dados
simulados. As fontes marcadas como "confirmadas" foram confirmadas pelo
usuário rodando na máquina dele.

## Contexto do usuário

Opera **Nasdaq (MNQ)** — NDX/NQ é prioridade, S&P entra como apoio.
Escreve em caixa alta, português informal.
Prefere explicação **simples e didática**, passo a passo, com analogia antes do
termo técnico, e um resumo curto no fim.
**Não tem acesso ao sandbox:** todo código chega até ele por `git pull`, na
pasta `C:\indicador-gex`.
