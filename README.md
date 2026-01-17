# Blast Wave PPV Optimizer (Streamlit)

Blast vibration PPV optimizer for signature-hole workflows, implemented in Python + Streamlit. The app reads blasting data from a selected data directory and computes optimized full-blast waves using the USBM formulation.

## Key Features

- Choose the data directory from the UI (default: `C:\Users\<YourUser>\Documents\Blasting Data`).
- Compute optimized full-blast transversal, vertical, longitudinal, and PVS waves.
- Export outputs as `result_Tran.txt`, `result_Vert.txt`, `result_Long.txt`, and `result_PVS.txt` in the data directory.
- Scientific core isolated in `blastwave/core.py` for research continuity.

## Data Directory Layout

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

## Documentation

See `docs/USER_GUIDE.md` for a concise end-to-end workflow.
