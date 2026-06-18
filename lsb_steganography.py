"""LSB tabanlı steganografi: gizleme, çıkarma, metrik hesaplama ve grafik üretimi."""

from __future__ import annotations

import argparse
import csv
import warnings
from pathlib import Path
from typing import Dict, List, Tuple

import cv2
import matplotlib.pyplot as plt
import numpy as np

CAPACITY_LEVELS = (25, 50, 75, 100)
EXPECTED_SIZES = {(256, 256), (512, 512)}
SUPPORTED_EXTENSIONS = {".bmp", ".tiff", ".tif", ".png"}


def generate_random_data(capacity: int, rng: np.random.Generator | None = None) -> np.ndarray:
    """Belirtilen kapasite kadar 0/1 rastgele bit dizisi üretir."""
    if capacity <= 0:
        return np.array([], dtype=np.uint8)

    generator = rng or np.random.default_rng()
    return generator.integers(0, 2, size=capacity, dtype=np.uint8)


def hide_data(cover_image: np.ndarray, secret_bits: np.ndarray) -> np.ndarray:
    """24bpp RGB görüntünün tüm kanallarında LSB gizleme uygular."""
    if cover_image.ndim != 3 or cover_image.shape[2] != 3:
        raise ValueError("Görüntü 24bpp (H x W x 3) olmalıdır.")

    max_capacity = cover_image.shape[0] * cover_image.shape[1] * 3
    if secret_bits.size > max_capacity:
        raise ValueError(
            f"Gizlenecek bit sayısı ({secret_bits.size}) kapasiteyi ({max_capacity}) aşıyor."
        )

    stego = cover_image.copy()
    flat = stego.reshape(-1)

    mask = np.uint8(0xFE)
    flat[: secret_bits.size] = (flat[: secret_bits.size] & mask) | secret_bits.astype(np.uint8)

    return stego.reshape(cover_image.shape)


def extract_data(stego_image: np.ndarray, data_length: int) -> np.ndarray:
    """Stego görüntüden belirtilen uzunlukta LSB verisini çıkarır."""
    if stego_image.ndim != 3 or stego_image.shape[2] != 3:
        raise ValueError("Görüntü 24bpp (H x W x 3) olmalıdır.")

    max_capacity = stego_image.shape[0] * stego_image.shape[1] * 3
    if data_length > max_capacity:
        raise ValueError(
            f"İstenen uzunluk ({data_length}) kapasiteyi ({max_capacity}) aşıyor."
        )

    flat = stego_image.reshape(-1)
    return (flat[:data_length] & 1).astype(np.uint8)


def calculate_metrics(cover: np.ndarray, stego: np.ndarray) -> Dict[str, float]:
    """Kapak ve stego görüntü arasında steganografi metriklerini hesaplar."""
    cover_f = cover.astype(np.float64)
    stego_f = stego.astype(np.float64)
    diff = cover_f - stego_f

    mse = float(np.mean(diff ** 2))
    if mse == 0.0:
        psnr = float("inf")
    else:
        psnr = float(10.0 * np.log10((255.0 ** 2) / mse))

    ad = float(np.mean(np.abs(diff)))

    cover_sq_sum = float(np.sum(cover_f ** 2))
    stego_sq_sum = float(np.sum(stego_f ** 2))
    sc = float(cover_sq_sum / stego_sq_sum) if stego_sq_sum != 0.0 else float("inf")

    numerator = float(np.sum(cover_f * stego_f))
    denominator = float(np.sqrt(cover_sq_sum * stego_sq_sum))
    ncc = float(numerator / denominator) if denominator != 0.0 else 0.0

    cover_abs_sum = float(np.sum(np.abs(cover_f)))
    nae = float(np.sum(np.abs(diff)) / cover_abs_sum) if cover_abs_sum != 0.0 else 0.0

    return {
        "MSE": mse,
        "PSNR": psnr,
        "AD": ad,
        "SC": sc,
        "NCC": ncc,
        "NAE": nae,
    }


def read_image_bgr(image_path: Path) -> np.ndarray | None:
    """Unicode yollar dahil görüntüyü BGR 24bpp olarak okur."""
    file_bytes = np.fromfile(str(image_path), dtype=np.uint8)
    image = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
    return image


