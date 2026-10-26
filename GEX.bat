@echo off
title Terminal GEX - nao feche esta janela
cd /d "%~dp0"

echo.
echo   ========================================
echo     TERMINAL GEX - niveis de gamma
echo   ========================================
echo.

rem Se o terminal ja esta no ar, abrir um segundo daria erro de porta ocupada.
rem Entao neste caso so reabre o painel no navegador.
rem O teste e abrir uma conexao de verdade na porta: e o unico jeito que nao
rem depende do idioma do Windows nem confunde conexao encerrando com servidor
rem ligado, como aconteceria lendo a saida do netstat.
powershell -NoProfile -Command "try{$c=New-Object Net.Sockets.TcpClient;$c.Connect('127.0.0.1',8777);$c.Close();exit 0}catch{exit 1}" >nul 2>&1
if %errorlevel%==0 (
  echo   O terminal ja estava rodando.
  echo   Abrindo o painel no navegador...
  start "" "http://localhost:8777"
  timeout /t 3 >nul
  exit /b 0
)

rem Em algumas instalacoes o comando e "py" em vez de "python".
set "PY="
where python >nul 2>&1 && set "PY=python"
if not defined PY (
  where py >nul 2>&1 && set "PY=py"
)
if not defined PY (
  echo   Nao encontrei o Python neste computador.
  echo.
  echo   Baixe em https://python.org e, durante a instalacao,
  echo   marque a caixa "Add Python to PATH".
  echo.
  pause
  exit /b 1
)

echo   Ligando o servidor...
echo.
echo   Deixe esta janela aberta: ela e o motor do painel.
echo   Se fechar, o painel para de responder.
echo.
echo   Para desligar de proposito: feche a janela.
echo.

%PY% terminal.py

rem Sem esta pausa a janela fecharia junto com o erro e a mensagem sumiria
rem antes de dar tempo de ler.
if errorlevel 1 (
  echo.
  echo   ----------------------------------------
  echo    O terminal fechou com erro.
  echo    O motivo esta na mensagem acima.
  echo   ----------------------------------------
  echo.
  pause
)
exit /b
