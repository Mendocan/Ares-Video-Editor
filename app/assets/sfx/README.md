# Ses Efektleri Kutuphanesi

Bu klasor, Ares Video Editor icindeki **Ses Efektleri Kutuphanesi** panelinin
yerel dosya kaynagidir. Alt klasorler (`wind`, `engine`, `gun`, `explosion`)
kategori bazinda ses dosyalarini barindirir.

## Nasil doldurulur?

Uygulama ic agdan (sandbox) dogrudan internete erisip ikili ses dosyasi
indiremedigi icin bu klasorler bos gelir. Uygulama icindeki **Ses Efektleri**
penceresinden ilgili kategoriyi secip **"Kaynagi Ac"** butonuna tikladiginizda,
arastirmada belirlenen en iyi acik kaynak / CC0 lisansli kaynak tarayicida
acilir (bkz. `app/core/sfx_library.py`). Indirdiginiz `.wav` / `.mp3` / `.ogg`
dosyalarini ilgili alt klasore (orn. `explosion/patlama_01.wav`) kopyalayin;
dosyalar otomatik olarak panelde listelenir ve tek tikla timeline'a
eklenebilir.

## Kategoriler ve onerilen kaynaklar

| Kategori | Klasor | Onerilen kaynak | Lisans |
|---|---|---|---|
| Ruzgar | `wind/` | Kenney Audio, OpenGameArt Wind/Ambient SFX | CC0 |
| Motor | `engine/` | Pttn/stk-assets (`engine_large.ogg`, `engine_small.ogg`), Kenney Audio | CC0 / dosya bazinda kontrol |
| Silah | `gun/` | PanderMusubi/sound-effects-library-weapons, Pttn/stk-assets (`shoot.ogg`) | CC0 |
| Patlama | `explosion/` | OpenGameArt "SoundFX Library [CC0]", Pttn/stk-assets (`explosion.ogg`) | CC0 |

CC0 (Creative Commons Zero) lisansli dosyalar atifsiz, ticari projelerde dahi
serbestce kullanilabilir. "Dosya bazinda kontrol" notu olan kaynaklarda her
dosyanin lisansini indirmeden once ilgili depo/README'sinden dogrulayin.
