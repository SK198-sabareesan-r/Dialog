# How to Start the Application

## Backend Server

### Option 1: PowerShell (Windows)
```powershell
# Navigate to backend directory
cd backend

# Activate virtual environment
.\venv\Scripts\Activate.ps1

# If you get execution policy error, run this first:
# Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Navigate to api directory and start server
cd api
python app.py
```

### Option 2: Git Bash / WSL
```bash
# Navigate to backend directory
cd backend

# Activate virtual environment
source venv/Scripts/activate

# Navigate to api directory and start server
cd api
python app.py
```

### Option 3: Direct Python Path (No activation needed)
```powershell
# From backend directory
cd backend\api
..\venv\Scripts\python.exe app.py
```

The backend API will be available at:
- **API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/api/health

---

## Frontend Server

### In a new terminal:
```bash
# Navigate to frontend directory
cd frontend

# Install dependencies (first time only)
npm install

# Start development server
npm start
```

The frontend will be available at:
- **Application**: http://localhost:3000

---

## Quick Start (Both Servers)

### Terminal 1 - Backend:
```powershell
cd backend\api
..\venv\Scripts\python.exe app.py
```

### Terminal 2 - Frontend:
```bash
cd frontend
npm start
```

---

## Troubleshooting

### Backend Issues

**"ModuleNotFoundError"**
- Make sure you're using the venv Python: `venv\Scripts\python.exe`
- OR activate the venv first: `.\venv\Scripts\Activate.ps1`

**"Execution policy error"**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

**"Cannot find module 'apscheduler'"**
```powershell
cd backend
.\venv\Scripts\pip.exe install -r requirements.txt
```

**Port 8000 already in use**
- Check if another instance is running
- Kill the process: `taskkill /F /IM python.exe`
- Or change the port in `app.py`

### Frontend Issues

**"npm not found"**
- Install Node.js from https://nodejs.org/

**"Module not found"**
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
```

**Port 3000 already in use**
- The app will prompt you to use another port
- Or kill the process

---

## Logs

Backend logs are stored in:
```
backend/logs/
├── application.log  # All logs
├── errors.log      # Only errors
└── activity.log    # Daily activity
```

View logs in real-time:
```bash
# Application log
tail -f backend/logs/application.log

# Error log
tail -f backend/logs/errors.log
```

---

## Stopping the Servers

- Press `Ctrl+C` in each terminal to stop the servers
- Or close the terminal windows

---

## Environment Configuration

Make sure your `.env` file is configured:
```
backend/config/.env
```

Required settings:
- AWS credentials
- S3 bucket name
- Bedrock Knowledge Base ID
- Data Source ID

See `backend/config/.env.example` for reference.
