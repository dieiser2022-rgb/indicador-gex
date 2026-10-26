@echo off
title Limpar o cache de icones do Windows
cd /d "%~dp0"

rem Use so se o atalho continuar aparecendo com o icone errado depois de
rem recriado. O Windows guarda os icones em cache pelo nome do arquivo, e o
rem cache nao se atualiza sozinho quando o icone de um atalho muda.

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

%PY% limpar_cache_icone.py
exit /b
