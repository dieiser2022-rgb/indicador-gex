@echo off
title Atualizar o Terminal GEX
cd /d "%~dp0"

echo.
echo   Buscando a versao mais nova do codigo...
echo.

git pull origin terminal-completo

if errorlevel 1 (
  echo.
  echo   Nao conseguiu atualizar. O motivo esta acima.
  echo   Se falar de "local changes", avise que alguem
  echo   editou os arquivos aqui na pasta.
) else (
  echo.
  echo   Atualizado.
  echo.
  echo   Se o terminal estava aberto, feche a janela dele
  echo   e abra de novo para valer a versao nova.
)

echo.
pause
