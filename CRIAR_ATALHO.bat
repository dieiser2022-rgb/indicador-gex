@echo off
title Criar atalho do Terminal GEX
cd /d "%~dp0"

rem Este .bat e so um chamador. A criacao do atalho mora no criar_atalho.py:
rem montar o comando do PowerShell dentro do cmd exige aspas dentro de aspas
rem e parenteses dentro de "for /f in (...)", que e onde o cmd quebra.

set "PY="
where python >nul 2>&1 && set "PY=python"
if not defined PY (
  where py >nul 2>&1 && set "PY=py"
)
if not defined PY (
  echo.
  echo   Nao encontrei o Python neste computador.
  echo.
  echo   Baixe em https://python.org e, durante a instalacao,
  echo   marque a caixa "Add Python to PATH".
  echo.
  pause
  exit /b 1
)

%PY% criar_atalho.py
exit /b
