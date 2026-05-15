import pandas as pd
import numpy as np
import os
from sqlalchemy import create_engine, text
from datetime import datetime, timedelta
from urllib.parse import quote_plus
import json


DB_PASSWORD = "Rana@2019!" 
encoded_password = quote_plus(DB_PASSWORD) 

DB_CONNECTION = f"postgresql://postgres:{encoded_password}@localhost:5432/predictive_maintenance_dwh"
engine = create_engine(DB_CONNECTION)
print("Database connection created")


AI4I_PATH = "ai4i2020.csv"
SCANIA_FOLDER = "SCANIA Component X"
METROPT3_PATH = "MetroPT3(AirCompressor).csv"
PUMP_PATH ="Large_Industrial_Pump_Maintenance_Dataset.csv"


print("STARTING ETL PROCESS FOR ALL DATASETS")


print("1. LOADING AI4I 2020 DATASET")

try:
    df_ai4i = pd.read_csv(AI4I_PATH)
    print(f"Loaded {len(df_ai4i)} rows")
    
    df_ai4i['timestamp'] = pd.date_range(start='2024-01-01', periods=len(df_ai4i), freq='h')
    df_ai4i['time_key'] = df_ai4i['timestamp'].dt.strftime('%Y%m%d%H').astype(int)
    
    with engine.connect() as conn:
        result = conn.execute(text("SELECT equipment_key FROM maintenance.DimEquipment WHERE ai4i_machine_id = 'M001'"))
        equipment = result.fetchone()
        
        if not equipment:
            conn.execute(text("""
                INSERT INTO maintenance.DimEquipment (ai4i_machine_id, equipment_type, manufacturer, source_system)
                VALUES ('M001', 'CNC_Machine', 'Siemens', 'AI4I')
            """))
            conn.commit()
            result = conn.execute(text("SELECT equipment_key FROM maintenance.DimEquipment WHERE ai4i_machine_id = 'M001'"))
            equipment = result.fetchone()
        
        equipment_key = equipment[0]
        print(f"Equipment key: {equipment_key}")
    
    df_to_load = pd.DataFrame({
        'equipment_key': equipment_key,
        'time_key': df_ai4i['time_key'],
        'udi': df_ai4i['UDI'],
        'air_temperature_k': df_ai4i['Air temperature [K]'],
        'process_temperature_k': df_ai4i['Process temperature [K]'],
        'rotational_speed_rpm': df_ai4i['Rotational speed [rpm]'],
        'torque_nm': df_ai4i['Torque [Nm]'],
        'tool_wear_min': df_ai4i['Tool wear [min]'],
        'product_type': df_ai4i['Type'],
        'twf_failure': df_ai4i['TWF'].astype(bool),
        'hdf_failure': df_ai4i['HDF'].astype(bool),
        'pwf_failure': df_ai4i['PWF'].astype(bool),
        'osf_failure': df_ai4i['OSF'].astype(bool),
        'rnf_failure': df_ai4i['RNF'].astype(bool),
        'machine_failure': df_ai4i['Machine failure'].astype(bool)
    })
    
    batch_size = 1000
    for i in range(0, len(df_to_load), batch_size):
        batch = df_to_load.iloc[i:i+batch_size]
        batch.to_sql('factai4i', engine, schema='maintenance', if_exists='append', index=False)
        print(f"Loaded rows {i} to {min(i+batch_size, len(df_to_load))}")
    
    print(f"AI4I: Loaded {len(df_to_load)} rows into FactAI4I")
    
except Exception as e:
    print(f"AI4I Error: {e}")


print("2. LOADING SCANIA DATASET")

if os.path.exists(SCANIA_FOLDER):
    print("SCANIA folder contents:")
    for f in os.listdir(SCANIA_FOLDER):
        print(f"  - {f}")

