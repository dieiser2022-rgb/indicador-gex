@echo off
title Terminal GEX - comecar
cd /d "%~dp0"

rem Porta de entrada unica. Baixou a pasta e nao sabe o que fazer? Clica aqui.
rem
rem Ele percorre, em ordem: Python instalado, checagem da maquina, atalho na
rem area de trabalho e, por fim, sobe o terminal. Cada etapa explica o que
rem esta fazendo e pede confirmacao antes de instalar qualquer coisa.
rem
rem Em batch puro de proposito: numa maquina nova o Python pode nao existir
rem ainda, entao a porta de entrada nao pode depender dele.

echo.
echo   =====================================================
echo     TERMINAL GEX - niveis de gamma
echo     primeira vez? este arquivo faz tudo em ordem
echo   =====================================================
echo.

rem ---------------------------------------------- 1 de 4: Python
echo   [1 de 4]  Procurando o Python...
echo.

set "PY="
where python >nul 2>&1 && set "PY=python"
if not defined PY (
  where py >nul 2>&1 && set "PY=py"
)

if defined PY goto tem_python

echo   O Python nao esta instalado nesta maquina.
echo   Ele e a unica coisa que o projeto precisa.
echo.

where winget >nul 2>&1
if errorlevel 1 goto sem_winget

echo   Posso instalar agora com um comando do proprio Windows:
echo.
echo     winget install -e --id Python.Python.3.13
echo.
echo   Para instalar, aperte uma tecla.
echo   Para desistir, feche esta janela.
echo.
pause
echo.
echo   Instalando. Leva alguns minutos...
echo.

winget install -e --id Python.Python.3.13 --accept-source-agreements --accept-package-agreements

if errorlevel 1 (
  echo.
  echo   A instalacao nao terminou bem. Veja a mensagem acima.
  echo   O arquivo instalar\LEIA-ME-PRIMEIRO.txt tem o plano B.
  echo.
  pause
  exit /b 1
)

echo.
echo   =====================================================
echo     PYTHON INSTALADO - FALTA UM PASSO
echo   =====================================================
echo.
echo   Agora FECHE esta janela e abra o COMECAR.bat de novo.
echo.
echo   Nao e frescura: o Windows monta a lista de programas
echo   quando a janela abre. Esta aqui nasceu antes do Python
echo   existir, entao ela ainda nao o enxerga. A proxima vai.
echo.
pause
exit /b 0

:sem_winget
echo   Este Windows nao tem o winget, entao preciso que voce
echo   instale o Python na mao:
echo.
echo     1. Abra  https://www.python.org/downloads/
echo     2. Baixe e execute o instalador
echo     3. MARQUE a caixinha "Add python.exe to PATH"
echo        na primeira tela - sem ela nada funciona
echo     4. Install Now
echo     5. Volte e abra o COMECAR.bat de novo
echo.
echo   O passo 1 do instalar\LEIA-ME-PRIMEIRO.txt detalha isso.
echo.
pause
exit /b 1

:tem_python
for /f "delims=" %%v in ('%PY% -V 2^>^&1') do set "VER=%%v"
echo   Encontrado: %VER%
echo.

rem ---------------------------------------------- 2 de 4: checagem
echo   [2 de 4]  Conferindo se a maquina esta pronta...
echo.

if not exist "instalar\checar_instalacao.py" (
  echo   Nao achei instalar\checar_instalacao.py
  echo   A pasta parece incompleta. Baixe o projeto de novo.
  echo.
  pause
  exit /b 1
)

%PY% instalar\checar_instalacao.py
if errorlevel 1 (
  echo.
  echo   A checagem encontrou problemas. Resolva o que ela
  echo   apontou e abra o COMECAR.bat de novo.
  echo.
  pause
  exit /b 1
)

rem ---------------------------------------------- 3 de 4: atalho
echo.
echo   [3 de 4]  Atalho na area de trabalho
echo.
echo   Quer um atalho "Terminal GEX" na area de trabalho,
echo   para nao precisar vir nesta pasta toda vez?
echo.
choice /c SN /n /m "   Criar o atalho? [S/N] "
if errorlevel 2 goto sem_atalho

echo.
if exist "criar_atalho.py" (
  %PY% criar_atalho.py
) else (
  echo   Nao achei o criar_atalho.py, seguindo sem o atalho.
)
goto subir

:sem_atalho
echo.
echo   Sem atalho. Para criar depois: CRIAR_ATALHO.bat
echo.

rem ---------------------------------------------- 4 de 4: subir
:subir
echo.
echo   [4 de 4]  Abrindo o terminal
echo.
echo   Vai abrir o navegador em http://localhost:8777
echo.
echo   A janela preta que fica aberta e o MOTOR do painel.
echo   Pode minimizar. Se fechar, o painel para de responder.
echo.
echo   No painel, clique em ATUALIZAR REGIOES. A primeira
echo   carga leva de 40 a 60 segundos.
echo.
pause
echo.

%PY% abrir.py
exit /b
