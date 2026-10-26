@echo off
title Copiar o indicador do TradingView
cd /d "%~dp0"

set "ARQ=indicadores\tradingview_gex.pine"

if not exist "%ARQ%" (
  echo.
  echo   Nao achei o arquivo %ARQ%
  echo.
  pause
  exit /b 1
)

type "%ARQ%" | clip

echo.
echo   ========================================
echo    INDICADOR COPIADO
echo   ========================================
echo.
echo   Agora no TradingView:
echo.
echo   1. Abra o Pine Editor, no rodape do grafico
echo   2. Clique no meio do codigo
echo   3. CTRL+A para selecionar tudo, e DELETE
echo   4. CTRL+V para colar o novo
echo   5. Clique em Save, e depois em Add to chart
echo.
echo   No grafico tem que aparecer o aviso "GEX v4".
echo   Se nao aparecer, a colagem nao pegou.
echo.
pause
