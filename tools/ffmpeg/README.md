# FFmpeg (portable paket icin)

`build_portable.ps1` calistirildiginda bu klasore FFmpeg kopyalanir ve ZIP icine dahil edilir.

Gerekli dosyalar (`bin` altinda):

- `ffmpeg.exe`
- `ffprobe.exe`

## Manuel hazirlik

1. https://www.gyan.dev/ffmpeg/builds/ adresinden **ffmpeg-release-essentials** indirin.
2. Arsivden `bin` icindeki `ffmpeg.exe` ve `ffprobe.exe` dosyalarini su klasore koyun:

```
tools/ffmpeg/bin/ffmpeg.exe
tools/ffmpeg/bin/ffprobe.exe
```

## Otomatik (build sirasinda)

`build_portable.ps1` once bu klasore bakar; yoksa sistemdeki (WinGet/PATH) FFmpeg'i kopyalar.
