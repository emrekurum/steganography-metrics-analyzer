"""
Sentetik test görüntüsü üretici.

Projede hazır veri seti yoksa, analiz betiğini denemek için
5 adet 256x256 ve 5 adet 512x512 renkli görüntü oluşturur.
Her görüntü BMP ve TIFF formatında kaydedilir.
"""

from pathlib import Path

import cv2
import numpy as np

# Üretilecek boyutlar (genişlik, yükseklik)
SIZES = [(256, 256), (512, 512)]

# Her boyut için üretilecek görüntü adedi
COUNT_PER_SIZE = 5

# Kayıt formatları
FORMATS = (".bmp", ".tiff")


def create_pattern(width: int, height: int, index: int) -> np.ndarray:
    """
    Test amaçlı renkli gradyan deseni üretir.

    index parametresi her görüntüye farklı renk kayması vererek
    birbirinden ayırt edilebilir desenler oluşturur.

    Dönüş:
        BGR formatında 24bpp numpy dizisi
    """
    x = np.linspace(0, 255, width, dtype=np.float32)
    y = np.linspace(0, 255, height, dtype=np.float32)
    xv, yv = np.meshgrid(x, y)

    # Her kanal için farklı gradyan formülü
    r = ((xv + index * 30) % 256).astype(np.uint8)
    g = ((yv + index * 45) % 256).astype(np.uint8)
    b = (((xv + yv) / 2 + index * 60) % 256).astype(np.uint8)

    return cv2.merge([b, g, r])


def main() -> None:
    """test_images/256x256 ve test_images/512x512 altına dosyaları yazar."""
    base_dir = Path(__file__).resolve().parent / "test_images"

    for width, height in SIZES:
        size_dir = base_dir / f"{width}x{height}"
        size_dir.mkdir(parents=True, exist_ok=True)

        for index in range(1, COUNT_PER_SIZE + 1):
            image = create_pattern(width, height, index)
            stem = f"test_{index:02d}"

            for extension in FORMATS:
                output_path = size_dir / f"{stem}{extension}"
                cv2.imwrite(str(output_path), image)
                print(f"Oluşturuldu: {output_path}")


if __name__ == "__main__":
    main()