def write_image_bgr(image_path: Path, image: np.ndarray) -> None:
    """Unicode yollar dahil görüntüyü kayıpsız BMP olarak yazar."""
    success, encoded = cv2.imencode(".bmp", image)
    if not success:
        raise RuntimeError(f"Görüntü kodlanamadı: {image_path}")
    encoded.tofile(str(image_path))


def prepare_cover_from_array(image: np.ndarray) -> Tuple[np.ndarray, Tuple[int, int], str | None]:
    """NumPy dizisinden kapak görüntüsü hazırlar; gerekirse 256x256'ya yeniden boyutlandırır."""
    if image is None:
        raise FileNotFoundError("Görüntü okunamadı.")
    if image.ndim != 3 or image.shape[2] != 3:
        raise ValueError("Görüntü 24bpp renkli (H x W x 3) olmalıdır.")

    height, width = image.shape[:2]
    current_size = (width, height)
    resize_note = None

    if current_size not in EXPECTED_SIZES:
        resize_note = f"Boyut {width}x{height}; otomatik olarak 256x256'ya yeniden boyutlandırıldı."
        image = cv2.resize(image, (256, 256), interpolation=cv2.INTER_AREA)
        current_size = (256, 256)

    return image, current_size, resize_note


def encode_image_bgr_bytes(image: np.ndarray) -> bytes:
    """BGR görüntüsünü BMP bayt dizisine dönüştürür."""
    success, encoded = cv2.imencode(".bmp", image)
    if not success:
        raise RuntimeError("Görüntü kodlanamadı.")
    return encoded.tobytes()


def decode_image_bgr(data: bytes) -> np.ndarray | None:
    """Bayt dizisinden BGR görüntü okur."""
    buffer = np.frombuffer(data, dtype=np.uint8)
    return cv2.imdecode(buffer, cv2.IMREAD_COLOR)


def load_cover_image(image_path: Path) -> Tuple[np.ndarray, Tuple[int, int]]:
    """Görüntüyü BGR 24bpp olarak yükler; gerekirse 256x256'ya yeniden boyutlandırır."""
    image = read_image_bgr(image_path)
    if image is None:
        raise FileNotFoundError(f"Görüntü okunamadı: {image_path}")

    cover, current_size, resize_note = prepare_cover_from_array(image)
    if resize_note:
        warnings.warn(f"{image_path.name}: {resize_note}", UserWarning, stacklevel=2)

    return cover, current_size


def max_bit_capacity(image: np.ndarray) -> int:
    """M x N x 3 formülüyle maksimum gizlenebilir bit sayısını döndürür."""
    height, width = image.shape[:2]
    return height * width * 3


def discover_test_images(test_root: Path) -> List[Path]:
    """BMP/TIFF/PNG test görüntülerini bulur (alt klasör veya düz klasör yapısı)."""
    images: List[Path] = []
    seen: set[str] = set()

    search_dirs: List[Path] = []
    for size_label in ("256x256", "512x512"):
        size_dir = test_root / size_label
        if size_dir.exists():
            search_dirs.append(size_dir)

    if not search_dirs:
        search_dirs.append(test_root)

    for search_dir in search_dirs:
        candidates = [
            path
            for path in sorted(search_dir.rglob("*"))
            if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS
        ]
        candidates.sort(
            key=lambda path: (
                path.stem.lower(),
                0 if path.suffix.lower() == ".bmp" else 1 if path.suffix.lower() in {".tif", ".tiff"} else 2,
            )
        )

        for path in candidates:
            if path.stem.lower() in seen:
                continue

            image = read_image_bgr(path)
            if image is None:
                warnings.warn(f"{path.name} okunamadı; atlanıyor.", UserWarning, stacklevel=2)
                continue
            if image.ndim != 3 or image.shape[2] != 3:
                warnings.warn(f"{path.name} gri tonlamalı; 24bpp gerektiği için atlanıyor.", UserWarning, stacklevel=2)
                continue

            seen.add(path.stem.lower())
            images.append(path)

    return images


