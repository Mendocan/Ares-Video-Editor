# PyInstaller Build Script
# Bu script, uygulamayi tek bir .exe dosyasi haline getirir.

$ProjectRoot = Get-Location
$EntryScript = Join-Path $ProjectRoot "app\main.py"

Write-Host "Paketleme basliyor..." -ForegroundColor Cyan

# Gerekli paketlerin yuklu oldugundan emin ol
python -m pip install -r requirements.txt

# PyInstaller ile derleme (PATH sorunlarini asmak icin python -m modulu uzerinden)
python -m PyInstaller --noconfirm `
    --onedir `
    --windowed `
    --name "Ares_Editor_2026" `
    --add-data "app;app/" `
    --collect-all qtawesome `
    --distpath "build\dist" `
    --workpath "build\work" `
    $EntryScript

Write-Host "Paketleme tamamlandi! Cikti klasoru: build\dist\Ares_Editor_2026" -ForegroundColor Green
