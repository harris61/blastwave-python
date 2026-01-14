from pathlib import Path
from typing import List

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

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
        .block-container { padding-top: 0; padding-bottom: 2rem; }
        section.main > div { padding-top: 4rem !important; }
        .bw-title { font-size: 2rem; font-weight: 700; margin: 0.2rem 0 0.6rem; }
        .bw-subtitle { font-size: 1.1rem; font-weight: 600; margin: 0.4rem 0; }
        .bw-label { font-size: 0.95rem; font-weight: 600; margin: 0.2rem 0; }
        .bw-muted { color: #666; font-size: 0.9rem; }
        </style>
        """,
        unsafe_allow_html=True,
    )
    header = st.columns([0.6, 4, 1.2])
    with header[0]:
        st.image(str(icon_path), width=48)
    with header[1]:
        st.markdown('<div class="bw-title">Blast Wave PPV Optimizer</div>', unsafe_allow_html=True)
    with header[2]:
        st.image(str(logo_path), width=80)

    default_dir = get_default_dir()
    st.markdown(
        f'<div class="bw-muted">Input folder: {default_dir}</div>',
        unsafe_allow_html=True,
    )

    inputs = render_inputs()

    if inputs["calculate"]:
        with st.spinner("Calculating..."):
            try:
                signature, result = run_calculation(inputs["params"], default_dir)
            except Exception as exc:
                st.error(f"Gagal menghitung PPV. {exc}")
                return
        render_results(signature, result, inputs["params"])


def render_inputs():
    row = st.columns([2, 2, 2, 2, 2, 2, 1.2])
    with row[0]:
        st.markdown('<div class="bw-label">Jumlah File Signature Wave</div>', unsafe_allow_html=True)
        signature_file_count = st.number_input(
            "Jumlah File Signature Wave",
            min_value=1,
            step=1,
            format="%d",
            key="sig_count",
            label_visibility="collapsed",
        )
    with row[1]:
        st.markdown('<div class="bw-label">Jumlah File Skenario Delay</div>', unsafe_allow_html=True)
        delay_file_count = st.number_input(
            "Jumlah File Skenario Delay",
            min_value=1,
            step=1,
            format="%d",
            key="delay_count",
            label_visibility="collapsed",
        )
    with row[2]:
        st.markdown('<div class="bw-label">Konstanta Lapangan</div>', unsafe_allow_html=True)
        field_constant = st.number_input(
            "Konstanta Lapangan",
            min_value=0.0,
            step=0.1,
            key="field_constant",
            label_visibility="collapsed",
        )
    with row[3]:
        st.markdown('<div class="bw-label">Muatan Signature Hole (kg)</div>', unsafe_allow_html=True)
        signature_weight = st.number_input(
            "Muatan Signature Hole (kg)",
            min_value=0.0,
            step=0.1,
            key="sig_weight",
            label_visibility="collapsed",
        )
    with row[4]:
        st.markdown('<div class="bw-label">Sampling Rate (sps)</div>', unsafe_allow_html=True)
        sampling_rate = st.number_input(
            "Sampling Rate (sps)",
            min_value=1,
            step=1,
            format="%d",
            key="sampling_rate",
            label_visibility="collapsed",
        )
    with row[5]:
        st.markdown('<div class="bw-label">Lama Pengukuran (ms)</div>', unsafe_allow_html=True)
        measurement_ms = st.number_input(
            "Lama Pengukuran (ms)",
            min_value=1,
            step=1,
            format="%d",
            key="measurement_ms",
            label_visibility="collapsed",
        )
    with row[6]:
        st.markdown('<div class="bw-label">&nbsp;</div>', unsafe_allow_html=True)
        calculate = st.button("Calculate", use_container_width=True)

    if sampling_rate % DEFAULT_SPS != 0:
        st.warning(f"Sampling rate harus habis dibagi {DEFAULT_SPS}.")

    params = InputParams(
        signature_file_count=int(signature_file_count),
        delay_file_count=int(delay_file_count),
        sampling_rate=int(sampling_rate),
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


def render_results(signature, result, inputs: InputParams) -> None:
    signature_ppv_tran = get_peak_abs(signature.tran)
    signature_ppv_vert = get_peak_abs(signature.vert)
    signature_ppv_long = get_peak_abs(signature.long)

    header = st.columns([3, 3, 2])
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
    with header[2]:
        st.markdown(
            f'<div class="bw-subtitle">Optimized Peak Vector Sum(mm/s, 1/{inputs.sampling_rate} ms)</div>',
            unsafe_allow_html=True,
        )

    body = st.columns([3, 3, 2])
    with body[0]:
        st.pyplot(
            plot_series(
                signature.tran,
                f"Signature Transversal Wave PPV = {signature_ppv_tran} mm/s",
                "turquoise",
            )
        )
        st.pyplot(
            plot_series(
                signature.vert,
                f"Signature Vertical Wave PPV = {signature_ppv_vert} mm/s",
                "blue",
            )
        )
        st.pyplot(
            plot_series(
                signature.long,
                f"Signature Longitudinal Wave PPV = {signature_ppv_long} mm/s",
                "purple",
            )
        )
    with body[1]:
        st.pyplot(
            plot_series(
                extract_wave(result.tran, result.opt_tran_index, result.wave_length),
                (
                    f"Skenario {result.opt_tran_index + 1} Full Blast Transversal Wave PPV = "
                    f"{result.opt_tran_ppv} mm/s"
                ),
                "turquoise",
            )
        )
        st.pyplot(
            plot_series(
                extract_wave(result.vert, result.opt_vert_index, result.wave_length),
                (
                    f"Skenario {result.opt_vert_index + 1} Full Blast Vertical Wave PPV = "
                    f"{result.opt_vert_ppv} mm/s"
                ),
                "blue",
            )
        )
        st.pyplot(
            plot_series(
                extract_wave(result.long, result.opt_long_index, result.wave_length),
                (
                    f"Skenario {result.opt_long_index + 1} Full Blast Longitudinal Wave PPV = "
                    f"{result.opt_long_ppv} mm/s"
                ),
                "purple",
            )
        )
    with body[2]:
        st.pyplot(
            plot_series(
                extract_wave(result.pvs, result.opt_pvs_index, result.wave_length),
                (
                    f"Skenario {result.opt_pvs_index + 1} Peak Vector Sum PPV = "
                    f"{result.opt_pvs_ppv} mm/s"
                ),
                "green",
            )
        )
        render_ppv_table(result)


def render_ppv_table(result) -> None:
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
    st.dataframe(df, use_container_width=True, height=260)


def plot_series(data: List[float], title: str, color: str):
    fig, ax = plt.subplots(figsize=(5.2, 2.2))
    ax.plot(range(len(data)), data, color=color)
    ax.set_title(title)
    ax.set_xlabel("Sample")
    ax.set_ylabel("mm/s")
    ax.grid(True, linestyle="-", color="#666", alpha=0.6)
    fig.tight_layout()
    return fig


if __name__ == "__main__":
    main()
