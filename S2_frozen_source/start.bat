@echo off
REM BioLitEvidence Finder - Windows one-click starter.
REM First run installs dependencies; subsequent runs just start the servers.

setlocal enabledelayedexpansion

echo ============================================
echo  BioLitEvidence Finder - starting...
echo ============================================

REM --- Backend ---
pushd "%~dp0backend"
if not exist ".venv\Scripts\python.exe" (
    echo [setup] Creating Python virtualenv...
    where python >nul 2>nul || ( echo Python 3.11+ is required. && popd && exit /b 1 )
    python -m venv .venv
    call .venv\Scripts\activate.bat
    python -m pip install --upgrade pip
    pip install -r requirements.txt
) else (
    call .venv\Scripts\activate.bat
)
if not exist ".env" (
    echo [setup] Copying .env.example to .env (edit this file to add API keys^)
    copy /Y .env.example .env >nul
)
start "BioLit backend" cmd /k ".venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000"
popd

REM --- Frontend ---
pushd "%~dp0frontend"
if not exist "node_modules" (
    echo [setup] Installing frontend dependencies...
    where npm >nul 2>nul || ( echo Node.js 18+ is required. && popd && exit /b 1 )
    call npm install
)
start "BioLit frontend" cmd /k "npm run dev -- --host 0.0.0.0 --port 5173"
popd

echo.
echo ============================================
echo  BioLitEvidence Finder is starting up.
echo  Frontend: http://localhost:5173
echo  Backend:  http://localhost:8000/docs
echo ============================================
echo  Two console windows opened. Closing them stops the servers.
echo.
pause
