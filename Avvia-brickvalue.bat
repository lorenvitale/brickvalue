@echo off
chcp 65001 >nul
title brickvalue
cd /d "%~dp0"

echo ============================================
echo            brickvalue - avvio
echo ============================================
echo.

rem --- Trova Python ---
set "PYCMD="
where py >nul 2>nul && set "PYCMD=py -3"
if not defined PYCMD ( where python >nul 2>nul && set "PYCMD=python" )
if not defined PYCMD (
  echo  [!] Python non risulta installato.
  echo.
  echo  1. Scaricalo da:  https://www.python.org/downloads/
  echo  2. Durante l'installazione SPUNTA "Add Python to PATH".
  echo  3. Poi fai di nuovo doppio clic su questo file.
  echo.
  pause
  exit /b 1
)

rem --- Ambiente virtuale (solo al primo avvio) ---
if not exist ".venv\Scripts\activate.bat" (
  echo  Primo avvio: preparo l'ambiente, puo' richiedere 1-2 minuti...
  %PYCMD% -m venv .venv
  if errorlevel 1 ( echo  [!] Impossibile creare l'ambiente. & pause & exit /b 1 )
)
call ".venv\Scripts\activate.bat"

rem --- Dipendenze ---
python -m pip install --upgrade pip --quiet
pip install -e . --quiet
if errorlevel 1 ( echo  [!] Errore nell'installazione delle dipendenze. & pause & exit /b 1 )

echo.
echo  brickvalue e' pronto su:   http://127.0.0.1:8000
echo  La pagina si apre da sola tra pochi secondi.
echo  Per spegnere: chiudi questa finestra.
echo.

rem --- Apre il browser dopo qualche secondo, mentre il server parte ---
start "" /b cmd /c "timeout /t 4 >nul & explorer http://127.0.0.1:8000"

python -m brickvalue --port 8000
