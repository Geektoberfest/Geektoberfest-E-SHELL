# run.ps1 ( we have to make this )
$ErrorActionPreference = "Stop"

# Move to the directory containing this scrit (epic)
Set-Location $PSScriptRoot

# Use the virtual environment if available 
$python = Join-Path $PSScriptRoot "venv\Scripts\python.exe"

# fallback
if (-not (Test-Path $python)) {
    Write-Host "Virtual environment not found. Creating one..."
    py -3 -m venv venv
    .\venv\Scripts\python.exe -m pip install -r requirements.txt
}

# Run E-SHELL
& $python assistant.py

exit $LASTEXITCODE
