@echo off
echo Starting Dialog Backend on port 8001...
cd /d c:\Users\Dell\Desktop\demo\backend\api
c:\Users\Dell\Desktop\demo\backend\venv\Scripts\uvicorn.exe app:app --reload --reload-dir c:\Users\Dell\Desktop\demo\backend\api --reload-dir c:\Users\Dell\Desktop\demo\backend\services --reload-dir c:\Users\Dell\Desktop\demo\backend\config --host 0.0.0.0 --port 8001