def save_metric_plots(
    results_by_size: Dict[str, Dict[int, Dict[str, float]]],
    output_dir: Path,
) -> None:
    """Her metrik için kapasiteye karşı ayrı PNG grafik kaydeder."""
    output_dir.mkdir(parents=True, exist_ok=True)
    metric_names = ("MSE", "PSNR", "AD", "SC", "NCC", "NAE")

    for metric in metric_names:
        plt.figure(figsize=(8, 5))

        for size_label, capacity_metrics in results_by_size.items():
            capacities = CAPACITY_LEVELS
            values = [capacity_metrics[capacity][metric] for capacity in capacities]
            plt.plot(capacities, values, marker="o", linewidth=2, label=size_label)

        plt.title(f"{metric} vs. Gizleme Kapasitesi")
        plt.xlabel("Kapasite (%)")
        plt.ylabel(metric)
        plt.xticks(CAPACITY_LEVELS)
        plt.grid(True, linestyle="--", alpha=0.5)
        plt.legend()
        plt.tight_layout()

        plot_path = output_dir / f"{metric.lower()}_vs_capacity.png"
        plt.savefig(plot_path, dpi=150)
        plt.close()
        print(f"Grafik kaydedildi: {plot_path}")


def save_metrics_csv(
    detailed_rows: List[Dict[str, object]],
    aggregated: Dict[str, Dict[int, Dict[str, float]]],
    output_dir: Path,
) -> None:
    """Görüntü bazlı ve ortalama metrik sonuçlarını CSV olarak kaydeder."""
    output_dir.mkdir(parents=True, exist_ok=True)
    metric_names = ("MSE", "PSNR", "AD", "SC", "NCC", "NAE")

    detailed_path = output_dir / "metrics_detailed.csv"
    with detailed_path.open("w", newline="", encoding="utf-8") as csv_file:
        fieldnames = [
            "image_name",
            "width",
            "height",
            "capacity_pct",
            "bit_count",
            *metric_names,
        ]
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(detailed_rows)
    print(f"CSV kaydedildi: {detailed_path}")

    averages_path = output_dir / "metrics_averages.csv"
    with averages_path.open("w", newline="", encoding="utf-8") as csv_file:
        fieldnames = ["size", "capacity_pct", *metric_names]
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()

        for size_label, capacity_metrics in aggregated.items():
            for capacity_pct in CAPACITY_LEVELS:
                metrics = capacity_metrics.get(capacity_pct)
                if not metrics:
                    continue
                writer.writerow(
                    {
                        "size": size_label,
                        "capacity_pct": capacity_pct,
                        **metrics,
                    }
                )
    print(f"CSV kaydedildi: {averages_path}")


def parse_args() -> argparse.Namespace:
    project_root = Path(__file__).resolve().parent
    default_input = project_root / "test_images"
    desktop_input = Path.home() / "OneDrive" / "Masaüstü" / "standard_test_images"

    parser = argparse.ArgumentParser(description="LSB steganografi ve metrik analizi")
    parser.add_argument(
        "--input",
        type=Path,
        default=desktop_input if desktop_input.exists() else default_input,
        help="Test görüntülerinin bulunduğu klasör",
    )
    return parser.parse_args()


