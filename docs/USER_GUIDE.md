# User Guide

## 1) Prepare Data

Package your data using this structure (top-level folder name can be `Blasting Data`):

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

## 3) Upload Data Package

Use the **Data Package** uploader to provide a `.rar` or `.zip` file containing the required folders.
The default upload limit is 100 MB.

## 4) Enter Inputs

- Field Constant (B)
- Signature Hole Charge (kg)
- Full Blast Duration (ms)

## 5) Calculate

Click **Calculate** to run the optimization. The charts and table update automatically.

## 6) Output Files

The app generates four result files and bundles them into a download:

- `result_Tran.txt`
- `result_Vert.txt`
- `result_Long.txt`
- `result_PVS.txt`
- `result_data.zip`

Each output file contains one value per line.

## Troubleshooting

- Verify the sampling rate is consistent across signature files.
- Ensure delay and explosive weight files have matching counts per scenario.
- If `.rar` extraction fails, upload a `.zip` package or ensure the Linux 7-Zip binary is available (`tools/7z/7zz`).
