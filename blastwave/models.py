from dataclasses import dataclass
from typing import List


@dataclass
class InputParams:
    signature_file_count: int
    delay_file_count: int
    sampling_rate: int
    measurement_ms: int
    field_constant: float
    signature_weight: float


@dataclass
class SignatureWaveData:
    tran: List[float]
    vert: List[float]
    long: List[float]
    length: int


@dataclass
class DelayScenarioData:
    delays: List[List[int]]
    max_delay: int


@dataclass
class WeightData:
    weights: List[List[float]]


@dataclass
class DistanceData:
    ratios: List[float]


@dataclass
class ComputationResult:
    wave_length: int
    tran: List[List[float]]
    vert: List[List[float]]
    long: List[List[float]]
    pvs: List[List[float]]
    ppv: List[List[float]]
    opt_tran_index: int
    opt_vert_index: int
    opt_long_index: int
    opt_pvs_index: int
    opt_tran_ppv: float
    opt_vert_ppv: float
    opt_long_ppv: float
    opt_pvs_ppv: float