def run_batch_analysis(
    test_root: Path,
    output_root: Path,
    *,
    progress_callback=None,
) -> Tuple[List[Dict[str, object]], Dict[str, Dict[int, Dict[str, float]]]]:
    """Tüm test görüntülerinde LSB analizi yapar ve çıktıları kaydeder."""
    stego_dir = output_root / "stego"
    plot_dir = output_root / "plots"
    metrics_dir = output_root / "metrics"

    stego_dir.mkdir(parents=True, exist_ok=True)

    image_paths = discover_test_images(test_root)
    if not image_paths:
        raise FileNotFoundError(f"Renkli test görüntüsü bulunamadı: {test_root}")

    rng_by_size: Dict[Tuple[int, int], np.random.Generator] = {
        (256, 256): np.random.default_rng(256),
        (512, 512): np.random.default_rng(512),
    }
    full_random_bits: Dict[Tuple[int, int], np.ndarray] = {}

    for size in ((256, 256), (512, 512)):
        capacity = size[0] * size[1] * 3
        full_random_bits[size] = generate_random_data(capacity, rng=rng_by_size[size])

    aggregated: Dict[str, Dict[int, Dict[str, float]]] = {
        "256x256": {capacity: {} for capacity in CAPACITY_LEVELS},
        "512x512": {capacity: {} for capacity in CAPACITY_LEVELS},
    }
    metric_sums: Dict[str, Dict[int, Dict[str, float]]] = {
        "256x256": {capacity: {} for capacity in CAPACITY_LEVELS},
        "512x512": {capacity: {} for capacity in CAPACITY_LEVELS},
    }
    metric_counts: Dict[str, Dict[int, int]] = {
        "256x256": {capacity: 0 for capacity in CAPACITY_LEVELS},
        "512x512": {capacity: 0 for capacity in CAPACITY_LEVELS},
    }
    detailed_rows: List[Dict[str, object]] = []

    total_steps = len(image_paths) * len(CAPACITY_LEVELS)
    step = 0

    for image_path in image_paths:
        try:
            cover, (width, height) = load_cover_image(image_path)
        except ValueError:
            continue

        size_key = (width, height)
        size_label = f"{width}x{height}"

        if size_key not in full_random_bits:
            continue

        total_capacity = max_bit_capacity(cover)
        stem = image_path.stem

        for capacity_pct in CAPACITY_LEVELS:
            bit_count = int(total_capacity * capacity_pct / 100)
            secret_bits = full_random_bits[size_key][:bit_count]

            stego = hide_data(cover, secret_bits)
            extracted = extract_data(stego, bit_count)

            if not np.array_equal(secret_bits, extracted):
                raise RuntimeError(
                    f"{image_path.name} için %{capacity_pct} kapasitede çıkarma doğrulaması başarısız."
                )

            metrics = calculate_metrics(cover, stego)

            for metric_name, value in metrics.items():
                metric_sums[size_label][capacity_pct][metric_name] = (
                    metric_sums[size_label][capacity_pct].get(metric_name, 0.0) + value
                )
            metric_counts[size_label][capacity_pct] += 1

            detailed_rows.append(
                {
                    "image_name": image_path.name,
                    "width": width,
                    "height": height,
                    "capacity_pct": capacity_pct,
                    "bit_count": bit_count,
                    **metrics,
                }
            )

            output_name = f"stego_{capacity_pct}_{width}x{height}_{stem}.bmp"
            write_image_bgr(stego_dir / output_name, stego)

            step += 1
            if progress_callback:
                progress_callback(step, total_steps, image_path.name, capacity_pct)

    for size_label in aggregated:
        for capacity_pct in CAPACITY_LEVELS:
            count = metric_counts[size_label][capacity_pct]
            if count == 0:
                continue
            aggregated[size_label][capacity_pct] = {
                metric: metric_sums[size_label][capacity_pct][metric] / count
                for metric in metric_sums[size_label][capacity_pct]
            }

    save_metric_plots(aggregated, plot_dir)
    save_metrics_csv(detailed_rows, aggregated, metrics_dir)

    return detailed_rows, aggregated


def main() -> None:
    args = parse_args()
    project_root = Path(__file__).resolve().parent
    test_root = args.input.resolve()
    output_root = project_root / "output"

    if not test_root.exists():
        raise FileNotFoundError(f"Girdi klasörü bulunamadı: {test_root}")

    image_paths = discover_test_images(test_root)
    if not image_paths:
        raise FileNotFoundError(f"Renkli test görüntüsü bulunamadı: {test_root}")

    print(f"Girdi klasörü: {test_root}")
    print(f"Bulunan görüntü sayısı: {len(image_paths)}")

    def log_progress(step: int, total: int, image_name: str, capacity_pct: int) -> None:
        print(f"[{step}/{total}] {image_name} - %{capacity_pct}")

    run_batch_analysis(
        test_root,
        output_root,
        progress_callback=log_progress,
    )
    print("\nTüm işlemler tamamlandı.")


if __name__ == "__main__":
    main()
