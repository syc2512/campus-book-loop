$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python)) {
    $python = Join-Path (Split-Path -Parent $root) ".venv\Scripts\python.exe"
}
if (-not (Test-Path -LiteralPath $python)) {
    throw "Run the Python environment setup before seeding the API."
}
Push-Location (Join-Path $root "apps\api")
try {
    & $python -m app.seed
} finally {
    Pop-Location
}
