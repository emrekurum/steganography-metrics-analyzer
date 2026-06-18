"""
Streamlit web arayüzü.

lsb_steganography.py içindeki fonksiyonları kullanarak:
- Tek görüntü analizi
- Klasör bazlı toplu analiz
sunar.
"""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

import cv2
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st

from lsb_steganography import (
    CAPACITY_LEVELS,
    calculate_metrics,
    decode_image_bgr,
    discover_test_images,
    encode_image_bgr_bytes,
    extract_data,
    generate_random_data,
    hide_data,
    max_bit_capacity,
    prepare_cover_from_array,
    run_batch_analysis,
)

PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_INPUT = Path.home() / "OneDrive" / "Masaüstü" / "standard_test_images"
OUTPUT_ROOT = PROJECT_ROOT / "output"


def bgr_to_rgb(image: np.ndarray) -> np.ndarray:
    """OpenCV BGR formatını ekranda göstermek için RGB'ye çevirir."""
    return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)


def format_metric_value(name: str, value: float) -> str:
    """Metrik değerini tabloda okunabilir metne dönüştürür."""
    if name == "PSNR" and value == float("inf"):
        return "∞"
    if name == "PSNR":
        return f"{value:.2f} dB"
    return f"{value:.6f}"


def render_metrics_table(metrics: dict[str, float]) -> None:
    """Hesaplanan metrikleri Streamlit tablosu olarak gösterir."""
    rows = [
        {"Metrik": name, "Değer": format_metric_value(name, value)}
        for name, value in metrics.items()
    ]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def render_capacity_chart(
    aggregated: dict[str, dict[int, dict[str, float]]],
    metric_name: str,
) -> None:
    """
    Seçilen metrik için kapasiteye karşı çizgi grafiği çizer.

    256x256 ve 512x512 grupları ayrı eğriler olarak gösterilir.
    """
    fig, ax = plt.subplots(figsize=(7, 4))

    for size_label, capacity_metrics in aggregated.items():
        values = [capacity_metrics[capacity][metric_name] for capacity in CAPACITY_LEVELS]
        ax.plot(CAPACITY_LEVELS, values, marker="o", linewidth=2, label=size_label)

    ax.set_title(f"{metric_name} vs. Gizleme Kapasitesi")
    ax.set_xlabel("Kapasite (%)")
    ax.set_ylabel(metric_name)
    ax.set_xticks(CAPACITY_LEVELS)
    ax.grid(True, linestyle="--", alpha=0.5)
    ax.legend()
    fig.tight_layout()
    st.pyplot(fig)
    plt.close(fig)


def single_image_tab() -> None:
    """
    Tek görüntü sekmesi.

    Kullanıcı bir kapak görüntüsü yükler, kapasite seçer ve
    gizleme + metrik analizi sonuçlarını anında görür.
    """
    st.subheader("Tek Görüntü Analizi")

    uploaded = st.file_uploader(
        "Kapak görüntüsü yükleyin (BMP / TIFF / PNG)",
        type=["bmp", "tif", "tiff", "png"],
    )

    col1, col2 = st.columns(2)
    with col1:
        capacity_pct = st.selectbox("Gizleme kapasitesi (%)", CAPACITY_LEVELS, index=1)
    with col2:
        seed = st.number_input("Rastgele tohum", min_value=0, value=42, step=1)

    if uploaded is None:
        st.info("Başlamak için bir renkli görüntü yükleyin.")
        return

    try:
        raw_image = decode_image_bgr(uploaded.getvalue())
        cover, (width, height), resize_note = prepare_cover_from_array(raw_image)
    except ValueError as exc:
        st.error(str(exc))
        return
    except FileNotFoundError:
        st.error("Görüntü okunamadı.")
        return

    total_capacity = max_bit_capacity(cover)
    bit_count = int(total_capacity * capacity_pct / 100)

    st.caption(
        f"Boyut: {width}x{height} | Maksimum kapasite: {total_capacity:,} bit | "
        f"Gizlenecek: {bit_count:,} bit (%{capacity_pct})"
    )
    if resize_note:
        st.warning(resize_note)

    if st.button("Gizle ve Analiz Et", type="primary"):
        # Seçilen kapasite kadar rastgele bit üret ve gizle
        secret_bits = generate_random_data(total_capacity, rng=np.random.default_rng(int(seed)))
        secret_bits = secret_bits[:bit_count]

        stego = hide_data(cover, secret_bits)
        extracted = extract_data(stego, bit_count)
        metrics = calculate_metrics(cover, stego)
        verified = bool(np.array_equal(secret_bits, extracted))

        # Sonuçları oturum hafızasında sakla (sayfa yenilense bile görüntülenebilsin)
        st.session_state["single_result"] = {
            "cover": cover,
            "stego": stego,
            "metrics": metrics,
            "verified": verified,
            "capacity_pct": capacity_pct,
            "bit_count": bit_count,
            "filename": Path(uploaded.name).stem,
            "size_label": f"{width}x{height}",
        }

    result = st.session_state.get("single_result")
    if not result:
        st.image(bgr_to_rgb(cover), caption="Kapak Görüntü", use_container_width=True)
        return

    status_col, metric_col = st.columns([1, 1])
    with status_col:
        if result["verified"]:
            st.success("Çıkarma doğrulaması başarılı.")
        else:
            st.error("Çıkarma doğrulaması başarısız.")

    with metric_col:
        st.metric("Gizlenen bit", f"{result['bit_count']:,}")

    render_metrics_table(result["metrics"])

    image_col1, image_col2 = st.columns(2)
    with image_col1:
        st.image(bgr_to_rgb(result["cover"]), caption="Kapak", use_container_width=True)
    with image_col2:
        st.image(bgr_to_rgb(result["stego"]), caption="Stego", use_container_width=True)

    stego_bytes = encode_image_bgr_bytes(result["stego"])
    st.download_button(
        "Stego BMP indir",
        data=stego_bytes,
        file_name=(
            f"stego_{result['capacity_pct']}_{result['size_label']}_{result['filename']}.bmp"
        ),
        mime="image/bmp",
    )


