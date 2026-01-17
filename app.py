from pathlib import Path
from typing import List, Optional, Tuple
import base64
import hashlib
import io
import shutil
import subprocess
import sys
import tempfile
import zipfile

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st
import re

from blastwave.core import compute_scenario_waves, extract_wave, get_peak_abs
from blastwave.io import DEFAULT_SPS, load_delay_scenarios, load_distance_data
from blastwave.io import load_signature_wave, load_weights, validate_scenario_alignment
from blastwave.models import InputParams

PAGE_STYLE = """
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
"""
METADATA_NOTE = "Note: Sample rate across signature waves must match."
USBM_FORMULA = "USBM: v = K (D / sqrt(Qmax))^(-B) (Duvall and Petkof)"


def main() -> None:
    assets_dir = Path(__file__).parent / "assets"
    icon_path = assets_dir / "sound__3__zx3_icon.ico"
    logo_path = assets_dir / "itb.png"

    configure_page(icon_path)
    st.markdown('<div style="height:50px;"></div>', unsafe_allow_html=True)
    left_logo = _encode_image_base64(icon_path)
    right_logo = _encode_image_base64(logo_path)
    render_header(left_logo, right_logo)

    st.markdown('<div class="bw-content">', unsafe_allow_html=True)
    data_dir, metadata, validation_errors = load_data_package()
    render_metadata(metadata, validation_errors)

    inputs = render_inputs(metadata, data_dir is not None and not validation_errors)

    if inputs["calculate"] and data_dir is not None:
        with st.spinner("Calculating..."):
            try:
                signature, result = run_calculation(inputs["params"], data_dir)
            except Exception as exc:
                st.error(f"Failed to compute PPV. {exc}")
                return
        output_paths = write_result_files(data_dir, result)
        if output_paths:
            st.info(
                "Output files saved: "
                + ", ".join(str(path) for path in output_paths)
            )
            archive_bytes = build_result_archive(output_paths)
            if archive_bytes:
                st.download_button(
                    "Download result_data.zip",
                    data=archive_bytes,
                    file_name="result_data.zip",
                    mime="application/zip",
                    width="stretch",
                )
        render_results(signature, result, inputs["params"])
    st.markdown("</div>", unsafe_allow_html=True)


def configure_page(icon_path: Path) -> None:
    st.set_page_config(page_title="Blast Wave PPV Optimizer", layout="wide", page_icon=str(icon_path))
    st.markdown(PAGE_STYLE, unsafe_allow_html=True)


def render_header(left_logo: str, right_logo: str) -> None:
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


