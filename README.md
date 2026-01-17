# Blast Wave PPV Optimizer (Streamlit)

Blast vibration PPV optimizer for signature-hole workflows, implemented in Python + Streamlit. The app ingests a data package (.rar or .zip) with the required folder structure and computes optimized full-blast waves using the USBM formulation.

## Key Features

- Upload a data package (`.rar` or `.zip`) from the UI.
- Compute optimized full-blast transversal, vertical, longitudinal, and PVS waves.
- Export outputs as `result_Tran.txt`, `result_Vert.txt`, `result_Long.txt`, and `result_PVS.txt`.
- Download the results as `result_data.zip`.
- Scientific core isolated in `blastwave/core.py` for research continuity.

## Data Package Layout

```
Blasting Data/
  Signature Wave/
    1.txt
    2.txt
    ...
  Delay Scenario/
    1.txt
    2.txt
    ...
  Explosive Weight/
    1.txt
    2.txt
    ...
  Simulation Distance/
    distanceaverage.txt
    distancesimulation.txt
```

## Run Locally

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

## Notes

- Sampling rate must be divisible by 1024 and consistent across signature files.
- Signature wave files must contain at least three numeric columns per line.
- Delay files skip the first line (header); remaining lines are delay values in ms.
- Output waveforms are saved as plain text with one value per line.
- `.rar` extraction requires 7-Zip (`7z`) that matches the server OS. Streamlit Cloud runs on Linux, so upload a `.zip` package unless a Linux 7z binary is bundled.
- Upload limit is 100 MB by default (configurable in `.streamlit/config.toml`).

## Documentation

See `docs/USER_GUIDE.md` for a concise end-to-end workflow.
