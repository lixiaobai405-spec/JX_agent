@echo off
setlocal

set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"

echo [JX Agent] Project root: "%ROOT%"

where uv >nul 2>nul
if errorlevel 1 (
  echo [JX Agent] ERROR: uv was not found in PATH.
  echo Install uv or open a terminal where uv is available, then run this script again.
  pause
  exit /b 1
)

where npm >nul 2>nul
if errorlevel 1 (
  echo [JX Agent] ERROR: npm was not found in PATH.
  echo Install Node.js/npm or open a terminal where npm is available, then run this script again.
  pause
  exit /b 1
)

if not exist "%ROOT%\.env" (
  if exist "%ROOT%\.env_example" (
    copy "%ROOT%\.env_example" "%ROOT%\.env" >nul
    echo [JX Agent] .env was missing, copied from .env_example.
  ) else (
    echo [JX Agent] ERROR: .env is missing and .env_example was not found.
    pause
    exit /b 1
  )
)

if not exist "%ROOT%\.venv\Scripts\python.exe" (
  echo [JX Agent] ERROR: .venv was not found.
  echo Run this command first:
  echo   uv sync
  pause
  exit /b 1
)

if not exist "%ROOT%\frontend\node_modules" (
  echo [JX Agent] ERROR: frontend dependencies were not found.
  echo Run these commands first:
  echo   cd frontend
  echo   npm install
  pause
  exit /b 1
)

echo [JX Agent] Starting backend and frontend...

start "JX Agent Backend" powershell -NoExit -ExecutionPolicy Bypass -Command "Set-Location -LiteralPath '%ROOT%'; uv run python -m uvicorn main:app --host 0.0.0.0 --port 8000"
start "JX Agent Frontend" powershell -NoExit -ExecutionPolicy Bypass -Command "Set-Location -LiteralPath '%ROOT%\frontend'; npm run dev"

echo [JX Agent] Backend:  http://localhost:8000
echo [JX Agent] API docs: http://localhost:8000/docs
echo [JX Agent] Frontend: http://localhost:5173
echo.
echo Close the two opened PowerShell windows to stop the services.
pause

endlocal
