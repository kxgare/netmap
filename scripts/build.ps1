$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot
$PythonExecutable = Join-Path $ProjectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path $PythonExecutable)) {
    throw 'Сначала создайте .venv и установите зависимости согласно README.md.'
}
& $PythonExecutable -m pytest -q
if ($LASTEXITCODE -ne 0) { throw 'Тесты завершились с ошибкой.' }
& $PythonExecutable -m PyInstaller --noconfirm --clean NetMap.spec
if ($LASTEXITCODE -ne 0) { throw 'Сборка завершилась с ошибкой.' }
Write-Host 'Готово: dist\NetMap\NetMap.exe. Распространяйте всю папку dist\NetMap.'
