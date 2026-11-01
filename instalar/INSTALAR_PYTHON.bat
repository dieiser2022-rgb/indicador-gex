@echo off
title Instalar o Python pelo winget
cd /d "%~dp0"

rem Instala o Python usando o winget, o gerenciador de pacotes que ja vem no
rem Windows 10 e 11. Evita o erro mais comum da instalacao manual: esquecer de
rem marcar a caixinha "Add python.exe to PATH".
rem
rem Nao roda nada sem confirmacao: instalar programa e acao que o usuario tem
rem que autorizar.

echo.
echo   ====================================================
echo    INSTALAR O PYTHON
echo   ====================================================
echo.

rem Ja esta instalado? Entao nao ha nada a fazer.
set "PY="
where python >nul 2>&1 && set "PY=python"
if not defined PY (
  where py >nul 2>&1 && set "PY=py"
)
if defined PY (
  echo   O Python JA ESTA instalado nesta maquina:
  echo.
  %PY% --version
  echo.
  echo   Nao precisa instalar nada. Siga para o PASSO 3:
  echo   duplo clique em CHECAR.bat
  echo.
  pause
  exit /b 0
)

rem O winget existe? No Windows 10 ele vem pelo "App Installer" da Microsoft
rem Store, e em instalacoes antigas pode nao estar presente.
where winget >nul 2>&1
if errorlevel 1 (
  echo   Este computador nao tem o winget.
  echo.
  echo   Duas saidas:
  echo.
  echo   1. Instale o "App Installer" pela Microsoft Store
  echo      e rode este arquivo de novo.
  echo.
  echo   2. Ou instale o Python na mao, pelo site:
  echo        https://www.python.org/downloads/
  echo      Nesse caso, MARQUE a caixinha
  echo        "Add python.exe to PATH"
  echo      na primeira tela do instalador.
  echo.
  echo   O PASSO 1 do LEIA-ME-PRIMEIRO.txt explica em detalhe.
  echo.
  pause
  exit /b 1
)

echo   O winget foi encontrado. O comando que vou rodar e:
echo.
echo     winget install -e --id Python.Python.3.13
echo.
echo   Ele baixa e instala o Python da fonte oficial, e ja
echo   configura o PATH sozinho.
echo.
echo   Se preferir nao instalar agora, feche esta janela.
echo.
pause

echo.
echo   Instalando. Isso leva alguns minutos...
echo.

winget install -e --id Python.Python.3.13 --accept-source-agreements --accept-package-agreements

if errorlevel 1 (
  echo.
  echo   ----------------------------------------------------
  echo    A INSTALACAO NAO TERMINOU BEM
  echo   ----------------------------------------------------
  echo.
  echo   Veja a mensagem acima. Se falar que o pacote nao foi
  echo   encontrado, tente uma versao anterior:
  echo.
  echo     winget install -e --id Python.Python.3.12
  echo.
  echo   Ou instale na mao pelo site, como explica o PASSO 1
  echo   do LEIA-ME-PRIMEIRO.txt.
  echo.
  pause
  exit /b 1
)

echo.
echo   ====================================================
echo    INSTALADO
echo   ====================================================
echo.
echo   IMPORTANTE: feche esta janela e abra outra.
echo.
echo   O Windows so enxerga o Python novo em janelas abertas
echo   DEPOIS da instalacao. Nesta aqui ele ainda nao existe.
echo.
echo   Na janela nova, confira com:
echo     python --version
echo.
echo   Depois siga para o PASSO 3: duplo clique em CHECAR.bat
echo.
echo   Se o comando "python" abrir a Microsoft Store em vez de
echo   mostrar a versao, veja a secao "SE DER PROBLEMA" do
echo   LEIA-ME-PRIMEIRO.txt - e um atalho do Windows que
echo   precisa ser desligado.
echo.
pause
exit /b
