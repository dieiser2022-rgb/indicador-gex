# Terminal GEX — estado do projeto

## Arquivos

| Arquivo | O que faz |
|---|---|
| `terminal.py` | servidor local em `localhost:8777` e todas as rotas da API |
| `painel.html` | interface: as 9 áreas do layout desenhado pelo usuário |
| `gamma_cboe.py` | baixa a CBOE e calcula os níveis; roda sozinho pelo terminal de texto |
| `fontes.py` | candles, cotações, calendário econômico e notícias |
| `leitura.py` | texto do market maker e morning call, por regras |
| `agendador.py` | coleta a cada 15 min dentro do horário de mercado |
| `testar_candles.py` | verifica quais fontes de candles respondem |
| `config.json` | cores e preferências (criado no primeiro uso) |
| `legado/` | primeiras tentativas, raspando um site de terceiros (abandonado) |

## As 9 áreas do desenho

| # | Parte | Situação |
|---|---|---|
| 1 | Agenda econômica: 3 antes, 3 depois, botão para a semana inteira | feito |
| 2 | Regime de gamma em destaque grande | feito |
| 3 | Texto de como o market maker tende a agir | feito |
| 4 | Gráfico de candles com os níveis plotados | feito |
| 5 | Perfil de gamma na lateral do gráfico | feito |
| 6 | Notícias, clicáveis, com resumo que expande | feito |
| 7 | Morning call factual | feito |
| 8 | Cards de NDX/SPX/QQQ/SPY + NQ/ES | feito |
| 9 | Botões MT5 / TradingView / NinjaTrader | **só layout** — mostram os níveis em texto |
| + | Editor de cores, salvo em `config.json` | feito |
| + | Seletor de vencimento (0DTE / semana / mês / 45 dias) | feito |

## Fontes de dados

- **CBOE** `https://cdn.cboe.com/api/global/delayed_quotes/options/{SIMBOLO}.json`
  (índices com underscore: `_SPX`, `_NDX`). Traz `current_price`, `gamma`,
  `open_interest`, `iv`. Atraso ~15 min, sem chave.
- **Yahoo** `.../v8/finance/chart/{SIMBOLO}?interval=15m&range=5d`
  Confirmado para `NQ=F`, `ES=F`, `^NDX`, `^SPX`, `QQQ`. O endpoint **v7 de
  opções dá 401** — só o v8 de chart serve.
- **Calendário** `https://nfs.faireconomy.media/ff_calendar_thisweek.json`
  (cai para `.xml`). Traz horário, moeda, impacto, previsão e anterior.
  É um feed informal e pode sair do ar — nesse caso a área fica vazia, sem
  derrubar o resto. Reserva oficial possível: Federal Reserve e BLS, que não
  têm o campo de previsão.
- **Notícias** RSS de MarketWatch, Yahoo Finance, CNBC e Investing.
- **Stooq**: não funciona, devolve página anti-robô.

Nada exige chave ou cadastro. Todas as funções de `fontes.py` devolvem vazio
em caso de falha, em vez de levantar exceção.

## Decisões de cálculo

- Strike não vem como campo: está no nome do contrato, padrão OSI.
  `SPY261023C00500000` = SPY + 261023 + C + strike×1000.
- `MARGEM = 0` no terminal, para a parede bater com a convenção dos sites de
  referência (eles aceitam parede colada no preço).
- Contratos já vencidos são descartados: o gamma de uma opção no dia do
  vencimento distorce o total. Foi o que inflou a primeira medição.
- Contratos sem IV herdam a IV mediana.
- Sem gamma da CBOE, calcula por Black-Scholes usando só `math`.
- A inversão gama vem de varredura: simula 51 preços, recalcula o gamma da
  carteira em cada um e acha onde troca de sinal. Somar strikes não funciona
  quando todos têm o mesmo sinal — foi o que dava `N/A` antes.

## Níveis de outros ativos no gráfico

O gráfico mostra o índice principal com conversão **exata** (basta somar o
basis) e o ETF do mesmo mercado por **proporção** (`spot_base / spot_outro`),
que é aproximado e aparece tracejado na tela.

Plota apenas o par natural — NDX+QQQ no gráfico do Nasdaq, SPX+SPY no do S&P.
Jogar os quatro ativos daria 12 linhas e viraria uma zebra ilegível.

## Validação contra o site de referência (23/10/2026)

Spot, inversão gama e parede de call bateram quase exatos nos 4 ativos.
Net GEX do SPX: nosso −51,14B contra −50,98B (0,3%).
Basis automático: ES = SPX + 48,82 e NQ = NDX + 217,47 — coincidiu.

## Pendências

1. **Parede de put divergia** da referência: a nossa ficava 1,4% a 3,3% longe
   do preço, a do site 0,01% a 0,12%. Hipótese: somávamos 45 dias e o site usa
   só o vencimento próximo. O seletor de vencimento agora permite testar isso
   na interface — falta comparar com `0DTE` e `semana` e fechar a questão.
2. **Item 9**: a exportação em si. Hoje os botões só mostram os níveis em texto
   para copiar. Falta gerar o formato de cada plataforma (indicador do MT5,
   script Pine do TradingView, arquivo do NinjaTrader).
3. **Morning call com IA**, se o usuário quiser depois. Ficou decidido que a
   versão factual vem primeiro, e que IA não entra para projetar preço — só
   poderia redigir melhor os mesmos dados.

## Contexto do usuário

Opera **Nasdaq** (NQ) — NDX/NQ é prioridade, S&P entra como apoio.
Prefere explicações em português, linguagem simples, passo a passo.
O código chega até ele por `git pull`, então não há mais a restrição de
evitar barras invertidas que existia na fase de copiar e colar.
