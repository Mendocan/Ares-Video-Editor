# FFmpeg'i kullanici PATH'ine kalici ekler (WinGet / yerel kurulum).
Set-Location $PSScriptRoot

function Find-FfmpegBin {
    $cmd = Get-Command ffmpeg -ErrorAction SilentlyContinue
    if ($cmd) {
        return Split-Path $cmd.Source -Parent
    }

    $localAppData = $env:LOCALAPPDATA
    if ($localAppData) {
        $packages = Join-Path $localAppData "Microsoft\WinGet\Packages"
        if (Test-Path $packages) {
            $bins = Get-ChildItem -Path $packages -Recurse -Filter "ffmpeg.exe" -ErrorAction SilentlyContinue |
                ForEach-Object { Split-Path $_.FullName -Parent } |
                Select-Object -First 1
            if ($bins) { return $bins }
        }
    }

    $projectBin = Join-Path $PSScriptRoot "tools\ffmpeg\bin"
    if (Test-Path (Join-Path $projectBin "ffmpeg.exe")) {
        return $projectBin
    }

    return $null
}

$ffmpegBin = Find-FfmpegBin
if (-not $ffmpegBin) {
    Write-Error "ffmpeg.exe bulunamadi. Once: winget install Gyan.FFmpeg"
    exit 1
}

$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($userPath -notlike "*$ffmpegBin*") {
    $newPath = if ([string]::IsNullOrWhiteSpace($userPath)) { $ffmpegBin } else { "$userPath;$ffmpegBin" }
    [Environment]::SetEnvironmentVariable("Path", $newPath, "User")
    $env:Path = "$ffmpegBin;" + $env:Path
    Write-Host "FFmpeg PATH'e eklendi: $ffmpegBin"
} else {
    Write-Host "FFmpeg zaten PATH'te: $ffmpegBin"
}

ffmpeg -version | Select-Object -First 1
