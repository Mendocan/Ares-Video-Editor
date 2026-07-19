# Ares Video Editor

Windows için masaüstü video editörü: çok şeritli timeline, FFmpeg ile dışa aktarma ve altyazı araçları. **Python** ve **PySide6** ile geliştirilmiştir.

## Özellikler

- **Timeline** — video, ses ve altyazı şeritleri; kesme, bölme, taşıma, ripple/slip
- **Filmstrip önizleme** — klip üzerinde küçük kare önizlemeleri
- **Oynatma** — önizleme oynatıcı, playhead ile scrub
- **Dışa aktarma** — FFmpeg ile MP4 (gömülü altyazı, logo, efektler, isteğe bağlı NVENC)
- **Altyazı** — SRT içe aktarma, stil, kelime zamanlaması, Whisper ile otomatik üretim
- **Proje** — `.aresproj` kaydet / aç
- **Toplu dışa aktarma** — aynı ayarlarla birden fazla video

---

## Son kullanıcı — indir ve çalıştır (Portable)

Python veya kurulum **gerekmez**. GitHub Releases sayfasından ZIP indirin:

1. [Releases](https://github.com/Mendocan/Ares-Video-Editor/releases) sayfasına gidin
2. En son sürümde **`Ares_Editor_2026_Portable.zip`** dosyasını indirin
3. ZIP’i bir klasöre çıkartın (ör. `D:\Ares_Editor`)
4. **`Ares_Editor_2026.exe`** dosyasını çalıştırın
5. Klasördeki **`OKU_BENI.txt`** dosyasına bakın

### Gereksinimler (portable)

| Gereksinim | Açıklama |
|------------|----------|
| Windows 10/11 (64-bit) | Birincil hedef platform |
| FFmpeg | Portable pakette **`tools\ffmpeg\bin`** içinde gelir; ayrı kurulum gerekmez |
| İnternet (isteğe bağlı) | Whisper ile ilk altyazı üretiminde model indirilir |
| NVIDIA GPU (isteğe bağlı) | NVENC ile daha hızlı export |

### FFmpeg nedir?

**FFmpeg**, videoyu işleyen arka plan motorudur. Ares arayüzü tek başına video encode edemez; şu işler FFmpeg ile yapılır:

- MP4 **dışa aktarma**
- **Gerçek önizleme (kare)** — altyazılı kare render
- Timeline **filmstrip** ve **waveform** görselleri
- Video **süre / format** bilgisi (`ffprobe`)

Portable sürümde bu araçlar pakete dahildir.

---

## Geliştirici — kaynak koddan çalıştırma

### Gereksinimler

- **Python 3.10+**
- **FFmpeg** — `PATH` üzerinde olmalı veya `tools\ffmpeg\bin` içine konulmalı

```powershell
winget install Gyan.FFmpeg
```

İsteğe bağlı: NVIDIA GPU (NVENC), `faster-whisper` (otomatik altyazı)

### Hızlı başlangıç

```powershell
cd Ares-Video-Editor
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app\main.py
```

Veya:

```powershell
.\run.ps1
```

### Kullanım

1. **İçe aktar** — sidebar, araç çubuğu veya sürükle-bırak ile video ekleyin
2. **Düzenle** — timeline’da kesin, playhead’de bölün, efekt uygulayın
3. **Altyazı** (isteğe bağlı) — SRT yükleyin veya Whisper ile üretin
4. **Dışa aktar** — format, çözünürlük ve kalite seçerek MP4 kaydedin

---

## Portable paket oluşturma (yayıncı)

Geliştirici makinede:

```powershell
.\build_portable.ps1
```

**Çıktılar:**

| Dosya | Açıklama |
|-------|----------|
| `build\dist\Ares_Editor_2026\` | Çalıştırılabilir klasör |
| `release\Ares_Editor_2026_Portable.zip` | Son kullanıcıya verilecek arşiv |

Script, FFmpeg’i sırayla şuradan arar ve pakete kopyalar:

1. `tools\ffmpeg\bin\` (repo içi)
2. Sistemdeki kurulum (PATH / WinGet)

FFmpeg’i elle hazırlamak için: `tools\ffmpeg\README.md`

---

## GitHub Release yükleme

`gh` CLI yüklü değilse **tarayıcıdan** yükleyin (`gh` şart değil):

1. https://github.com/Mendocan/Ares-Video-Editor/releases adresine gidin
2. **Draft a new release** (veya **Create a new release**)
3. **Tag:** örn. `v2026.07.06`
4. **Title:** örn. `Ares Editor 2026 — Portable`
5. **Attach binaries:** `release\Ares_Editor_2026_Portable.zip` dosyasını sürükleyin
6. Kısa not örneği:

   ```
   Windows portable sürüm. Kurulum gerekmez.
   - FFmpeg dahil
   - ZIP'i açın, Ares_Editor_2026.exe çalıştırın
   - Whisper ilk kullanımda model indirir
   ```

7. **Publish release**

### `gh` CLI ile (isteğe bağlı)

Önce GitHub CLI kurun:

```powershell
winget install GitHub.cli
```

Ardından:

```powershell
gh auth login
gh release create v2026.07.06 `
  --title "Ares Editor 2026 — Portable" `
  --notes "Windows portable ZIP. FFmpeg dahil. Kurulum gerekmez." `
  release\Ares_Editor_2026_Portable.zip
```

`gh` tanınmıyorsa terminali kapatıp yeniden açın veya `gh` yerine yukarıdaki tarayıcı yöntemini kullanın.

---

## Proje yapısı

```
app/
  main.py              # Giriş noktası
  core/                # Timeline, altyazı, FFmpeg yardımcıları
  services/            # Export, thumbnail, transkripsiyon, proje
  ui/                  # Ana pencere, timeline, diyaloglar
tools/ffmpeg/          # Portable paket için FFmpeg (build sırasında)
build_portable.ps1     # Portable ZIP oluşturur
release/               # Oluşan ZIP (git'e eklenmez)
docs/PORTABLE_README.txt
requirements.txt
run.ps1
```

## FFmpeg sorun giderme (geliştirici)

Export veya thumbnail hatası alırsanız:

```powershell
winget install Gyan.FFmpeg
```

veya `setup_ffmpeg_path.ps1` çalıştırın, ya da `ARES_FFMPEG_BIN` ortam değişkenine `bin` klasörünü yazın.

## Durum

Aktif geliştirme aşamasında. Sürümler arasında uyumsuzluk olabilir.
