from pathlib import Path
from typing import List
import base64

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st
import re

from blastwave.compute import compute_scenario_waves, extract_wave, get_peak_abs
from blastwave.io import DEFAULT_SPS, get_default_dir, load_delay_scenarios, load_distance_data
from blastwave.io import load_signature_wave, load_weights, validate_scenario_alignment
from blastwave.models import InputParams


def main() -> None:
    assets_dir = Path(__file__).parent / "assets"
    icon_path = assets_dir / "sound__3__zx3_icon.ico"
    logo_path = assets_dir / "itb.png"

    st.set_page_config(page_title="Blast Wave PPV Optimizer", layout="wide", page_icon=str(icon_path))
    st.markdown(
        """
        <style>
        [data-testid="stAppViewContainer"] > .main { padding-top: 50px !important; }
        .block-container { padding-top: 0; padding-bottom: 2rem; }
        [data-testid="stNumberInput"] button { display: none; }
        .bw-title { font-size: 3.12rem; font-weight: 700; margin: 0.2rem 0 0.6rem; text-align: center; }
        .bw-header { display: flex; align-items: center; justify-content: space-between; gap: 1rem; }
        .bw-header-title { flex: 1; text-align: center; }
        .bw-content { margin-top: 40px; }
        .bw-subtitle { font-size: 1.1rem; font-weight: 600; margin: 0.4rem 0; }
        .bw-label { font-size: 0.95rem; font-weight: 600; margin: 0.2rem 0; }
        .bw-muted { color: #666; font-size: 0.9rem; }
        .bw-plot-title { font-size: 0.95rem; font-weight: 600; margin: 0.6rem 0 0.2rem; }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.markdown('<div style="height:50px;"></div>', unsafe_allow_html=True)
    left_logo = _encode_image_base64(icon_path)
    right_logo = _encode_image_base64(logo_path)
    st.markdown(
        (
            '<div class="bw-header">'
            f'<img src="{left_logo}" width="80" />'
            '<div class="bw-header-title"><div class="bw-title">Blast Wave PPV Optimizer</div></div>'
            f'<img src="{right_logo}" width="96" />'
            "</div>"
        ),
        unsafe_allow_html=True,
    )

    st.markdown('<div class="bw-content">', unsafe_allow_html=True)
    default_dir = get_default_dir()
    metadata = read_input_metadata(default_dir)
    st.markdown(
        (
            f'<div class="bw-muted">Input folder: {default_dir}</div>'
            f'<div class="bw-muted">Signature files: {metadata["signature_count"]} | '
            f'Delay files: {metadata["delay_count"]} | Sample rate: {metadata["sampling_rate"]} sps</div>'
            '<div class="bw-muted">'
            'Created by: <a href="https://www.linkedin.com/in/harristio-adam/" target="_blank">Harristio Adam</a> | '
            'Supervised by: <a href="https://itb.ac.id/staf/profil/ganda-marihot-simangunsong" target="_blank">'
            'Prof. Dr.Eng. Ir. Ganda Marihot Simangunsong, S.T., M.T.</a> | '
            'Github repo: <a href="https://github.com/harris61/blastwave-python" target="_blank">'
            'github.com/harris61/blastwave-python</a>'
            "</div>"
        ),
        unsafe_allow_html=True,
    )

    inputs = render_inputs(metadata)

    if inputs["calculate"]:
        with st.spinner("Calculating..."):
            try:
                signature, result = run_calculation(inputs["params"], default_dir)
            except Exception as exc:
                st.error(f"Gagal menghitung PPV. {exc}")
                return
        render_results(signature, result, inputs["params"])
    st.markdown("</div>", unsafe_allow_html=True)


def render_inputs(metadata):
    row = st.columns([2, 2, 2, 1.2])
    with row[0]:
        st.markdown('<div class="bw-label">Konstanta Lapangan</div>', unsafe_allow_html=True)
        field_constant = st.number_input(
            "Konstanta Lapangan",
            min_value=0.0,
            step=0.1,
            format="%g",
            key="field_constant",
            label_visibility="collapsed",
        )
    with row[1]:
        st.markdown('<div class="bw-label">Muatan Signature Hole (kg)</div>', unsafe_allow_html=True)
        signature_weight = st.number_input(
            "Muatan Signature Hole (kg)",
            min_value=0.0,
            step=0.1,
            format="%g",
            key="sig_weight",
            label_visibility="collapsed",
        )
    with row[2]:
        st.markdown('<div class="bw-label">Lama Pengukuran (ms)</div>', unsafe_allow_html=True)
        measurement_ms = st.number_input(
            "Lama Pengukuran (ms)",
            min_value=0,
            step=1,
            format="%d",
            key="measurement_ms",
            label_visibility="collapsed",
        )
    with row[3]:
        st.markdown('<div class="bw-label">&nbsp;</div>', unsafe_allow_html=True)
        calculate = st.button("Calculate", use_container_width=True)

    params = InputParams(
        signature_file_count=metadata["signature_count"],
        delay_file_count=metadata["delay_count"],
        sampling_rate=metadata["sampling_rate"],
        measurement_ms=int(measurement_ms),
        field_constant=float(field_constant),
        signature_weight=float(signature_weight),
    )
    return {"params": params, "calculate": calculate}


def run_calculation(inputs: InputParams, default_dir: Path):
    if not default_dir.exists():
        raise ValueError(f"Folder not found: {default_dir}")

    if inputs.sampling_rate % DEFAULT_SPS != 0:
        raise ValueError(f"Sampling rate harus habis dibagi {DEFAULT_SPS}.")
    if inputs.field_constant <= 0:
        raise ValueError("Konstanta Lapangan harus angka > 0.")
    if inputs.signature_weight <= 0:
        raise ValueError("Muatan Signature Hole harus angka > 0.")

    ratio_sps = inputs.sampling_rate // DEFAULT_SPS

    signature = load_signature_wave(
        default_dir,
        inputs.signature_file_count,
        inputs.measurement_ms,
        ratio_sps,
    )
    delays = load_delay_scenarios(default_dir, inputs.delay_file_count, ratio_sps)
    weights = load_weights(default_dir, inputs.delay_file_count)
    distances = load_distance_data(default_dir, inputs.delay_file_count)
    validate_scenario_alignment(delays, weights, distances)

    result = compute_scenario_waves(
        signature,
        delays,
        weights,
        distances,
        inputs.field_constant,
        inputs.signature_weight,
    )
    return signature, result


def read_input_metadata(default_dir: Path) -> dict:
    signature_dir = default_dir / "Signature Wave"
    delay_dir = default_dir / "Delay Scenario"
    signature_count = _count_numeric_files(signature_dir)
    delay_count = _count_numeric_files(delay_dir)
    sampling_rate = _read_sample_rate(signature_dir)
    return {
        "signature_count": signature_count,
        "delay_count": delay_count,
        "sampling_rate": sampling_rate,
    }


def _count_numeric_files(dir_path: Path) -> int:
    if not dir_path.exists():
        return 0
    count = 0
    for path in dir_path.iterdir():
        if path.is_file() and path.suffix.lower() == ".txt":
            try:
                value = int(path.stem)
            except ValueError:
                continue
            if value >= 1:
                count += 1
    return count


def _read_sample_rate(signature_dir: Path) -> int:
    candidates = []
    if signature_dir.exists():
        for path in signature_dir.iterdir():
            if path.is_file() and path.suffix.lower() == ".txt":
                try:
                    value = int(path.stem)
                except ValueError:
                    continue
                if value >= 1:
                    candidates.append((value, path))
    if not candidates:
        return 0
    _, first_file = sorted(candidates, key=lambda item: item[0])[0]
    for line in first_file.read_text().splitlines()[:200]:
        cleaned = line.strip().strip('"')
        if cleaned.lower().startswith("sample rate"):
            match = re.search(r"(\d+)", cleaned)
            if match:
                return int(match.group(1))
    return 0


def _encode_image_base64(path: Path) -> str:
    data = path.read_bytes()
    encoded = base64.b64encode(data).decode("ascii")
    if path.suffix.lower() == ".png":
        mime = "image/png"
    elif path.suffix.lower() in {".jpg", ".jpeg"}:
        mime = "image/jpeg"
    else:
        mime = "image/x-icon"
    return f"data:{mime};base64,{encoded}"


def render_results(signature, result, inputs: InputParams) -> None:
    signature_ppv_tran = get_peak_abs(signature.tran)
    signature_ppv_vert = get_peak_abs(signature.vert)
    signature_ppv_long = get_peak_abs(signature.long)
    max_x = result.wave_length

    top = st.columns([1, 3, 1])
    with top[1]:
        st.markdown(
            (
                f'<div class="bw-subtitle" style="text-align:center;">'
                f'Optimized Peak Vector Sum(mm/s, 1/{inputs.sampling_rate} ms)</div>'
            ),
            unsafe_allow_html=True,
        )
        st.pyplot(
            plot_series(
                extract_wave(result.pvs, result.opt_pvs_index, result.wave_length),
                f"Skenario {result.opt_pvs_index + 1} Peak Vector Sum PPV = {result.opt_pvs_ppv} mm/s",
                "green",
                max_x,
                figsize=(4.2, 1.8),
            ),
            use_container_width=True,
        )
        render_ppv_table(result, height=208)

    header = st.columns([3, 3])
    with header[0]:
        st.markdown(
            f'<div class="bw-subtitle">Signature Wave(mm/s, 1/{inputs.sampling_rate} ms)</div>',
            unsafe_allow_html=True,
        )
    with header[1]:
        st.markdown(
            f'<div class="bw-subtitle">Optimized Full Blast Wave(mm/s, 1/{inputs.sampling_rate} ms)</div>',
            unsafe_allow_html=True,
        )

    rows = [
        (
            f"Signature Transversal Wave PPV = {signature_ppv_tran} mm/s",
            signature.tran,
            "turquoise",
            (
                f"Skenario {result.opt_tran_index + 1} Full Blast Transversal Wave PPV = "
                f"{result.opt_tran_ppv} mm/s"
            ),
            extract_wave(result.tran, result.opt_tran_index, result.wave_length),
            "turquoise",
        ),
        (
            f"Signature Vertical Wave PPV = {signature_ppv_vert} mm/s",
            signature.vert,
            "blue",
            (
                f"Skenario {result.opt_vert_index + 1} Full Blast Vertical Wave PPV = "
                f"{result.opt_vert_ppv} mm/s"
            ),
            extract_wave(result.vert, result.opt_vert_index, result.wave_length),
            "blue",
        ),
        (
            f"Signature Longitudinal Wave PPV = {signature_ppv_long} mm/s",
            signature.long,
            "purple",
            (
                f"Skenario {result.opt_long_index + 1} Full Blast Longitudinal Wave PPV = "
                f"{result.opt_long_ppv} mm/s"
            ),
            extract_wave(result.long, result.opt_long_index, result.wave_length),
            "purple",
        ),
    ]

    for left_title, left_data, left_color, right_title, right_data, right_color in rows:
        row = st.columns([3, 3])
        with row[0]:
            st.markdown(f'<div class="bw-plot-title">{left_title}</div>', unsafe_allow_html=True)
            st.pyplot(
                plot_series(left_data, "", left_color, max_x, figsize=(4.2, 1.8)),
                use_container_width=True,
            )
        with row[1]:
            st.markdown(f'<div class="bw-plot-title">{right_title}</div>', unsafe_allow_html=True)
            st.pyplot(
                plot_series(right_data, "", right_color, max_x, figsize=(4.2, 1.8)),
                use_container_width=True,
            )


def render_ppv_table(result, height: int = 260) -> None:
    scenario_count = len(result.ppv[0])
    rows: List[dict] = []
    for index in range(scenario_count):
        rows.append(
            {
                "Skenario Delay": index + 1,
                "PPV Tran (mm/s)": result.ppv[0][index],
                "PPV Vert (mm/s)": result.ppv[1][index],
                "PPV Long (mm/s)": result.ppv[2][index],
                "PPV PVS (mm/s)": result.ppv[3][index],
            }
        )

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, height=height)


def plot_series(data: List[float], title: str, color: str, max_x: int, figsize=(5.2, 2.2)):
    fig, ax = plt.subplots(figsize=figsize)
    ax.plot(range(len(data)), data, color=color)
    ax.set_xlim(0, max_x)
    ax.set_title(title, fontsize=10)
    ax.set_xlabel("Sample")
    ax.set_ylabel("mm/s")
    ax.grid(True, linestyle="-", color="#666", alpha=0.6)
    fig.subplots_adjust(left=0.1, right=0.98, top=0.82, bottom=0.2)
    return fig


if __name__ == "__main__":
    main()
