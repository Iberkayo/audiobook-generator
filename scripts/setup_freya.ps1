$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$ThirdParty = Join-Path $RepoRoot "third_party"
$FreyaDir = Join-Path $ThirdParty "FreyaTTS"

New-Item -ItemType Directory -Force -Path $ThirdParty | Out-Null

if (-not (Test-Path $FreyaDir)) {
    Write-Host "Cloning official FreyaTTS repository..."
    git clone https://github.com/freyavoiceai/FreyaTTS.git $FreyaDir
} else {
    Write-Host "FreyaTTS checkout already exists. Updating..."
    git -C $FreyaDir pull --ff-only
}

Write-Host "Installing FreyaTTS dependencies into the active Python environment..."
python -m pip install -r (Join-Path $FreyaDir "requirements.txt")

Write-Host "Running import smoke test..."
$env:PYTHONPATH = "$FreyaDir;$env:PYTHONPATH"
python -c "from freyatts import FreyaTTS; print('FreyaTTS import OK')"

Write-Host "FreyaTTS setup complete."
