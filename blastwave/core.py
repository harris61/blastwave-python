import math
from typing import List, Tuple

from blastwave.models import ComputationResult, DelayScenarioData, DistanceData, SignatureWaveData, WeightData


def compute_scenario_waves(
    signature: SignatureWaveData,
    delays: DelayScenarioData,
    weights: WeightData,
    distances: DistanceData,
    field_constant: float,
    signature_weight: float,
) -> ComputationResult:
    scenario_count = len(delays.delays)
    wave_length = signature.length + delays.max_delay + 100

    list_tran = _blank_2d(scenario_count, wave_length)
    list_vert = _blank_2d(scenario_count, wave_length)
    list_long = _blank_2d(scenario_count, wave_length)
    list_pvs = _blank_2d(scenario_count, wave_length)

    for scenario in range(scenario_count):
        distance_ratio = distances.ratios[scenario]
        if distance_ratio <= 0:
            raise ValueError(f"Invalid distance ratio in scenario {scenario + 1}.")

        delay_list = delays.delays[scenario]
        weight_list = weights.weights[scenario]

        for index, delay_value in enumerate(delay_list):
            scale = math.pow(
                (weight_list[index] / signature_weight) / math.pow(distance_ratio, 2),
                0.5 * field_constant,
            )

            for sample in range(signature.length):
                target_index = sample + delay_value
                list_tran[scenario][target_index] += signature.tran[sample] * scale
                list_vert[scenario][target_index] += signature.vert[sample] * scale
                list_long[scenario][target_index] += signature.long[sample] * scale

    for scenario in range(scenario_count):
        for sample in range(wave_length):
            tran = list_tran[scenario][sample]
            vert = list_vert[scenario][sample]
            lon = list_long[scenario][sample]
            list_pvs[scenario][sample] = math.sqrt(tran * tran + vert * vert + lon * lon)

    list_ppv = _blank_2d(4, scenario_count)
    for scenario in range(scenario_count):
        tran_part = extract_wave(list_tran, scenario, wave_length)
        vert_part = extract_wave(list_vert, scenario, wave_length)
        long_part = extract_wave(list_long, scenario, wave_length)
        pvs_part = extract_wave(list_pvs, scenario, wave_length)

        list_ppv[0][scenario] = get_peak_abs(tran_part)
        list_ppv[1][scenario] = get_peak_abs(vert_part)
        list_ppv[2][scenario] = get_peak_abs(long_part)
        list_ppv[3][scenario] = get_peak_abs(pvs_part)

    tran_parts = list_ppv[0]
    vert_parts = list_ppv[1]
    long_parts = list_ppv[2]
    pvs_parts = list_ppv[3]

    ppv_tran_full, opt_tran_index = get_min_abs(tran_parts)
    ppv_vert_full, opt_vert_index = get_min_abs(vert_parts)
    ppv_long_full, opt_long_index = get_min_abs(long_parts)
    ppv_pvs, opt_pvs_index = get_min_abs(pvs_parts)

    return ComputationResult(
        wave_length=wave_length,
        tran=list_tran,
        vert=list_vert,
        long=list_long,
        pvs=list_pvs,
        ppv=list_ppv,
        opt_tran_index=opt_tran_index,
        opt_vert_index=opt_vert_index,
        opt_long_index=opt_long_index,
        opt_pvs_index=opt_pvs_index,
        opt_tran_ppv=ppv_tran_full,
        opt_vert_ppv=ppv_vert_full,
        opt_long_ppv=ppv_long_full,
        opt_pvs_ppv=ppv_pvs,
    )


def get_peak_abs(values: List[float]) -> float:
    if not values:
        return 0.0
    best = values[0]
    for value in values[1:]:
        if abs(value) > abs(best):
            best = value
    return best


def get_min_abs(values: List[float]) -> Tuple[float, int]:
    if not values:
        return 0.0, -1
    best = values[0]
    index = 0
    for idx, value in enumerate(values[1:], start=1):
        if abs(value) < abs(best):
            best = value
            index = idx
    return best, index


def extract_wave(source: List[List[float]], row: int, length: int) -> List[float]:
    return source[row][:length]


def _blank_2d(rows: int, cols: int) -> List[List[float]]:
    return [[0.0 for _ in range(cols)] for _ in range(rows)]
