# indicador-gex

Terminal local de níveis de gamma (GEX) para índices e futuros americanos.
Calcula os níveis a partir da cadeia de opções da CBOE, sem depender de nenhum
site de terceiros e sem precisar de login, cadastro ou chave de API.

Roda inteiro com a biblioteca padrão do Python. **Não há nada para instalar.**

## O painel

```
┌────────────┬──────────────────────┬─────────────┐
│ agenda     │   GEX em destaque    │ market      │
│ economica  │   e regime de gama   │ maker       │
├────────────┼──────────────────────┼─────────────┤
│ morning    │  candles + niveis    │ noticias    │
│ call       │  + perfil de gamma   │             │
├────────────┴──────────────────────┴─────────────┤
│ cards: NDX  SPX  QQQ  SPY  (+ NQ e ES)          │
├─────────────────────────────────────────────────┤
│ exportar: MT5 | TradingView | NinjaTrader       │
└─────────────────────────────────────────────────┘
```

- **Agenda econômica** — 3 eventos antes e 3 depois do momento atual, com
  previsão e valor anterior. Botão para abrir a semana inteira.
- **Regime de gama** — GEX líquido grande, verde ou vermelho.
- **Market maker** — texto explicando como o hedge dos dealers tende a agir,
  com alertas quando o preço está colado num nível.
- **Gráfico** — candles de 15 minutos com as paredes e a inversão gama
  plotadas, mais o perfil de gamma por strike na lateral.
- **Notícias** — manchetes de várias fontes; clique para expandir o resumo.
- **Morning call** — futuros, Europa, Ásia, VIX, juros, commodities, eventos
  do dia, estrutura de gamma e manchetes.
- **Cores** — botão `cores` no topo permite trocar a paleta, salva em disco.
- **Vencimento** — seletor de 0DTE, semana, mês ou 45 dias, que muda os níveis.

## Os números

Para NDX, SPX, QQQ e SPY:

- **Spot** — preço atual do índice
- **Inversão gama** (zero gamma) — o preço onde o regime vira
- **Parede de call** — maior concentração de gamma de call acima do preço
- **Parede de put** — maior concentração de gamma de put abaixo do preço
- **GEX líquido** — tamanho da posição de gamma dos dealers, por 1% de movimento
- **Regime** — positivo (dealers estabilizam) ou negativo (dealers amplificam)

Para NQ e ES, os mesmos níveis convertidos do índice para o preço do futuro,
usando o basis calculado automaticamente.

## Como usar

### Windows, com um clique

Dê um duplo clique em **`CRIAR_ATALHO.bat`** uma vez. Ele põe um atalho
"Terminal GEX" na área de trabalho, com ícone próprio. Clique com o botão
direito nesse atalho e escolha **Fixar na barra de tarefas** (no Windows 11,
primeiro em *Mostrar mais opções*).

Daí em diante é um clique no ícone da barra de tarefas.

| Arquivo | O que faz |
|---|---|
| `abrir.py` | liga o terminal; se já estiver ligado, só reabre o painel |
| `GEX.bat` | duplo clique na pasta — chama o `abrir.py` |
| `CRIAR_ATALHO.bat` | cria o atalho da área de trabalho, uma vez só |
| `ATUALIZAR.bat` | baixa a versão mais nova do código |
| `COPIAR_INDICADOR.bat` | copia o indicador do TradingView para a área de transferência |
| `DIAGNOSTICO.bat` | relatório do ícone, dos atalhos e da porta, para colar no chat |
| `LIMPAR_CACHE_ICONE.bat` | só se o atalho insistir em mostrar o ícone errado |

O atalho aponta para o `python.exe` com o `abrir.py` como argumento, e **não**
para o `GEX.bat`. O motivo é uma limitação do Windows: atalho de `.bat` é
resolvido até o `cmd.exe`, e a barra de tarefas fixa o ícone do `cmd`
descartando o ícone configurado. Apontando para o `python.exe`, o ícone é
respeitado. É por isso que a lógica de partida mora no `abrir.py` e não no
`.bat`.

A janela preta que abre é o servidor. Ela precisa ficar aberta enquanto o
painel estiver em uso — pode minimizar, mas fechar derruba o painel.

### Pela linha de comando

```bash
python terminal.py
```

Abre o navegador em `http://localhost:8777`. Clique em **ATUALIZAR REGIOES**.
A primeira carga leva de 40 a 60 segundos (o arquivo do SPX tem 13 MB).

Para ver só um ativo no terminal, em texto:

```bash
python gamma_cboe.py
```

Para acumular histórico a cada 15 minutos, em horário de mercado:

```bash
python agendador.py
```

## Arquivos

| Arquivo | Função |
|---|---|
| `gamma_cboe.py` | baixa a CBOE e calcula os níveis; grava `gamma.csv` |
| `terminal.py` | servidor local e interface web |
| `agendador.py` | coleta periódica dentro do horário de mercado |
| `testar_candles.py` | verifica quais fontes de candles respondem |
| `fazer_icone.py` | gera `gex.ico`, o ícone do atalho (Python puro) |
| `*.bat` | atalhos do Windows, descritos em *Como usar* |
| `ESTADO.md` | estado do projeto, decisões tomadas e pendências |
| `legado/` | primeiras tentativas, raspando um site de terceiros (abandonado) |

## Fontes de dados

- **Opções:** CBOE, arquivo público `delayed_quotes` (atraso de ~15 minutos).
  Traz gamma, open interest e volatilidade implícita por contrato.
- **Preço de futuros e candles:** Yahoo Finance, endpoint v8 de chart.

Nenhuma das duas exige chave ou cadastro.

## Como os níveis são calculados

O strike não vem como campo separado: está codificado no nome do contrato, no
padrão OSI (`SPY261023C00500000` = SPY, vencimento 23/10/2026, call, strike 500).

Para cada contrato com open interest, o gamma em dólares é
`gamma × open interest × 100 × spot² × 0,01`, positivo para call e negativo para
put. Os valores são somados por strike.

A **inversão gama** não sai de uma soma simples: o programa simula o índice em
81 preços diferentes, recalcula o gamma de toda a carteira em cada um, e acha
onde o total troca de sinal.

Quando a CBOE não envia o gamma de um contrato, ele é calculado por
Black-Scholes a partir da volatilidade implícita. Contratos já vencidos são
descartados, porque o gamma de uma opção no dia do vencimento distorce o total.

## Validação

Comparado com um serviço comercial de referência em 23/10/2026 (SPX):

| Campo | Calculado aqui | Referência |
|---|---|---|
| Spot | 7623,68 | 7624 |
| Inversão gama | 7730,06 | 7737 |
| Parede de call | 8000,00 | 8000 |
| GEX líquido | −51,14 B | −50,98 B |

O basis calculado (ES = SPX + 48,82 e NQ = NDX + 217,47) também coincidiu com
os valores da referência.

## Aviso

Ferramenta de análise para uso pessoal. Os números descrevem a mecânica de
hedge dos dealers — não são previsão de preço nem recomendação de investimento.
Dados com atraso, não servem para execução.
