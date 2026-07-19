Set-Location $PSScriptRoot
Write-Host "build_portable.ps1 kullanin (ZIP + FFmpeg dahil)." -ForegroundColor Yellow
& (Join-Path $PSScriptRoot "build_portable.ps1")
