# Terminal GEX — onde paramos

## Funcionando hoje

Arquivos na máquina do usuário, em `C:\gex`:

| Arquivo | O que faz |
|---|---|
| `gamma_cboe.py` | baixa a CBOE, calcula Net GEX, Zero Gamma, Call/Put Wall, grava `gamma.csv` |
| `terminal.py` | servidor local em `localhost:8777`, cards dos 4 ativos + botão atualizar |
| `agendador.py` | coleta a cada 15 min só em horário de mercado (feito, nunca rodou de verdade) |
| `testar_candles.py` | descobriu as fontes de candles |

Rodar: `cd C:\gex` e `python terminal.py`. Nada para instalar — só biblioteca padrão.

## Fontes de dados confirmadas na máquina dele

- **CBOE** `https://cdn.cboe.com/api/global/delayed_quotes/options/{SIMBOLO}.json`
  (índices com underscore: `_SPX`, `_NDX`). Traz `current_price`, `gamma`,
  `open_interest`, `iv`. Atraso ~15 min, sem chave. SPX tem 29 mil contratos.
- **Yahoo** `https://query1.finance.yahoo.com/v8/finance/chart/{SIMBOLO}?interval=15m&range=1mo`
  Funcionou para `NQ=F`, `ES=F`, `^NDX`, `^SPX`, `QQQ`. NQ=F devolveu 2485 candles
  de 15m. O endpoint **v7 de opções dá 401** — só o v8 de chart serve.
- **Stooq**: não funciona, devolve página anti-robô.
- Strike não vem como campo: está no nome do contrato (padrão OSI).
  `SPY261023C00500000` = SPY + 261023 + C + strike×1000.

### Ainda não testadas (entram num testador quando chegar a hora)

- Calendário: `https://nfs.faireconomy.media/ff_calendar_thisweek.xml`
  (feed semanal público do ForexFactory: horário, moeda, impacto, evento,
  previsão, anterior). É informal e pode cair sem aviso — reserva oficial:
  Federal Reserve (FOMC), BLS (CPI/payroll), que não têm campo de previsão.
- Notícias: RSS do MarketWatch e do Yahoo Finance (livres para uso pessoal).

## Validação contra o site de referência (23/10/2026)

Spot, inversão gama e parede de call bateram quase exatos nos 4 ativos.
Net GEX do SPX: nosso −51,14B contra −50,98B do site (0,3%).
Basis automático: ES = SPX + 48,82 / NQ = NDX + 217,47 — bateu com o site.

## O terminal que o usuário desenhou (escopo acordado)

| # | Parte | Situação |
|---|---|---|
| 1 | Calendário econômico do dia: 3 eventos antes, 3 depois, botão para o completo | dá |
| 2 | Regime de gamma (positivo/negativo) em destaque grande | dá, já calculado |
| 3 | Texto de como o market maker tende a se comportar | dá, por regras |
| 4 | Gráfico de candles 15m com os níveis plotados (vários ativos juntos) | dá |
| 5 | Perfil de gamma vertical na lateral do gráfico | dá |
| 6 | Notícias (atraso é aceitável) | dá, via RSS |
| 7 | Morning call | ver abaixo |
| 8 | Cards de NDX/SPX/QQQ/NQ/ES | pronto |
| 9 | Botões "gerar GEX para MT5 / TradingView / NinjaTrader" | **só o layout** por enquanto |
| + | Campo de edição de cores do terminal | dá, salvar em JSON local |

### Item 3 — regras para o texto do market maker

Cruzar três coisas que já temos: sinal do Net GEX, posição do preço em relação
à inversão gama, e distância até cada parede. Gamma positivo = dealer freia
(range, reversão à média). Negativo = dealer empurra (movimento esticado).
Deixar explícito no painel que é leitura de mecânica, não previsão de preço.

### Item 7 — decisão tomada

Fazer primeiro o **morning call factual**, sem IA: fechamento de futuros,
Europa e Ásia, eventos do calendário, manchetes, regime de gamma e níveis-chave.
Grátis, sem instalar nada.

Foi explicado ao usuário, e ele concordou, que IA não prevê mercado — colocar
"hoje deve subir X%" seria fabricar confiança sem base. Se mais tarde ele quiser
o texto mais redigido, plugar um LLM (chave paga, ou Ollama local com ~4 GB) que
escreve em cima dos mesmos dados, sem inventar direção.

## Pendências técnicas

1. **Parede de put diverge.** Nossa fica longe do preço (1,4% a 3,3%), a do site
   fica colada (0,01% a 0,12%). Hipótese: somamos 45 dias (`DIAS_MAX = 45`) e o
   site usa só o vencimento próximo (os prints dele diziam "0DTE + Weekly").
   Teste de uma linha pendente: trocar para `DIAS_MAX = 7` e comparar.
2. **Seletor de vencimento** na interface: 0DTE / semana / mês / 45 dias.
3. **Barras por strike poluídas** — ~100 linhas por card. Enxugar e marcar onde
   ficam a inversão gama e as paredes.

## Logística: como entregar o código

O terminal completo deve dar 800 a 1000 linhas. Copiar e colar no Notepad já
causou dois erros de sintaxe e é inviável nesse tamanho.

**Plano combinado:** o usuário (`dieiser2022-rgb`) vai criar um repositório vazio
no GitHub e passar o nome. Então tentar `git push` dos arquivos. Tentativa de
criar o repositório pelo agente deu **HTTP 403**, mas enviar para um repositório
que ele mesmo criou pode funcionar.

Se o push falhar, plano B: dividir o terminal em arquivos menores e colar aos poucos.

## Cuidado ao gerar código para este usuário

O código vai por copiar e colar, e isso corrompe sequências de escape: `\n`,
`\t` e `\r` dentro de strings viram caracteres reais e quebram o arquivo.
Já aconteceu duas vezes.

Regra: **nenhuma barra invertida no arquivo** e **ASCII puro**. Verificar antes
de entregar. Usar `chr(9)`, `chr(10)`, `print("")` em vez dos escapes.
(Se o push para o GitHub funcionar, essa restrição deixa de ser necessária.)

## Contexto do usuário

Opera **Nasdaq** (NQ) — NDX/NQ é prioridade, S&P entra como apoio.
Prefere explicações em português, linguagem simples, passo a passo.
