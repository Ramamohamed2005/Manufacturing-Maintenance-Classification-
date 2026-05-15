import pandas as pd
import os
from pathlib import Path



AI4I_PATH = "ai4i2020.csv"
SCANIA_FOLDER = "SCANIA Component X"
METROPT3_PATH = "MetroPT3(AirCompressor).csv "
PUMP_PATH ="Large_Industrial_Pump_Maintenance_Dataset.csv"


print("AI4I 2020 DATASET")

try:
    df_ai4i = pd.read_csv(AI4I_PATH)
    print(f"File loaded successfully")
    print(f"Shape: {df_ai4i.shape[0]} rows, {df_ai4i.shape[1]} columns")
    print(f"Column names:")
    for col in df_ai4i.columns:
        print(f"   - {col} ({df_ai4i[col].dtype})")
    print(f"First 3 rows:")
    print(df_ai4i.head(3))
    print(f"Data types summary:")
    print(df_ai4i.dtypes.value_counts())
except Exception as e:
    print(f"Error loading AI4I: {e}")
    print(f"Path tried: {AI4I_PATH}")



print("SCANIA COMPONENT X DATASET")

try:
    if os.path.exists(SCANIA_FOLDER):
        csv_files = [f for f in os.listdir(SCANIA_FOLDER) if f.endswith('.csv')]
        print(f"Found {len(csv_files)} CSV files in SCANIA folder:")
        for file in csv_files:
            file_path = os.path.join(SCANIA_FOLDER, file)
            df_temp = pd.read_csv(file_path, nrows=5)
            print(f"File: {file}")
            print(f"- Shape: {pd.read_csv(file_path).shape[0]} rows (approx)")
            print(f"- Columns: {list(df_temp.columns)[:5]}... (total {len(df_temp.columns)})")
            print(f"- Sample: {df_temp.iloc[0].to_dict() if len(df_temp) > 0 else 'Empty'}")
    else:
        print(f"SCANIA folder not found at: {SCANIA_FOLDER}")
        print(f"Please update the path")
except Exception as e:
    print(f"Error exploring SCANIA: {e}")


print("METROPT3 DATASET")

try:
    df_metro = pd.read_csv(METROPT3_PATH, nrows=10)
    print(f"File loaded successfully (first 10 rows)")
    print(f"Full file size: {os.path.getsize(METROPT3_PATH) / (1024*1024):.2f} MB")
    print(f"Column names:")
    for col in df_metro.columns:
        print(f"- {col} ({df_metro[col].dtype})")
    print(f"First 3 rows:")
    print(df_metro.head(3))
except Exception as e:
    print(f"Error loading MetroPT3: {e}")
    print(f"Path tried: {METROPT3_PATH}")


print("LARGE INDUSTRIAL PUMP DATASET")

try:
    df_pump = pd.read_csv(PUMP_PATH, nrows=10)
    print(f"File loaded successfully (first 10 rows)")
    print(f"Shape: {pd.read_csv(PUMP_PATH).shape[0]} rows (approx), {df_pump.shape[1]} columns")
    print(f"Column names:")
    for col in df_pump.columns:
        print(f"- {col} ({df_pump[col].dtype})")
    print(f"First 3 rows:")
    print(df_pump.head(3))
except Exception as e:
    print(f"Error loading Pump dataset: {e}")
    print(f"Path tried: {PUMP_PATH}")
