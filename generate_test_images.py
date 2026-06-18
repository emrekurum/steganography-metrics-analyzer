"""Standart test görüntülerini (5x256x256, 5x512x512) TIFF ve BMP olarak üretir."""

from pathlib import Path

import cv2
import numpy as np

SIZES = [(256, 256), (512, 512)]
COUNT_PER_SIZE = 5
FORMATS = (".bmp", ".tiff")


def create_pattern(width: int, height: int, index: int) -> np.ndarray:
    x = np.linspace(0, 255, width, dtype=np.float32)
    y = np.linspace(0, 255, height, dtype=np.float32)
    xv, yv = np.meshgrid(x, y)

    r = ((xv + index * 30) % 256).astype(np.uint8)
    g = ((yv + index * 45) % 256).astype(np.uint8)
    b = (((xv + yv) / 2 + index * 60) % 256).astype(np.uint8)

    return cv2.merge([b, g, r])


def main() -> None:
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