try:
    operational_path = os.path.join(SCANIA_FOLDER, "train_operational_readouts.csv")
    df_ops = pd.read_csv(operational_path, encoding='latin1')
    print(f"Loaded {len(df_ops)} operational rows")
    
    # Find the label file - could be train_labels.csv or something else
    label_files = [f for f in os.listdir(SCANIA_FOLDER) if 'label' in f.lower()]
    print(f"Found label files: {label_files}")
    
    if not label_files:
        print("No label file found. Will proceed without labels.")
        df_labels = pd.DataFrame()
    else:
        labels_path = os.path.join(SCANIA_FOLDER, label_files[0])
        df_labels = pd.read_csv(labels_path)
        print(f"Loaded {len(df_labels)} label rows")
        print(f"Label columns: {list(df_labels.columns)}")
    
    # Merge if labels exist
    if len(df_labels) > 0:
        df_merged = df_ops.merge(df_labels, on='vehicle_id', how='left')
    else:
        df_merged = df_ops.copy()
        df_merged['class_label'] = 0
    
    # Register vehicles
    unique_vehicles = df_merged['vehicle_id'].unique()
    vehicle_equipment_map = {}
    
    with engine.connect() as conn:
        for vehicle_id in unique_vehicles:
            result = conn.execute(text("SELECT equipment_key FROM maintenance.DimEquipment WHERE scania_vehicle_id = :vid"), {"vid": str(vehicle_id)})
            equipment = result.fetchone()
            
            if not equipment:
                conn.execute(text("""
                    INSERT INTO maintenance.DimEquipment (scania_vehicle_id, equipment_type, manufacturer, source_system)
                    VALUES (:vid, 'Truck', 'SCANIA', 'SCANIA')
                """), {"vid": str(vehicle_id)})
                conn.commit()
                result = conn.execute(text("SELECT equipment_key FROM maintenance.DimEquipment WHERE scania_vehicle_id = :vid"), {"vid": str(vehicle_id)})
                equipment = result.fetchone()
            
            vehicle_equipment_map[vehicle_id] = equipment[0]
        
        print(f"Registered {len(vehicle_equipment_map)} unique vehicles")
    
    
    sensor_columns = [col for col in df_merged.columns if '_' in col and col[0].isdigit()][:14]

    print(f"Using {len(sensor_columns)} sensor columns: {sensor_columns[:5]}...")
    
    SAMPLE_SIZE = None  # Change to None to load all 1.1M rows
    if SAMPLE_SIZE:
        df_sample = df_merged.head(SAMPLE_SIZE)
        print(f"Using sample of {SAMPLE_SIZE} rows (not full dataset)")
    else:
        df_sample = df_merged
        print(f"Loading all {len(df_sample)} rows")
    
    scania_data = []

    def clean_nan(val):
        return None if pd.isna(val) else float(val)

    for idx, row in df_sample.iterrows():
        equipment_key = vehicle_equipment_map.get(row['vehicle_id'])
        if equipment_key:
            record = {
                'equipment_key': equipment_key,
                'time_step': row['time_step'],
                'has_failed': bool(row.get('class_label', 0)) if 'class_label' in row else False,
                # Store sensor readings as a JSONB field for flexibility
                'sensor_readings': json.dumps({col: clean_nan(row[col]) for col in sensor_columns if col in row})

            }
            scania_data.append(record)
    
    df_scania = pd.DataFrame(scania_data)
    
    batch_size = 5000
    for i in range(0, len(df_scania), batch_size):
        batch = df_scania.iloc[i:i+batch_size]
        batch.to_sql('factscania', engine, schema='maintenance', if_exists='append', index=False)
        print(f"Loaded rows {i} to {min(i+batch_size, len(df_scania))}")
    
    print(f"SCANIA: Loaded {len(df_scania)} rows into FactScania")
    
except Exception as e:
    print(f"SCANIA Error: {e}")


print("3. LOADING METROPT3 DATASET (Large file - chunking)")

try:
    with engine.connect() as conn:
        result = conn.execute(text("SELECT equipment_key FROM maintenance.DimEquipment WHERE metropt3_compressor_id = 'COMP_001'"))
        equipment = result.fetchone()
        
        if not equipment:
            conn.execute(text("""
                INSERT INTO maintenance.DimEquipment (metropt3_compressor_id, equipment_type, manufacturer, source_system)
                VALUES ('COMP_001', 'AirCompressor', 'Knorr-Bremse', 'MetroPT3')
            """))
            conn.commit()
            result = conn.execute(text("SELECT equipment_key FROM maintenance.DimEquipment WHERE metropt3_compressor_id = 'COMP_001'"))
            equipment = result.fetchone()
        
        metro_equipment_key = equipment[0]
        print(f"MetroPT3 equipment key: {metro_equipment_key}")
    
    chunk_size = 50000
    total_loaded = 0
    
    # Define columns to load (skip 'Unnamed: 0')
    columns_to_load = ['timestamp', 'TP2', 'TP3', 'H1', 'DV_pressure', 'Reservoirs', 
                       'Oil_temperature', 'Motor_current', 'COMP', 'DV_eletric', 
                       'Towers', 'MPG', 'LPS', 'Pressure_switch', 'Oil_level', 'Caudal_impulses']
    
    for chunk in pd.read_csv(METROPT3_PATH, chunksize=chunk_size):
        # Create time_key
        chunk['timestamp'] = pd.to_datetime(chunk['timestamp'])
        chunk['time_key'] = chunk['timestamp'].dt.strftime('%Y%m%d%H').astype(int)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT time_key FROM maintenance.DimTime"))
            valid_time_keys = [row[0] for row in result.fetchall()]
            
        # Filter to only valid time_keys
        chunk = chunk[chunk['time_key'].isin(valid_time_keys)]
        if len(chunk) == 0:
            continue
        
        # Prepare for loading
        df_chunk = pd.DataFrame({
            'equipment_key': metro_equipment_key,
            'time_key': chunk['time_key'],
            'tp2_pressure_bar': chunk['TP2'],
            'tp3_pressure_bar': chunk['TP3'],
            'h1_pressure_bar': chunk['H1'],
            'dv_pressure_bar': chunk['DV_pressure'],
            'reservoirs_pressure_bar': chunk['Reservoirs'],
            'oil_temperature_celsius': chunk['Oil_temperature'],
            'motor_current_amps': chunk['Motor_current'],
            'comp_signal': chunk['COMP'].astype(bool),
            'dv_electric_signal': chunk['DV_eletric'].astype(bool),
            'towers_signal': chunk['Towers'].astype(bool),
            'mpg_signal': chunk['MPG'].astype(bool),
            'lps_signal': chunk['LPS'].astype(bool),
            'pressure_switch': chunk['Pressure_switch'].astype(bool),
            'oil_level_ok': chunk['Oil_level'].astype(bool),
            'caudal_impulse': chunk['Caudal_impulses'].astype(bool),
            'label_status': 'unknown'
        })
        
        # Load this chunk
        df_chunk.to_sql('factmetropt3', engine, schema='maintenance', if_exists='append', index=False)
        total_loaded += len(df_chunk)
        print(f"Loaded {total_loaded:,} rows...", end='\r')
    
    print(f"MetroPT3: Loaded {total_loaded:,} rows into FactMetroPT3")
    
