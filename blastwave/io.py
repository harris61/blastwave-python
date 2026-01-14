from pathlib import Path
from typing import List

from blastwave.models import DelayScenarioData, DistanceData, SignatureWaveData, WeightData

DEFAULT_SPS = 1024


def get_default_dir() -> Path:
    return Path.home() / "Documents" / "Blasting Data"


def load_signature_wave(
    default_dir: Path,
    file_count: int,
    measurement_ms: int,
    ratio_sps: int,
) -> SignatureWaveData:
    dir_wave = default_dir / "Signature Wave"
    files_wave = get_numeric_files(dir_wave, file_count)

    start_wave = 270 * ratio_sps
    end_wave = measurement_ms * ratio_sps
    if end_wave <= start_wave:
        raise ValueError("Lama Pengukuran terlalu kecil untuk window signature.")

    length_wave = end_wave - start_wave
    sum_tran = [0.0] * length_wave
    sum_vert = [0.0] * length_wave
    sum_long = [0.0] * length_wave

    for file_path in files_wave:
        lines = file_path.read_text().splitlines()
        if len(lines) <= end_wave:
            raise ValueError(f"File signature terlalu pendek: {file_path.name}")

        for i in range(length_wave):
            line = lines[start_wave + i]
            parsed = _try_parse_wave_line(line)
            if parsed is None:
                raise ValueError(f"Format data signature tidak valid: {file_path.name}")
            tran, vert, lon = parsed
            sum_tran[i] += tran
            sum_vert[i] += vert
            sum_long[i] += lon

    tran_wave = [value / file_count for value in sum_tran]
    vert_wave = [value / file_count for value in sum_vert]
    long_wave = [value / file_count for value in sum_long]

    return SignatureWaveData(
        tran=tran_wave,
        vert=vert_wave,
        long=long_wave,
        length=length_wave,
    )


def load_delay_scenarios(
    default_dir: Path,
    file_count: int,
    ratio_sps: int,
) -> DelayScenarioData:
    dir_delay = default_dir / "Delay Scenario"
    files_delay = get_numeric_files(dir_delay, file_count)

    delays: List[List[int]] = []
    max_delay = 0

    for file_path in files_delay:
        lines = file_path.read_text().splitlines()
        if len(lines) <= 1:
            raise ValueError(f"Delay file tidak memiliki data: {file_path.name}")

        delay_values: List[int] = []
        for line in lines[1:]:
            try:
                value = int(line)
            except ValueError as exc:
                raise ValueError(f"Data delay tidak valid: {file_path.name}") from exc
            delay_values.append(value * ratio_sps)

        delay_values.sort()
        delays.append(delay_values)
        if delay_values and delay_values[-1] > max_delay:
            max_delay = delay_values[-1]

    return DelayScenarioData(delays=delays, max_delay=max_delay)


def load_weights(default_dir: Path, file_count: int) -> WeightData:
    dir_weight = default_dir / "Explosive Weight"
    files_weight = get_numeric_files(dir_weight, file_count)

    weights: List[List[float]] = []
    for file_path in files_weight:
        lines = file_path.read_text().splitlines()
        weight_values: List[float] = []
        for line in lines:
            try:
                value = float(line)
            except ValueError as exc:
                raise ValueError(f"Data weight tidak valid: {file_path.name}") from exc
            weight_values.append(value)
        weights.append(weight_values)

    return WeightData(weights=weights)


def load_distance_data(default_dir: Path, scenario_count: int) -> DistanceData:
    distance_dir = default_dir / "Simulation Distance"
    avg_path = distance_dir / "distanceaverage.txt"
    sim_path = distance_dir / "distancesimulation.txt"

    avg_lines = avg_path.read_text().splitlines()
    if not avg_lines:
        raise ValueError("distanceaverage.txt kosong.")

    sum_distance = 0.0
    for line in avg_lines:
        try:
            value = float(line)
        except ValueError as exc:
            raise ValueError("Data distance average tidak valid.") from exc
        sum_distance += value

    average_distance = sum_distance / len(avg_lines)
    if average_distance <= 0:
        raise ValueError("Average distance tidak valid.")

    sim_lines = sim_path.read_text().splitlines()
    if len(sim_lines) < scenario_count:
        raise ValueError("Jumlah distance simulation lebih sedikit dari skenario.")

    ratios: List[float] = []
    for line in sim_lines:
        try:
            value = float(line)
        except ValueError as exc:
            raise ValueError("Data distance simulation tidak valid.") from exc
        ratios.append(value / average_distance)

    return DistanceData(ratios=ratios)


def validate_scenario_alignment(
    delays: DelayScenarioData,
    weights: WeightData,
    distances: DistanceData,
) -> None:
    if len(delays.delays) != len(weights.weights):
        raise ValueError("Jumlah file delay dan weight tidak sama.")

    for index, delay_list in enumerate(delays.delays):
        if len(delay_list) != len(weights.weights[index]):
            raise ValueError(f"Jumlah data delay dan weight tidak sama pada skenario {index + 1}.")

    if len(distances.ratios) < len(delays.delays):
        raise ValueError("Jumlah distance ratio kurang dari jumlah skenario.")


def get_numeric_files(dir_path: Path, expected_count: int) -> List[Path]:
    if not dir_path.exists():
        raise ValueError(f"Folder not found: {dir_path}")

    files = list(dir_path.glob("*.txt"))
    mapping = {}
    for file_path in files:
        try:
            value = int(file_path.stem)
        except ValueError:
            continue
        if value >= 1:
            if value in mapping:
                raise ValueError(f"File bernomor {value} duplikat di {dir_path.name}.")
            mapping[value] = file_path

    if len(mapping) < expected_count:
        raise ValueError(f"Jumlah file di {dir_path.name} lebih sedikit dari input.")

    ordered: List[Path] = []
    for value in range(1, expected_count + 1):
        file_path = mapping.get(value)
        if file_path is None:
            raise ValueError(
                f"File di {dir_path.name} harus bernomor mulai 1 sampai {expected_count}."
            )
        ordered.append(file_path)

    return ordered


def _try_parse_wave_line(line: str):
    tokens = line.split()
    if len(tokens) < 3:
        return None
    try:
        tran = float(tokens[0])
        vert = float(tokens[1])
        lon = float(tokens[2])
    except ValueError:
        return None
    return tran, vert, lon
