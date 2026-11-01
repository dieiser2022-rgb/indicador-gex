@echo off
title Checagem de instalacao - Terminal GEX
cd /d "%~dp0"

rem Roda a checagem do passo 3 do LEIA-ME-PRIMEIRO.txt.

set "PY="
where python >nul 2>&1 && set "PY=python"
if not defined PY (
  where py >nul 2>&1 && set "PY=py"
)
if not defined PY (
  echo.
  echo   ====================================================
  echo    O PYTHON NAO ESTA INSTALADO, OU FALTOU UMA CAIXINHA
  echo   ====================================================
  echo.
  echo   O Windows nao conhece o comando "python".
  echo.
  echo   Quase sempre e isto: o Python foi instalado, mas a
  echo   caixinha "Add python.exe to PATH" nao foi marcada na
  echo   primeira tela do instalador.
  echo.
  echo   Volte ao PASSO 1 do LEIA-ME-PRIMEIRO.txt desta pasta.
  echo.
  pause
  exit /b 1
)

%PY% checar_instalacao.py
exit /b
