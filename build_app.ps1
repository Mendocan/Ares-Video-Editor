Set-Location $PSScriptRoot

if (-not (Get-Command pyinstaller -ErrorAction SilentlyContinue)) {
    Write-Error "PyInstaller bulunamadi. Once: pip install -r requirements.txt"
    exit 1
}

pyinstaller Ares_Editor_2026.spec --noconfirm --clean

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "Derleme tamamlandi: build\dist\Ares_Editor_2026\Ares_Editor_2026.exe"
}
