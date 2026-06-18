# LSB Steganografi Metrik Analizörü

24 bit renkli (24bpp RGB) görüntülerde LSB (Least Significant Bit) tabanlı veri gizleme, çıkarma ve kalite metriklerinin hesaplanması için geliştirilmiş Python projesidir. Komut satırı aracı, toplu analiz betiği ve Streamlit tabanlı web arayüzü birlikte sunulur.

## İçindekiler

- [Genel Bakış](#genel-bakış)
- [Gereksinimler](#gereksinimler)
- [Kurulum](#kurulum)
- [Proje Yapısı](#proje-yapısı)
- [Girdi Görüntü Kuralları](#girdi-görüntü-kuralları)
- [Komut Satırı Kullanımı](#komut-satırı-kullanımı)
- [Web Arayüzü Kullanımı](#web-arayüzü-kullanımı)
- [Çıktı Dosyaları](#çıktı-dosyaları)
- [Metrik Tanımları](#metrik-tanımları)
- [Modüler Fonksiyonlar](#modüler-fonksiyonlar)
- [Sorun Giderme](#sorun-giderme)

## Genel Bakış

Proje aşağıdaki işlemleri gerçekleştirir:

1. Kapak görüntüsüne rastgele bit verisi gizler (B, G, R kanallarının tamamında LSB).
2. Gizlenen veriyi doğrulama amaçlı geri çıkarır.
3. Kapak ve stego görüntü arasında altı farklı kalite metriği hesaplar.
4. Sonuçları CSV, PNG grafik ve BMP stego dosyaları olarak kaydeder.

Desteklenen kapasite seviyeleri: **%25**, **%50**, **%75**, **%100**.

Maksimum gizlenebilir bit kapasitesi:

```
kapasite = M x N x 3
```

Burada `M` genişlik, `N` yükseklik ve `3` RGB kanal sayısıdır.

## Gereksinimler

- Python 3.10 veya üzeri
- Windows, macOS veya Linux

Python paketleri (`requirements.txt`):

| Paket | Amaç |
|---|---|
| opencv-python | Görüntü okuma/yazma |
| numpy | Dizi işlemleri ve bit manipülasyonu |
| matplotlib | Metrik grafikleri |
| streamlit | Web arayüzü |
| pandas | Tablo ve CSV işlemleri |

## Kurulum

Depoyu klonlayın veya proje klasörüne gidin:

```powershell
cd C:\steganography-metrics-analyzer
```

Bağımlılıkları kurun:

```powershell
pip install -r requirements.txt
```

İsteğe bağlı olarak sentetik test görüntüleri üretin:

```powershell
python generate_test_images.py
```

Bu komut `test_images/256x256/` ve `test_images/512x512/` altına 5'er adet BMP ve TIFF dosyası oluşturur.

## Proje Yapısı

```
steganography-metrics-analyzer/
├── app.py                    # Streamlit web arayüzü
├── lsb_steganography.py      # Ana analiz motoru (CLI + modüler fonksiyonlar)
├── generate_test_images.py   # Sentetik test görüntüsü üretici
├── run_ui.bat                # Windows arayüz başlatıcı
├── requirements.txt
├── .streamlit/
│   └── config.toml           # Streamlit yapılandırması
├── test_images/              # Opsiyonel test görüntüleri
│   ├── 256x256/
│   └── 512x512/
└── output/                   # Analiz çıktıları
    ├── stego/                # Stego BMP dosyaları
    ├── plots/                # Metrik grafikleri (PNG)
    └── metrics/              # CSV raporları
```

## Girdi Görüntü Kuralları

### Desteklenen formatlar

- BMP
- TIFF / TIF
- PNG (okuma desteklenir; stego çıktısı BMP olarak kaydedilir)

### Renk derinliği

Yalnızca **24bpp renkli** (3 kanallı) görüntüler işlenir. Gri tonlamalı görüntüler otomatik olarak atlanır.

### Boyut kuralları

| Boyut | Davranış |
|---|---|
| 256 x 256 | Doğrudan işlenir |
| 512 x 512 | Doğrudan işlenir |
| Diğer boyutlar | Uyarı verilir ve otomatik olarak 256 x 256 boyutuna yeniden boyutlandırılır |

### Klasör düzeni

Görüntüler iki şekilde sunulabilir:

**Düz klasör** (tüm dosyalar aynı dizinde):

```
standard_test_images/
├── lena.bmp
├── lena_color_256.tif
└── boat.png
```

**Alt klasörlü yapı**:

```
test_images/
├── 256x256/
│   └── test_01.bmp
└── 512x512/
    └── test_01.bmp
```

Aynı dosya adına sahip birden fazla format varsa öncelik sırası: BMP > TIFF > PNG.

## Komut Satırı Kullanımı

### Temel kullanım

Varsayılan girdi klasörü sırasıyla şunlardır:

1. `%USERPROFILE%\OneDrive\Masaüstü\standard_test_images` (varsa)
2. `test_images/` (proje içi)

```powershell
python lsb_steganography.py
```

### Özel girdi klasörü

```powershell
python lsb_steganography.py --input "C:\Users\emrek\OneDrive\Masaüstü\standard_test_images"
```

### İşlem akışı

Komut satırı aracı her renkli görüntü için sırasıyla:

1. Görüntüyü yükler ve boyut kontrolü yapar.
2. Maksimum bit kapasitesini hesaplar.
3. Her kapasite seviyesi (%25, %50, %75, %100) için rastgele bit verisi gizler.
4. Gizlenen veriyi çıkararak doğrular.
5. Altı metriği hesaplar.
6. Stego BMP, CSV ve PNG grafik dosyalarını kaydeder.

### Örnek terminal çıktısı

```
Girdi klasörü: C:\...\standard_test_images
Bulunan görüntü sayısı: 23
[1/92] lena.bmp - %25
...
Tüm işlemler tamamlandı.
```

## Web Arayüzü Kullanımı

### Başlatma

Windows ortamında `streamlit` komutu PATH'te olmayabilir. Bu nedenle aşağıdaki yöntemlerden biri kullanılmalıdır.

**Yöntem 1 -- Python modülü (önerilen):**

```powershell
cd C:\steganography-metrics-analyzer
python -m streamlit run app.py
```

**Yöntem 2 -- Batch dosyası:**

Proje klasöründeki `run_ui.bat` dosyasına çift tıklayın.

Tarayıcıda varsayılan adres: `http://localhost:8501`

İlk çalıştırmada e-posta isteği görünürse alanı boş bırakıp Enter tuşuna basabilirsiniz.

### Sekme: Tek Görüntü

Bu sekme tek bir kapak görüntüsü üzerinde interaktif analiz sağlar.

| Alan | Açıklama |
|---|---|
| Dosya yükleme | BMP, TIFF veya PNG formatında kapak görüntüsü seçin |
| Gizleme kapasitesi | %25, %50, %75 veya %100 |
| Rastgele tohum | Tekrarlanabilir bit üretimi için sayısal tohum |
| Gizle ve Analiz Et | Gizleme, çıkarma doğrulaması ve metrik hesaplama |

Sonuç ekranında:

- Metrik tablosu (MSE, PSNR, AD, SC, NCC, NAE)
- Kapak ve stego görüntü önizlemesi (yan yana)
- Çıkarma doğrulama durumu
- Stego BMP indirme bağlantısı

### Sekme: Toplu Analiz

Bu sekme bir klasördeki tüm uygun görüntülerde toplu analiz yapar.

| Alan | Açıklama |
|---|---|
| Görüntü klasörü | Analiz edilecek dizinin tam yolu |
| Toplu Analizi Başlat | Tüm görüntülerde 4 kapasite seviyesinde analiz |

Sonuç ekranında:

- Detaylı metrik tablosu (tüm görüntü ve kapasite kombinasyonları)
- CSV indirme
- Ortalama metrik grafikleri (256x256 ve 512x512 ayrımı)
- `output/plots/` altına kaydedilen PNG grafiklerinin önizlemesi

## Çıktı Dosyaları

### Stego görüntüler

Konum: `output/stego/`

Adlandırma formatı:

```
stego_{kapasite}_{genislik}x{yukseklik}_{dosya_adi}.bmp
```

Örnek:

```
stego_50_512x512_lena.bmp
```

Stego dosyaları kayıpsız BMP formatında kaydedilir.

### Metrik CSV dosyaları

Konum: `output/metrics/`

**metrics_detailed.csv** -- Görüntü bazlı detay:

| Sütun | Açıklama |
|---|---|
| image_name | Kaynak dosya adı |
| width, height | Görüntü boyutu |
| capacity_pct | Kapasite yüzdesi |
| bit_count | Gizlenen bit sayısı |
| MSE, PSNR, AD, SC, NCC, NAE | Metrik değerleri |

**metrics_averages.csv** -- Boyut grubu ortalamaları:

| Sütun | Açıklama |
|---|---|
| size | 256x256 veya 512x512 |
| capacity_pct | Kapasite yüzdesi |
| MSE, PSNR, AD, SC, NCC, NAE | Ortalama metrik değerleri |

### Grafik dosyaları

Konum: `output/plots/`

| Dosya | Metrik |
|---|---|
| mse_vs_capacity.png | Ortalama Karesel Hata |
| psnr_vs_capacity.png | Tepe Sinyal Gürültü Oranı |
| ad_vs_capacity.png | Ortalama Fark |
| sc_vs_capacity.png | Yapısal İçerik |
| ncc_vs_capacity.png | Normalize Karşıt Korelasyon |
| nae_vs_capacity.png | Normalize Mutlak Hata |

Grafiklerde x ekseni kapasite yüzdelerini (%25-%100), y ekseni ilgili metrik değerini gösterir. 256x256 ve 512x512 grupları ayrı eğriler olarak çizilir.

## Metrik Tanımları

Tüm metrikler kapak görüntüsü `I` ve stego görüntüsü `K` arasında hesaplanır.

| Metrik | Formül | Yorum |
|---|---|---|
| MSE | mean((I - K)^2) | Düşük değer daha iyi |
| PSNR | 10 * log10(255^2 / MSE) | Yüksek değer (dB) daha iyi |
| AD | mean(\|I - K\|) | Düşük değer daha iyi |
| SC | sum(I^2) / sum(K^2) | 1'e yakın değer daha iyi |
| NCC | sum(I*K) / sqrt(sum(I^2) * sum(K^2)) | 1'e yakın değer daha iyi |
| NAE | sum(\|I - K\|) / sum(\|I\|) | Düşük değer daha iyi |

## Modüler Fonksiyonlar

`lsb_steganography.py` içinde tanımlı temel fonksiyonlar:

| Fonksiyon | Görev |
|---|---|
| `generate_random_data(capacity)` | Belirtilen uzunlukta 0/1 rastgele bit dizisi üretir |
| `hide_data(cover_image, secret_bits)` | LSB tabanlı gizleme uygular |
| `extract_data(stego_image, data_length)` | Belirtilen uzunlukta LSB verisini çıkarır |
| `calculate_metrics(cover, stego)` | Altı metriği dictionary olarak döndürür |
| `run_batch_analysis(test_root, output_root)` | Toplu analiz pipeline'ını çalıştırır |

Bu fonksiyonlar hem komut satırı aracı hem de `app.py` tarafından kullanılır.

## Sorun Giderme

### `streamlit` komutu tanınmıyor

Windows'ta pip script dizini PATH'e ekli olmayabilir. Aşağıdaki komutu kullanın:

```powershell
python -m streamlit run app.py
```

Alternatif olarak `run_ui.bat` dosyasını çalıştırın.

### Görüntü okunamıyor

- Dosyanın bozuk olmadığından emin olun.
- Gri tonlamalı dosyalar desteklenmez; renkli (24bpp) sürümünü kullanın.
- Türkçe karakter içeren dosya yollarında sorun yaşarsanız görüntüleri ASCII karakterli bir yola taşıyın.

### Test görüntüsü bulunamadı

Komut satırı aracı şu hatayı verebilir:

```
Renkli test görüntüsü bulunamadı
```

Çözüm:

1. Görüntüleri desteklenen bir klasöre yerleştirin.
2. `--input` parametresi ile klasör yolunu açıkça belirtin.
3. Veya `python generate_test_images.py` ile sentetik görüntüler oluşturun.

### Port zaten kullanımda

Streamlit varsayılan olarak 8501 portunu kullanır. Meşgulse farklı port belirtin:

```powershell
python -m streamlit run app.py --server.port 8502
```

### OneDrive senkronizasyonu

OneDrive'da "yalnızca çevrimiçi" olarak işaretlenmiş dosyalar okunamayabilir. Görüntülerin yerel kopyasının indirildiğinden emin olun.

## Lisans

Bu proje eğitim ve araştırma amaçlı geliştirilmiştir.
