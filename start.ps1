$ErrorActionPreference = "Stop"
$CiteMindRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$BackendPython = Join-Path $CiteMindRoot "backend\.venv\Scripts\python.exe"

if (-not (Test-Path $BackendPython)) {
    python -m venv (Join-Path $CiteMindRoot "backend\.venv")
}

& $BackendPython -m pip install --quiet --disable-pip-version-check -r (Join-Path $CiteMindRoot "backend\requirements.txt")

if (-not (Test-Path (Join-Path $CiteMindRoot "frontend\node_modules"))) {
    npm install --prefix (Join-Path $CiteMindRoot "frontend")
}
npm run build --prefix (Join-Path $CiteMindRoot "frontend")

$EnvFile = Join-Path $CiteMindRoot ".env"
if (-not (Test-Path $EnvFile)) {
    Copy-Item (Join-Path $CiteMindRoot ".env.example") $EnvFile
    Write-Host "Created .env. Add OPENAI_API_KEY to enable questions." -ForegroundColor Yellow
}

Write-Host "CiteMind is starting at http://127.0.0.1:8000" -ForegroundColor Green
Set-Location (Join-Path $CiteMindRoot "backend")
& $BackendPython -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --env-file $EnvFile

