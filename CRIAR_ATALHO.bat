@echo off
title Criar atalho do Terminal GEX
cd /d "%~dp0"

rem A pasta vai para o PowerShell por variavel de ambiente. Passar caminho
rem dentro da linha de comando quebra quando ele tem espaco ou acento.
set "PASTA=%~dp0"
if "%PASTA:~-1%"=="\" set "PASTA=%PASTA:~0,-1%"

echo.
echo   Preparando o atalho do Terminal GEX...
echo.

rem Em algumas instalacoes o comando e "py" em vez de "python".
set "PY="
where python >nul 2>&1 && set "PY=python"
if not defined PY (
  where py >nul 2>&1 && set "PY=py"
)
if not defined PY (
  echo   Nao encontrei o Python neste computador.
  echo.
  echo   Baixe em https://python.org e, durante a instalacao,
  echo   marque a caixa "Add Python to PATH".
  echo.
  pause
  exit /b 1
)

rem O atalho precisa apontar para o python.exe, e nao para um .bat: o Windows
rem resolve atalho de .bat ate o cmd.exe e fixa o icone do cmd na barra de
rem tarefas, jogando fora o icone configurado. Quem sabe o caminho exato do
rem executavel e o proprio Python, por sys.executable.
set "PYEXE="
for /f "usebackq delims=" %%i in (`%PY% -c "import sys;print(sys.executable)"`) do set "PYEXE=%%i"
if not defined PYEXE (
  echo   Nao consegui descobrir onde o python.exe esta instalado.
  echo.
  pause
  exit /b 1
)

echo   Python encontrado em:
echo   %PYEXE%
echo.

rem As aspas dos argumentos entram como [char]34. Escrever aspas dentro de
rem aspas aqui seria um festival de barras invertidas.
powershell -NoProfile -ExecutionPolicy Bypass -Command "$p=$env:PASTA; $exe=$env:PYEXE; $script=Join-Path $p 'abrir.py'; if(-not (Test-Path $script)){ Write-Host '  Nao achei o abrir.py nesta pasta.'; exit 1 }; if(-not (Test-Path $exe)){ Write-Host '  O caminho do python.exe nao existe.'; exit 1 }; $q=[char]34; $mesa=[Environment]::GetFolderPath('Desktop'); $lnk=Join-Path $mesa 'Terminal GEX.lnk'; $w=New-Object -ComObject WScript.Shell; $s=$w.CreateShortcut($lnk); $s.TargetPath=$exe; $s.Arguments=($q + $script + $q); $s.WorkingDirectory=$p; $s.Description='Terminal GEX - niveis de gamma'; $s.WindowStyle=1; $ico=Join-Path $p 'gex.ico'; if(Test-Path $ico){ $s.IconLocation=($ico + ',0') }; $s.Save(); Write-Host ('  Atalho criado em: ' + $lnk)"

if errorlevel 1 (
  echo.
  echo   Nao consegui criar o atalho. O motivo esta acima.
  echo.
  pause
  exit /b 1
)

echo.
echo   ========================================
echo    AGORA FIXE NA BARRA DE TAREFAS
echo   ========================================
echo.
echo   1. Va na area de trabalho
echo   2. Clique com o botao direito em "Terminal GEX"
echo   3. No Windows 11, clique em "Mostrar mais opcoes"
echo   4. Clique em "Fixar na barra de tarefas"
echo.
echo   Se antes voce fixou a versao que virou icone de cmd,
echo   clique com o botao direito nela e desafixe primeiro.
echo.
pause
