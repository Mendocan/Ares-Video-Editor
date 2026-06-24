# Altyazi Renklendirme Araci Plani

## Proje Amaci

TikTok ve benzeri dikey ya da yatay videolarda, ekranda gorunen altyazida aktif kelimeyi farkli renkle vurgulayan, kullanim kolayligi yuksek bir Windows `.exe` araci gelistirmek.

Ilk hedef:

- Video yukleme
- Harici `.srt` yukleme
- Ileride otomatik altyazi uretimi
- Aktif kelimeyi farkli renkle vurgulama
- Beyaz metin + mavi aktif kelime stili
- MP4 olarak disa aktarma

## Hedef Kullanici

- Tek kullanicili, kisisel kullanim
- Hizli sosyal medya video uretimi
- After Effects kadar karmasik olmayan, ama is yapan bir masaustu arac

## MVP Kapsami

Ilk surumde mutlaka olacak ozellikler:

1. Video dosyasi secme
2. `.srt` dosyasi secme
3. Font secimi
4. Normal yazi rengi secimi
5. Aktif kelime rengi secimi
6. Konum secimi: alt orta
7. Boyut, stroke ve golge ayari
8. Onizleme alani
9. Videoyu altyazili olarak disa aktarma

## Ikinci Asama

MVP sonrasi eklenebilecekler:

- Otomatik altyazi olusturma
- Kelime zamanlarini iyilestirme
- Hazir stil sablonlari
- Dikey video presetleri
- Toplu isleme
- Proje kaydet / tekrar yukle
- Daha gelismis animasyonlar

## Teknik Yigin

Onerilen teknoloji:

- Arayuz: `Python + PySide6`
- Video isleme: `FFmpeg`
- Altyazi zamanlama ve render: `ASS subtitle` veya ozel render mantigi
- Otomatik transkripsiyon: `faster-whisper`
- Paketleme: `PyInstaller`

Bu secimin nedeni:

- Hizli prototip cikarmaya uygun
- Windows `.exe` uretmek kolay
- Video ve altyazi isleme icin guclu ekosistem var
- Tek kisilik ozel arac icin verimli

## Temel Is Akisi

1. Kullanici video dosyasini secer.
2. Kullanici `.srt` dosyasini yukler.
3. Sistem altyaziyi satir ve zaman olarak parse eder.
4. Kelime bazli zamanlama verisi olusturulur.
5. Aktif kelime secilen renkle vurgulanir.
6. Onizleme gosterilir.
7. Final video `mp4` olarak disa aktarilir.

## En Kritik Teknik Konu

Normal `.srt` dosyasi tek basina kelime bazli renklendirme icin yeterli degildir.

Bu nedenle iki yaklasim var:

1. `.srt` verisini uygulama icinde kelime seviyesine ayirip ozel render etmek
2. `ASS` tabanli bir ara format uretip FFmpeg ile videoya gommek

Baslangic icin en guvenli yol:

- Uygulama icinde kelime bazli mantigi kurmak
- Son ciktiyi FFmpeg ile video ustune islemek

## Onerilen Klasor Yapisi

```text
C:\Ares_Edit
|-- plan.md
|-- app
|   |-- main.py
|   |-- ui
|   |-- core
|   |-- services
|   |-- assets
|-- samples
|-- output
|-- docs
|-- build
```

## Gelistirme Asamalari

### Asama 1 - Plan ve Iskelet

- Proje klasor yapisini kur
- Arayuz iskeletini olustur
- Video ve `.srt` secme alanlarini ekle

### Asama 2 - Altyazi Motoru

- `.srt` parser yaz
- Kelime bazli isleme mantigini kur
- Aktif kelime renklendirmesini uygula

### Asama 3 - Onizleme

- Secilen font, renk ve konumu goster
- Kisa onizleme olustur

### Asama 4 - Export

- FFmpeg ile final render al
- MP4 cikti uret

### Asama 5 - Paketleme

- `.exe` uret
- Tek klasorlu dagitim hazirla

## Basari Kriterleri

Proje basarili sayilirsa:

- Program Windows'ta acilir
- Video ve `.srt` secilebilir
- Aktif kelime secilen renge doner
- Cikti bozulmadan alinabilir
- Kullanici teknik bilgi olmadan islem yapabilir

## Ilk Yapilacaklar

Bir sonraki adimda:

1. Proje klasor iskeletini olusturmak
2. Basit masaustu arayuzu kurmak
3. Video + `.srt` secme ekranini yapmak
4. Sonra altyazi motoruna gecmek

