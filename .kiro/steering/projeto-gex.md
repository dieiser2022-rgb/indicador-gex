---
inclusion: always
---

# Projeto: Terminal GEX

Terminal local de níveis de gamma para quem opera **Nasdaq (MNQ)**, mais um
indicador próprio de TradingView em Pine Script. O estado completo está em
`ESTADO.md` — leia antes de mexer em qualquer coisa.

Repositório: `dieiser2022-rgb/indicador-gex`, branch de trabalho
`terminal-completo` (PR #1 aberto, nunca mesclado). Pasta do usuário:
`C:\indicador-gex`.

## Regras do projeto

- **Só biblioteca padrão do Python.** Nada de `pip install`, nada de chave de
  API, nada de cadastro. Essa restrição vem do usuário e não é negociável.
- **Fonte de dados que falha devolve vazio**, nunca levanta exceção. Uma fonte
  fora do ar não pode derrubar o painel.
- **Não mexer na estrutura do `painel.html`** em pedido de visual. Quando o
  usuário pede "mais bonito", conferir que ids, classes e tags continuam os
  mesmos depois da mudança.
- **Call wall é verde, put wall é vermelho.** A cor segue o lado da aposta,
  não o papel de suporte ou resistência. Já foi trocado uma vez a pedido.
- **Nada de IA prevendo preço.** O morning call é factual.

## Pine Script: o que quebra a compilação

Quatro erros já custaram tempo. Não repetir:

1. **Nunca quebrar linha no meio de uma chamada.** A continuação exige
   indentação que não seja múltiplo de 4, e violar dá
   `end of line without line continuation`. Preferir linha longa.
2. **Lista atribuída a variável não existe em Pine** (`Syntax error at input '['`).
3. **Sem acento nem cedilha** em nome de função ou variável.
4. **Só funções `str.*` confirmadas.** `str.pos` e `str.trim` não foram
   validadas; para tirar espaço usar `str.replace_all(s, " ", "")`.

Sempre que o Pine mudar, subir o número em `VERSAO` — o aviso no gráfico
(`GEX v4: ...`) é o único jeito do usuário conferir se colou o código atual.

**Pegadinha:** o TradingView guarda as configurações salvas de cada instância.
Mudar o valor padrão de um `input` **não** muda o gráfico que o usuário já tem.
Para valer, ele precisa remover o indicador e adicionar de novo — avisar isso
sempre.

## Assunto pausado pelo usuário: executável / ícone na barra

O usuário pediu para deixar o atalho de abrir o terminal **para mais tarde**.
Não retomar por conta própria — esperar ele trazer o assunto.

## Assunto em aberto: ícone na barra de tarefas

Quatro tentativas falharam. Leia a seção "Onde paramos" do `ESTADO.md` antes
de propor qualquer coisa. O ícone e o atalho já foram **provados corretos** por
`diagnostico.py`; falta só descobrir o que o Windows faz ao fixar.

**Não escrever mais script sobre isso sem o usuário dizer o que falha.** As
quatro tentativas foram às cegas e gastaram a paciência dele. A pergunta de
múltipla escolha está aguardando resposta, e o `ARRUMAR_ICONE.bat` já está
pronto e ainda não foi testado por ele.

## Limitações do ambiente

O sandbox **não tem rede** (`INTEGRATIONS_ONLY`) e `web_fetch` dá 403 para
tudo. Nenhuma fonte de dados pode ser testada ao vivo, e Pine Script não pode
ser compilado aqui. Testar com dados simulados e deixar claro para o usuário o
que foi verificado e o que não foi.

## Como falar com o usuário

Escreve em caixa alta, português informal. Quer explicação **simples e
didática**: analogia do dia a dia antes do termo técnico, passo a passo, texto
curto e conversacional, resumo de uma ou duas frases no fim.

**Ele não tem acesso ao sandbox.** Todo código chega até ele por `git pull`, e
ele não vê saída de terminal — então mostrar no chat o que importa. Os comandos
que ele usa:

```
cd C:\indicador-gex
git pull origin terminal-completo
python terminal.py
type indicadores\tradingview_gex.pine | clip
```
