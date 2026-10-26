@echo off
title Diagnostico do Terminal GEX
cd /d "%~dp0"

rem Imprime na tela o estado do icone, dos atalhos e da porta. A saida e para
rem ser copiada e colada no chat: responde de uma vez o que levaria varias
rem rodadas de tentativa e erro.

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

%PY% diagnostico.py
exit /b
