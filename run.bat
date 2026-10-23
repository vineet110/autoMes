@echo off
cd /d "%~dp0"
if not exist .env (
  copy .env.example .env >nul
  echo Created .env - open it, fill in your email account, then run this again.
  notepad .env
  exit /b
)
pip install -q -r requirements.txt

rem Build the web interface the first time (needs Node.js). Delete frontend\out to rebuild.
if not exist frontend\out\index.html (
  where npm >nul 2>nul && (
    echo Building the web interface - first run only, takes a minute...
    pushd frontend
    call npm install --silent
    call npm run build
    popd
  ) || echo Node.js not found - using the classic interface. Install Node.js for the new one.
)

start "" http://127.0.0.1:8000
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
