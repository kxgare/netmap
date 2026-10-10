$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot
$PythonExecutable = Join-Path $ProjectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path $PythonExecutable)) {
    throw 'Сначала создайте .venv и установите зависимости согласно README.md.'
}
& $PythonExecutable -m netmap
exit $LASTEXITCODE
