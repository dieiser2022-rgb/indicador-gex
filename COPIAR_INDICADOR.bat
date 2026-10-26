@echo off
title Copiar o indicador do TradingView
cd /d "%~dp0"

rem Chamador. A copia mora no copiar_indicador.py, que le a versao direto do
rem arquivo .pine - assim o aviso na tela nunca fica falando de uma versao
rem antiga, como acontecia quando o numero estava escrito aqui.

set "PY="
where python >nul 2>&1 && set "PY=python"
if not defined PY (
  where py >nul 2>&1 && set "PY=py"
)
if not defined PY (
  echo.
  echo   Nao encontrei o Python neste computador.
  echo.
  pause
  exit /b 1
)

%PY% copiar_indicador.py
exit /b
