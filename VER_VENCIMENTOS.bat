@echo off
title Vencimentos da cadeia de opcoes
cd /d "%~dp0"

rem Lista os vencimentos que a CBOE esta entregando e checa se o 0DTE chegou.
rem Sem argumento olha o NDX (indice do Nasdaq). Para outro ativo, abra o
rem prompt e rode:  python ver_vencimentos.py SPX

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

%PY% ver_vencimentos.py NDX SPX
exit /b
