@echo off
title Arrumar o icone do Terminal GEX
cd /d "%~dp0"

rem Rode DEPOIS de fixar o atalho na barra de tarefas. Este script reescreve
rem o icone do atalho que o Windows criou ao fixar, e manda o Explorer reler.

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

%PY% arrumar_icone.py
exit /b
