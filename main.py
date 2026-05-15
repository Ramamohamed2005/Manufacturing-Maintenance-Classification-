import pandas as pd
from sqlalchemy import create_engine, text
from urllib.parse import quote_plus

# =====================================================
# DATABASE CONNECTION SETTINGS
# =====================================================

# Replace with your actual PostgreSQL password
DB_PASSWORD = "1234"  # <-- CHANGE THIS!

# Encode password (handles special characters)
encoded_password = quote_plus(DB_PASSWORD)

# Connection string
DB_CONNECTION = f"postgresql://postgres:{encoded_password}@localhost:5432/predictive_maintenance_dwh"

# Create engine
engine = create_engine(DB_CONNECTION)

print("Database connection created successfully!")

# Test the connection
try:
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        print("Connection test successful!")
except Exception as e:
    print(f"Connection failed: {e}")

# SINGLE connection block for all queries
with engine.connect() as conn:
    # Count rows in each table
    tables = ['FactSensorReadings', 'FactFleetEvents', 'DimEquipment', 'DimTime']
    for table in tables:
        try:
            result = conn.execute(text(f"SELECT COUNT(*) FROM maintenance.{table}"))
            count = result.fetchone()[0]
            print(f"{table}: {count:,} rows")
        except Exception as e:
            print(f"{table}: Error - {e}")
    
    # Get all tables in maintenance schema
    result = conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'maintenance'"))
    tables_list = [row[0] for row in result.fetchall()]
    print(f"\nTables in maintenance schema: {tables_list}")