# Blast Wave PPV Optimizer (Streamlit)

Port of the WinForms app to Python + Streamlit. This version reads input from the same default location:

`C:\Users\<YourUser>\Documents\Blasting Data`

## Folder Structure

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

- Sampling rate must be divisible by 1024.
- Signature wave file must contain at least 3 numeric columns per line.
- Delay files skip the first line (header), remaining lines are delay values in ms.
