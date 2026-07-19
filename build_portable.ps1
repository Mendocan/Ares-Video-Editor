# Ares Editor — portable ZIP paketi olusturur.
# Cikti: release\Ares_Editor_2026_Portable.zip

Set-Location $PSScriptRoot
$ErrorActionPreference = "Stop"

$AppName = "Ares_Editor_2026"
$DistDir = Join-Path $PSScriptRoot "build\dist\$AppName"
$ReleaseDir = Join-Path $PSScriptRoot "release"
$ZipPath = Join-Path $ReleaseDir "${AppName}_Portable.zip"

function Find-SystemFfmpegBin {
    $cmd = Get-Command ffmpeg -ErrorAction SilentlyContinue
    if ($cmd) {
        return Split-Path $cmd.Source -Parent
    }

    $localAppData = $env:LOCALAPPDATA
    if ($localAppData) {
        $packages = Join-Path $localAppData "Microsoft\WinGet\Packages"
        if (Test-Path $packages) {
            $found = Get-ChildItem -Path $packages -Recurse -Filter "ffmpeg.exe" -ErrorAction SilentlyContinue |
                ForEach-Object { Split-Path $_.FullName -Parent } |
                Select-Object -First 1
            if ($found) { return $found }
        }
    }

    return $null
}

function Ensure-FfmpegInDist {
    param([string]$TargetRoot)

    $targetBin = Join-Path $TargetRoot "tools\ffmpeg\bin"
    $ffmpegExe = Join-Path $targetBin "ffmpeg.exe"
    $ffprobeExe = Join-Path $targetBin "ffprobe.exe"

    if ((Test-Path $ffmpegExe) -and (Test-Path $ffprobeExe)) {
        Write-Host "FFmpeg zaten pakette: $targetBin" -ForegroundColor Green
        return
    }

    $sourceBin = Join-Path $PSScriptRoot "tools\ffmpeg\bin"
    if ((Test-Path (Join-Path $sourceBin "ffmpeg.exe")) -and (Test-Path (Join-Path $sourceBin "ffprobe.exe"))) {
        Write-Host "FFmpeg repo tools klasorunden kopyalaniyor..." -ForegroundColor Cyan
        New-Item -ItemType Directory -Force -Path $targetBin | Out-Null
        Copy-Item (Join-Path $sourceBin "*") $targetBin -Force
        return
    }

    $systemBin = Find-SystemFfmpegBin
    if ($systemBin) {
        Write-Host "FFmpeg sistemden kopyalaniyor: $systemBin" -ForegroundColor Cyan
        New-Item -ItemType Directory -Force -Path $targetBin | Out-Null
        Copy-Item (Join-Path $systemBin "ffmpeg.exe") $targetBin -Force
        Copy-Item (Join-Path $systemBin "ffprobe.exe") $targetBin -Force
        return
    }

    Write-Warning "FFmpeg bulunamadi. ZIP olusacak ama export calismayabilir."
    Write-Warning "tools\ffmpeg\bin altina ffmpeg.exe ve ffprobe.exe koyup tekrar calistirin."
}

Write-Host "=== 1/4 Bagimliliklar ===" -ForegroundColor Cyan
python -m pip install -r requirements.txt -q

Write-Host "=== 2/4 PyInstaller derlemesi ===" -ForegroundColor Cyan
python -m PyInstaller Ares_Editor_2026.spec --noconfirm --clean --distpath build\dist --workpath build\work
if ($LASTEXITCODE -ne 0) {
    Write-Error "PyInstaller derlemesi basarisiz."
    exit 1
}

if (-not (Test-Path $DistDir)) {
    Write-Error "Derleme ciktisi bulunamadi: $DistDir"
    exit 1
}

Write-Host "=== 3/4 FFmpeg ve kullanici dosyalari ===" -ForegroundColor Cyan
Ensure-FfmpegInDist -TargetRoot $DistDir
Copy-Item (Join-Path $PSScriptRoot "docs\PORTABLE_README.txt") (Join-Path $DistDir "OKU_BENI.txt") -Force

Write-Host "=== 4/4 ZIP olusturma ===" -ForegroundColor Cyan
New-Item -ItemType Directory -Force -Path $ReleaseDir | Out-Null
if (Test-Path $ZipPath) {
    Remove-Item $ZipPath -Force
}

Compress-Archive -Path $DistDir -DestinationPath $ZipPath -CompressionLevel Optimal

$sizeMb = [math]::Round((Get-Item $ZipPath).Length / 1MB, 1)
Write-Host ""
Write-Host "Portable paket hazir!" -ForegroundColor Green
Write-Host "  Klasor: $DistDir"
Write-Host "  ZIP:    $ZipPath ($sizeMb MB)"
Write-Host ""
Write-Host "GitHub Release icin bu ZIP dosyasini yukleyin." -ForegroundColor Yellow
