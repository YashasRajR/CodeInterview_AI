@echo off
REM Starts CodeInterview AI on Windows (run setup steps in README.md once first).
echo Starting CodeInterview AI...

start "Ollama" cmd /c "ollama serve"
start "Backend (Flask)" cmd /k "cd /d %~dp0backend && call venv\Scripts\activate && python app.py"
start "Frontend (React)" cmd /k "cd /d %~dp0frontend && npm run dev"

timeout /t 6 /nobreak >nul
start http://localhost:5173