def batch_analysis_tab() -> None:
    """
    Toplu analiz sekmesi.

    Belirtilen klasördeki tüm uygun görüntülerde analiz çalıştırır,
    tablo/grafik/CSV sonuçlarını gösterir.
    """
    st.subheader("Toplu Analiz")

    default_path = str(DEFAULT_INPUT if DEFAULT_INPUT.exists() else PROJECT_ROOT / "test_images")
    folder_input = st.text_input("Görüntü klasörü", value=default_path)

    folder_path = Path(folder_input).expanduser()
    if folder_path.exists():
        image_count = len(discover_test_images(folder_path))
        st.caption(f"Bulunan renkli görüntü sayısı: {image_count}")
    else:
        st.warning("Klasör bulunamadı.")

    if st.button("Toplu Analizi Başlat", type="primary", disabled=not folder_path.exists()):
        progress = st.progress(0.0)
        status = st.empty()

        def update_progress(step: int, total: int, image_name: str, capacity_pct: int) -> None:
            progress.progress(step / total)
            status.info(f"{image_name} — %{capacity_pct} ({step}/{total})")

        try:
            detailed_rows, aggregated = run_batch_analysis(
                folder_path,
                OUTPUT_ROOT,
                progress_callback=update_progress,
            )
        except FileNotFoundError as exc:
            st.error(str(exc))
            return
        except RuntimeError as exc:
            st.error(str(exc))
            return

        progress.progress(1.0)
        status.success("Toplu analiz tamamlandı.")

        st.session_state["batch_detailed"] = detailed_rows
        st.session_state["batch_aggregated"] = aggregated

    detailed_rows = st.session_state.get("batch_detailed")
    aggregated = st.session_state.get("batch_aggregated")

    if not detailed_rows or not aggregated:
        st.info("Sonuçları görmek için toplu analizi çalıştırın.")
        return

    st.dataframe(pd.DataFrame(detailed_rows), use_container_width=True, hide_index=True)

    csv_buffer = BytesIO()
    pd.DataFrame(detailed_rows).to_csv(csv_buffer, index=False, encoding="utf-8")
    st.download_button(
        "Detay CSV indir",
        data=csv_buffer.getvalue(),
        file_name="metrics_detailed.csv",
        mime="text/csv",
    )

    st.markdown("### Ortalama Metrik Grafikleri")
    metric_tabs = st.tabs(["MSE", "PSNR", "AD", "SC", "NCC", "NAE"])
    for tab, metric_name in zip(metric_tabs, ("MSE", "PSNR", "AD", "SC", "NCC", "NAE")):
        with tab:
            render_capacity_chart(aggregated, metric_name)

    plot_dir = OUTPUT_ROOT / "plots"
    if plot_dir.exists():
        st.markdown("### Kaydedilen Grafikler")
        plot_cols = st.columns(3)
        plot_files = sorted(plot_dir.glob("*_vs_capacity.png"))
        for index, plot_path in enumerate(plot_files):
            with plot_cols[index % 3]:
                st.image(str(plot_path), caption=plot_path.stem, use_container_width=True)


def main() -> None:
    """Arayüz düzenini oluşturur ve sekmeleri başlatır."""
    st.set_page_config(
        page_title="LSB Steganografi Analizörü",
        page_icon=":frame_with_picture:",
        layout="wide",
    )

    st.title("LSB Steganografi Metrik Analizörü")
    st.caption("24bpp RGB görüntülerde LSB tabanlı gizleme, çıkarma ve kalite metrikleri")

    tab_single, tab_batch = st.tabs(["Tek Görüntü", "Toplu Analiz"])
    with tab_single:
        single_image_tab()
    with tab_batch:
        batch_analysis_tab()


if __name__ == "__main__":
    main()