except Exception as e:
    print(f"MetroPT3 Error: {e}")


print("4. LOADING INDUSTRIAL PUMP DATASET")

try:
    df_pump = pd.read_csv(PUMP_PATH)
    print(f"Loaded {len(df_pump)} rows")
    
    # Create timestamps (pump data has no timestamp, create sequential)
    df_pump['timestamp'] = pd.date_range(start='2024-01-01', periods=len(df_pump), freq='min')  # Minute intervals
    df_pump['time_key'] = df_pump['timestamp'].dt.strftime('%Y%m%d%H').astype(int)    
    # Get or create equipment for each pump
    with engine.connect() as conn:
        for pump_id in df_pump['Pump_ID'].unique():
            result = conn.execute(text("SELECT equipment_key FROM maintenance.DimEquipment WHERE pump_id = :pid"), {"pid": str(pump_id)})
            equipment = result.fetchone()
            
            if not equipment:
                conn.execute(text("""
                    INSERT INTO maintenance.DimEquipment (pump_id, equipment_type, manufacturer, source_system)
                    VALUES (:pid, 'IndustrialPump', 'Grundfos', 'Pump')
                """), {"pid": str(pump_id)})
                conn.commit()
        
        print(f"Registered {df_pump['Pump_ID'].nunique()} pumps")
    
    # Prepare data for loading
    df_to_load = pd.DataFrame({
        'equipment_key': 0,  # Will map below
        'time_key': df_pump['time_key'],
        'temperature': df_pump['Temperature'],
        'vibration': df_pump['Vibration'],
        'pressure': df_pump['Pressure'],
        'flow_rate': df_pump['Flow_Rate'],
        'rpm': df_pump['RPM'],
        'operational_hours': df_pump['Operational_Hours'],
        'is_failing': df_pump['Maintenance_Flag'].astype(bool)
    })
    
    # Map equipment keys
    pump_key_map = {}
    with engine.connect() as conn:
        for pump_id in df_pump['Pump_ID'].unique():
            result = conn.execute(text("SELECT equipment_key FROM maintenance.DimEquipment WHERE pump_id = :pid"), {"pid": str(pump_id)})
            pump_key_map[pump_id] = result.fetchone()[0]
    
    df_to_load['equipment_key'] = df_pump['Pump_ID'].map(pump_key_map)
    
    batch_size = 2000
    for i in range(0, len(df_to_load), batch_size):
        batch = df_to_load.iloc[i:i+batch_size]
        batch.to_sql('factpump', engine, schema='maintenance', if_exists='append', index=False)
        print(f"   Loaded rows {i} to {min(i+batch_size, len(df_to_load))}")
    
    print(f"Pump: Loaded {len(df_to_load)} rows into FactPump")
    
except Exception as e:
    print(f"Pump Error: {e}")


print("5. VERIFICATION - CHECKING DATA IN DATABASE")

try:
    with engine.connect() as conn:
        # Check each table
        tables = ['factai4i', 'factscania', 'factmetropt3', 'factpump']
        for table in tables:
            result = conn.execute(text(f"SELECT COUNT(*) FROM maintenance.{table}"))
            count = result.fetchone()[0]
            print(f"maintenance.{table}: {count:,} rows")
        
        # Check dimensions
        result = conn.execute(text("SELECT source_system, COUNT(*) FROM maintenance.DimEquipment GROUP BY source_system"))
        print("Equipment by source:")
        for row in result:
            print(f"{row[0]}: {row[1]} equipment")
            
except Exception as e:
    print(f"Verification Error: {e}")

print("ETL PROCESS COMPLETE!")
