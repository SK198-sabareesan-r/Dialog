@echo off
echo Starting Dialog Backend on port 8000...
start "Dialog Backend" cmd /k "cd /d c:\Users\Dell\Desktop\demo\backend\api && c:\Users\Dell\Desktop\demo\backend\venv\Scripts\uvicorn.exe app:app --reload --reload-dir c:\Users\Dell\Desktop\demo\backend\api --reload-dir c:\Users\Dell\Desktop\demo\backend\services --reload-dir c:\Users\Dell\Desktop\demo\backend\config --host 0.0.0.0 --port 8000"

echo Starting Dialog Frontend on port 3000...
start "Dialog Frontend" cmd /k "cd /d c:\Users\Dell\Desktop\demo\frontend && npm start"

echo.
echo Backend : http://localhost:8000
echo Frontend: http://localhost:3000
echo API Docs: http://localhost:8000/docs
