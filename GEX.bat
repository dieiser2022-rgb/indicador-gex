@echo off
title Terminal GEX - nao feche esta janela
cd /d "%~dp0"

rem Este .bat e so para quem prefere dar duplo clique aqui na pasta. Quem usa
rem o atalho da barra de tarefas nem passa por ele: o atalho chama o
rem python.exe direto, porque atalho de .bat nao aceita icone proprio.
rem
rem Toda a logica (testar se ja esta no ar, segurar a janela no erro) mora no
rem abrir.py, para nao existir em dois lugares e sair de sincronia.

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

%PY% abrir.py
exit /b
