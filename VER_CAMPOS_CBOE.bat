@echo off
title Campos que a CBOE entrega
cd /d "%~dp0"

rem Mostra quais campos vem em cada contrato de opcao, e quantos contratos tem
rem cada campo preenchido. Serve para saber se colunas como volume e delta sao
rem viaveis antes de prometer que sao.

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

%PY% ver_campos_cboe.py NDX
exit /b
