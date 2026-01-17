# User Guide

## 1) Prepare Data

Ensure your data directory follows this structure:

```
Blasting Data/
  Signature Wave/
  Delay Scenario/
  Explosive Weight/
  Simulation Distance/
```

Each subfolder uses plain `.txt` files as described in the README.

## 2) Run the App

```
streamlit run app.py
```

## 3) Choose Data Directory

Use **Choose Directory** to select the folder that contains `Signature Wave`, `Delay Scenario`, `Explosive Weight`, and `Simulation Distance`.

## 4) Enter Inputs

- Field Constant (B)
- Signature Hole Charge (kg)
- Full Blast Duration (ms)

## 5) Calculate

Click **Calculate** to run the optimization. The charts and table update automatically.

## 6) Output Files

The app writes four files into the same data directory:

- `result_Tran.txt`
- `result_Vert.txt`
- `result_Long.txt`
- `result_PVS.txt`

Each file contains one value per line.

## Troubleshooting

- Verify the sampling rate is consistent across signature files.
- Ensure delay and explosive weight files have matching counts per scenario.
- If the folder dialog does not open, Tkinter may be missing in your Python environment.
