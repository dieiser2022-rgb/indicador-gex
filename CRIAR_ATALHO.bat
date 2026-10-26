@echo off
title Criar atalho do Terminal GEX
cd /d "%~dp0"

rem A pasta vai para o PowerShell por variavel de ambiente. Passar caminho
rem dentro da linha de comando quebra quando ele tem espaco ou acento.
set "PASTA=%~dp0"
if "%PASTA:~-1%"=="\" set "PASTA=%PASTA:~0,-1%"

echo.
echo   Criando o atalho do Terminal GEX...
echo.

powershell -NoProfile -ExecutionPolicy Bypass -Command "$p=$env:PASTA; $alvo=Join-Path $p 'GEX.bat'; if(-not (Test-Path $alvo)){ Write-Host '  Nao achei o GEX.bat nesta pasta.'; exit 1 }; $mesa=[Environment]::GetFolderPath('Desktop'); $lnk=Join-Path $mesa 'Terminal GEX.lnk'; $w=New-Object -ComObject WScript.Shell; $s=$w.CreateShortcut($lnk); $s.TargetPath=$alvo; $s.WorkingDirectory=$p; $s.Description='Terminal GEX - niveis de gamma'; $ico=Join-Path $p 'gex.ico'; if(Test-Path $ico){ $s.IconLocation=$ico }; $s.Save(); Write-Host ('  Atalho criado em: ' + $lnk)"

if errorlevel 1 (
  echo.
  echo   Nao consegui criar o atalho. Veja a mensagem acima.
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
echo   Pronto. Dai em diante e um clique no icone.
echo.
pause
