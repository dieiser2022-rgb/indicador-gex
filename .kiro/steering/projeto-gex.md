---
inclusion: always
---

# Projeto: Terminal GEX

Terminal local de níveis de gamma para quem opera **Nasdaq (MNQ)**, mais um
indicador próprio de TradingView em Pine Script. O estado completo está em
`ESTADO.md` — leia antes de mexer em qualquer coisa.

Repositório: `dieiser2022-rgb/indicador-gex`. Branch de trabalho
`terminal-completo`; o PR #1 foi mesclado em 01/11/2026 e a `main` ficou
idêntica. Pasta do usuário: `C:\indicador-gex`.

**Manter a `main` em dia.** O usuário pediu que baixar e usar fosse o mais
simples possível, e isso depende da `main` estar atual: é ela que o botão
"Download ZIP" do GitHub entrega. Depois de terminar uma entrega na
`terminal-completo`, avançar a `main` com `git merge --ff-only`. Se a `main`
ficar atrás, o usuário baixa uma versão velha sem perceber — foi exatamente o
risco que existia antes do merge, quando ela estava 50 commits atrás e sem o
`painel.html`.

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
(`GEX v5: ...`, versão atual) é o único jeito do usuário conferir se colou o
código atual. O `copiar_indicador.py` lê esse número do próprio `.pine`, então
não precisa ser atualizado em dois lugares.

Antes de entregar Pine novo, vale rodar a verificação das quatro armadilhas e
simular o parser do Pine em Python contra a linha exportada — foi assim que os
key levels 0DTE foram validados sem compilar nada. O parser normaliza o nome
para maiúsculas e sem espaço, então `GEX 1 0DTE` vira a chave `GEX10DTE`.

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

## Assunto em discussão: NinjaTrader

O usuário viu um painel de terceiros rodando dentro do NinjaTrader e perguntou
se dá para fazer o nosso lá. Foram apresentados três caminhos e ele ainda não
escolheu: **(C)** só o indicador que desenha os níveis no gráfico, em C# puro —
o recomendado, menor risco; **(A)** janela de AddOn com WebView2 mostrando o
`painel.html` que já existe; **(B)** reescrever o painel em WPF, que é grande.

O Python continua fazendo as contas em qualquer um dos três: o C# só leria
`http://localhost:8777/api/exportar`. Vale lembrar que NinjaScript não pode ser
compilado neste sandbox — mesma situação do Pine.

**O plano completo está em `indicadores/ninjatrader/README.md`**: contrato da
API medido de verdade (os 25 níveis e todos os campos da resposta), os três
caminhos comparados, onde os arquivos moram no NinjaTrader, onde o erro de
compilação aparece, e as três perguntas abertas. Ler esse arquivo antes de
escrever a primeira linha de C#.

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
ele não vê saída de terminal — então mostrar no chat o que importa.

Os comandos que ele usa:

```
cd C:\indicador-gex
git pull origin terminal-completo
python terminal.py
```

Para não depender de ele copiar texto da janela preta, os scripts de relatório
usam `relatorio.capturar()`, que joga a saída na área de transferência. Vale
reaproveitar em qualquer script novo cuja saída ele precise mandar no chat.

Atalhos prontos na raiz do repositório, todos chamadores finos de um `.py` de
mesmo nome: `COMECAR.bat` (porta de entrada única), `GEX.bat`, `ATUALIZAR.bat`,
`COPIAR_INDICADOR.bat`, `VER_VENCIMENTOS.bat`, `DIAGNOSTICO.bat`,
`CRIAR_ATALHO.bat`, `ARRUMAR_ICONE.bat`, `LIMPAR_CACHE_ICONE.bat`. Os `.bat`
precisam de CRLF (garantido pelo `.gitattributes`) e devem ficar finos: lógica
em `.bat` já quebrou duas vezes por causa do parser do `cmd`.
