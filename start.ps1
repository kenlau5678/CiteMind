$ErrorActionPreference = "Stop"
$CiteMindRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$BackendPython = Join-Path $CiteMindRoot "backend\.venv\Scripts\python.exe"
$CiteMindPort = if ($Env:CITEMIND_PORT) { [int]$Env:CITEMIND_PORT } else { 8000 }
if ($CiteMindPort -lt 1 -or $CiteMindPort -gt 65535) { throw "CITEMIND_PORT must be between 1 and 65535" }

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
    Write-Host "Created .env. PDF reading works now; add OPENAI_API_KEY later to enable questions." -ForegroundColor Yellow
}

Write-Host "CiteMind is starting at http://127.0.0.1:$CiteMindPort" -ForegroundColor Green
Set-Location (Join-Path $CiteMindRoot "backend")
& $BackendPython -m uvicorn app.main:app --host 127.0.0.1 --port $CiteMindPort --env-file $EnvFile