def render_metadata(metadata: dict, validation_errors: List[str]) -> None:
    if validation_errors:
        st.error("Data package validation failed:\n" + "\n".join(f"- {err}" for err in validation_errors))
    else:
        st.success("Data package validation passed.")
    st.markdown(
        (
            f'<div class="bw-muted">Signature files: {metadata["signature_count"]} | '
            f'Delay files: {metadata["delay_count"]} | Sample rate: {metadata["sampling_rate"]} sps | '
            f"{METADATA_NOTE} | {USBM_FORMULA}</div>"
            '<div class="bw-muted">'
            'Created by: <a href="https://www.linkedin.com/in/harristio-adam/" target="_blank">Harristio Adam</a> | '
            'Supervised by: <a href="https://itb.ac.id/staf/profil/ganda-marihot-simangunsong" target="_blank">'
            'Prof. Dr.Eng. Ir. Ganda Marihot Simangunsong, S.T., M.T.</a> | '
            'Github: <a href="https://github.com/harris61/blastwave-python" target="_blank">'
            'github.com/harris61/blastwave-python</a>'
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def render_inputs(metadata, can_calculate: bool):
    row = st.columns([1.0, 1.6, 1.6, 1.6, 1.2], gap="small")
    with row[0]:
        st.markdown('<div class="bw-label">Data Package (.rar or .zip)</div>', unsafe_allow_html=True)
        st.file_uploader(
            "Upload Data Package",
            type=["rar", "zip"],
            key="data_package",
            label_visibility="collapsed",
        )
    with row[1]:
        st.markdown('<div class="bw-label">Field Constant (B)</div>', unsafe_allow_html=True)
        field_constant = st.number_input(
            "Field Constant",
            min_value=0.0,
            step=0.1,
            format="%g",
            key="field_constant",
            label_visibility="collapsed",
        )
    with row[2]:
        st.markdown('<div class="bw-label">Signature Hole Charge (kg)</div>', unsafe_allow_html=True)
        signature_weight = st.number_input(
            "Signature Hole Charge (kg)",
            min_value=0.0,
            step=0.1,
            format="%g",
            key="sig_weight",
            label_visibility="collapsed",
        )
    with row[3]:
        st.markdown('<div class="bw-label">Full Blast Duration (ms)</div>', unsafe_allow_html=True)
        measurement_ms = st.number_input(
            "Full Blast Duration (ms)",
            min_value=0,
            step=1,
            format="%d",
            key="measurement_ms",
            label_visibility="collapsed",
        )
    with row[4]:
        st.markdown('<div class="bw-label">&nbsp;</div>', unsafe_allow_html=True)
        calculate = st.button("Calculate", width="stretch", disabled=not can_calculate)

    params = InputParams(
        signature_file_count=metadata["signature_count"],
        delay_file_count=metadata["delay_count"],
        sampling_rate=metadata["sampling_rate"],
        measurement_ms=int(measurement_ms),
        field_constant=float(field_constant),
        signature_weight=float(signature_weight),
    )
    return {"params": params, "calculate": calculate}


def load_data_package() -> Tuple[Optional[Path], dict, List[str]]:
    default_metadata = {"signature_count": 0, "delay_count": 0, "sampling_rate": 0}
    uploaded = st.session_state.get("data_package")
    if uploaded is None:
        previous_root = st.session_state.get("temp_root")
        if previous_root:
            shutil.rmtree(previous_root, ignore_errors=True)
            st.session_state.pop("temp_root", None)
            st.session_state.pop("data_dir", None)
            st.session_state.pop("validation_errors", None)
            st.session_state.pop("metadata", None)
            st.session_state.pop("data_hash", None)
        return None, default_metadata, ["Upload a data package (.rar or .zip)."]

    payload = uploaded.getvalue()
    payload_hash = hashlib.sha256(payload).hexdigest()
    cached_hash = st.session_state.get("data_hash")
    if cached_hash != payload_hash:
        previous_root = st.session_state.get("temp_root")
        if previous_root:
            shutil.rmtree(previous_root, ignore_errors=True)

        temp_root = Path(tempfile.mkdtemp(prefix="blastwave_"))
        archive_path = temp_root / uploaded.name
        archive_path.write_bytes(payload)
        extracted_dir = temp_root / "extracted"
        extracted_dir.mkdir(parents=True, exist_ok=True)

        errors = extract_archive(archive_path, extracted_dir)
        data_root = None
        metadata = default_metadata
        if not errors:
            data_root = find_data_root(extracted_dir)
            if data_root is None:
                errors.append(
                    "Required folders not found. Expected Signature Wave, Delay Scenario, "
                    "Explosive Weight, and Simulation Distance."
                )
            else:
                validation_errors, metadata = validate_data_dir(data_root)
                errors.extend(validation_errors)

        st.session_state["data_hash"] = payload_hash
        st.session_state["temp_root"] = str(temp_root)
        st.session_state["data_dir"] = str(data_root) if data_root else ""
        st.session_state["validation_errors"] = errors
        st.session_state["metadata"] = metadata

    data_dir_value = st.session_state.get("data_dir") or ""
    data_dir = Path(data_dir_value) if data_dir_value else None
    metadata = st.session_state.get("metadata", default_metadata)
    validation_errors = st.session_state.get("validation_errors", [])
    return data_dir, metadata, validation_errors


def extract_archive(archive_path: Path, target_dir: Path) -> List[str]:
    suffix = archive_path.suffix.lower()
    if suffix == ".zip":
        try:
            with zipfile.ZipFile(archive_path, "r") as archive:
                archive.extractall(target_dir)
        except zipfile.BadZipFile:
            return ["The ZIP file is invalid or corrupted."]
        return []

    if suffix == ".rar":
        extractor = find_7z_executable()
        if extractor is None:
            return [
                "RAR extraction requires 7-Zip (7z) on the server. "
                "Please upload a .zip package instead."
            ]
        result = shutil.which(extractor) or extractor
        if sys.platform != "win32":
            ensure_executable(Path(result))
        try:
            run = subprocess.run(
                [result, "x", str(archive_path), f"-o{target_dir}", "-y"],
                capture_output=True,
                text=True,
                check=False,
            )
        except OSError as exc:
            return [f"Failed to extract RAR file. {exc}"]
        if run.returncode != 0:
            return [
                "Failed to extract RAR file. Ensure it is a valid .rar archive "
                "and that 7-Zip matches the server OS."
            ]
        return []

    return ["Unsupported archive type. Please upload a .rar or .zip file."]


def find_7z_executable() -> Optional[str]:
    candidates = [
        shutil.which("7z"),
        shutil.which("7za"),
        shutil.which("7zr"),
    ]
    if sys.platform == "win32":
        candidates.extend(
            [
                str(Path(__file__).parent / "tools" / "7z" / "7z.exe"),
                "C:\\Program Files\\7-Zip\\7z.exe",
                "C:\\Program Files (x86)\\7-Zip\\7z.exe",
            ]
        )
    else:
        candidates.append(str(Path(__file__).parent / "tools" / "7z" / "7zz"))
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return candidate
    return None


def ensure_executable(path: Path) -> None:
    try:
        mode = path.stat().st_mode
        path.chmod(mode | 0o111)
    except OSError:
        pass


def find_data_root(extracted_dir: Path) -> Optional[Path]:
    preferred = extracted_dir / "Blasting Data"
    if preferred.exists():
        return preferred
    required = {"Signature Wave", "Delay Scenario", "Explosive Weight", "Simulation Distance"}
    if required.issubset({path.name for path in extracted_dir.iterdir() if path.is_dir()}):
        return extracted_dir
    for child in extracted_dir.iterdir():
        if child.is_dir() and required.issubset({path.name for path in child.iterdir() if path.is_dir()}):
            return child
    return None


def validate_data_dir(data_dir: Path) -> Tuple[List[str], dict]:
    errors: List[str] = []
    signature_dir = data_dir / "Signature Wave"
    delay_dir = data_dir / "Delay Scenario"
    weight_dir = data_dir / "Explosive Weight"
    distance_dir = data_dir / "Simulation Distance"

    for name, path in [
        ("Signature Wave", signature_dir),
        ("Delay Scenario", delay_dir),
        ("Explosive Weight", weight_dir),
        ("Simulation Distance", distance_dir),
    ]:
        if not path.exists():
            errors.append(f"Missing folder: {name}")

    signature_files = list_numeric_files(signature_dir) if signature_dir.exists() else []
    delay_files = list_numeric_files(delay_dir) if delay_dir.exists() else []
    weight_files = list_numeric_files(weight_dir) if weight_dir.exists() else []

    if not signature_files:
        errors.append("Signature Wave must contain numeric .txt files (1.txt, 2.txt, ...).")
    if not delay_files:
        errors.append("Delay Scenario must contain numeric .txt files (1.txt, 2.txt, ...).")
    if not weight_files:
        errors.append("Explosive Weight must contain numeric .txt files (1.txt, 2.txt, ...).")
    if delay_files and weight_files and len(delay_files) != len(weight_files):
        errors.append("Delay Scenario count must match Explosive Weight count.")

    avg_path = distance_dir / "distanceaverage.txt"
    sim_path = distance_dir / "distancesimulation.txt"
    if distance_dir.exists():
        if not avg_path.exists():
            errors.append("Missing file: Simulation Distance/distanceaverage.txt")
        if not sim_path.exists():
            errors.append("Missing file: Simulation Distance/distancesimulation.txt")

    sampling_rate = _read_sample_rate(signature_dir) if signature_dir.exists() else 0
    if signature_files and sampling_rate == 0:
        errors.append("Sample rate not found in signature files.")

    if sim_path.exists() and delay_files:
        sim_lines = sim_path.read_text().splitlines()
        if len(sim_lines) < len(delay_files):
            errors.append("distancesimulation.txt has fewer lines than delay scenarios.")

    metadata = {
        "signature_count": len(signature_files),
        "delay_count": len(delay_files),
        "sampling_rate": sampling_rate,
    }
    return errors, metadata


def list_numeric_files(dir_path: Path) -> List[Path]:
    files: List[Path] = []
    if not dir_path.exists():
        return files
    for path in dir_path.iterdir():
        if not path.is_file():
            continue
        if path.suffix.lower() != ".txt":
            continue
        try:
            value = int(path.stem)
        except ValueError:
            continue
        if value >= 1:
            files.append(path)
    return sorted(files, key=lambda item: int(item.stem))


def build_result_archive(output_paths: List[Path]) -> Optional[bytes]:
    if not output_paths:
        return None
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in output_paths:
            archive.write(path, arcname=path.name)
    return buffer.getvalue()


def run_calculation(inputs: InputParams, default_dir: Path):
    if not default_dir.exists():
        raise ValueError(f"Folder not found: {default_dir}")

    if inputs.sampling_rate % DEFAULT_SPS != 0:
        raise ValueError(f"Sampling rate must be divisible by {DEFAULT_SPS}.")
    if inputs.signature_weight <= 0:
        raise ValueError("Signature hole charge must be > 0.")

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
                f'Optimized Peak Vector Sum (mm/s, 1/{inputs.sampling_rate} ms)</div>'
            ),
            unsafe_allow_html=True,
        )
        st.pyplot(
            plot_series(
                extract_wave(result.pvs, result.opt_pvs_index, result.wave_length),
                f"Scenario {result.opt_pvs_index + 1} Peak Vector Sum PPV = {result.opt_pvs_ppv} mm/s",
                "green",
                max_x,
                figsize=(4.2, 1.8),
            ),
            width="stretch",
        )
        render_ppv_table(result, height=208)

    header = st.columns([3, 3])
    with header[0]:
        st.markdown(
            f'<div class="bw-subtitle">Signature Wave (mm/s, 1/{inputs.sampling_rate} ms)</div>',
            unsafe_allow_html=True,
        )
    with header[1]:
        st.markdown(
            f'<div class="bw-subtitle">Optimized Full Blast Wave (mm/s, 1/{inputs.sampling_rate} ms)</div>',
            unsafe_allow_html=True,
        )

    rows = [
        (
            f"Signature Transversal Wave PPV = {signature_ppv_tran} mm/s",
            signature.tran,
            "turquoise",
            (
                f"Scenario {result.opt_tran_index + 1} Full Blast Transversal Wave PPV = "
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
                f"Scenario {result.opt_vert_index + 1} Full Blast Vertical Wave PPV = "
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
                f"Scenario {result.opt_long_index + 1} Full Blast Longitudinal Wave PPV = "
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
                width="stretch",
            )
        with row[1]:
            st.markdown(f'<div class="bw-plot-title">{right_title}</div>', unsafe_allow_html=True)
            st.pyplot(
                plot_series(right_data, "", right_color, max_x, figsize=(4.2, 1.8)),
                width="stretch",
            )


def write_result_files(output_dir: Path, result) -> List[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = {
        "result_Tran.txt": extract_wave(result.tran, result.opt_tran_index, result.wave_length),
        "result_Vert.txt": extract_wave(result.vert, result.opt_vert_index, result.wave_length),
        "result_Long.txt": extract_wave(result.long, result.opt_long_index, result.wave_length),
        "result_PVS.txt": extract_wave(result.pvs, result.opt_pvs_index, result.wave_length),
    }
    written: List[Path] = []
    try:
        for name, data in outputs.items():
            path = output_dir / name
            with path.open("w", encoding="ascii", newline="\n") as handle:
                for value in data:
                    handle.write(f"{value}\n")
            written.append(path)
    except OSError as exc:
        st.error(f"Failed to save output files. {exc}")
        return []
    return written


def render_ppv_table(result, height: int = 260) -> None:
    scenario_count = len(result.ppv[0])
    rows: List[dict] = []
    for index in range(scenario_count):
        rows.append(
            {
                "Delay Scenario": index + 1,
                "PPV Tran (mm/s)": result.ppv[0][index],
                "PPV Vert (mm/s)": result.ppv[1][index],
                "PPV Long (mm/s)": result.ppv[2][index],
                "PPV PVS (mm/s)": result.ppv[3][index],
            }
        )

    df = pd.DataFrame(rows)
    st.dataframe(df, width="stretch", height=height)


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
