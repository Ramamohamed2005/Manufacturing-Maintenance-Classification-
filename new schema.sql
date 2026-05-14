
CREATE SCHEMA IF NOT EXISTS maintenance;
SET search_path TO maintenance, public;

-- 1. DimEquipment
CREATE TABLE maintenance.DimEquipment (
    equipment_key SERIAL PRIMARY KEY,
    ai4i_machine_id VARCHAR(20),
    scania_vehicle_id VARCHAR(50),
    metropt3_compressor_id VARCHAR(20),
    pump_id VARCHAR(20),
    equipment_type VARCHAR(50),
    manufacturer VARCHAR(100),
    source_system VARCHAR(20) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT valid_source CHECK (source_system IN ('AI4I', 'SCANIA', 'MetroPT3', 'Pump'))
);

CREATE INDEX idx_dim_equipment_source ON maintenance.DimEquipment(source_system);

-- 2. DimTime (Pre-populated for 2024)
CREATE TABLE maintenance.DimTime (
    time_key INTEGER PRIMARY KEY,
    full_timestamp TIMESTAMP NOT NULL,
    date DATE NOT NULL,
    year INTEGER NOT NULL,
    month INTEGER NOT NULL,
    day INTEGER NOT NULL,
    hour INTEGER NOT NULL,
    shift VARCHAR(10)
);

CREATE INDEX idx_dim_time_date ON maintenance.DimTime(date);
CREATE INDEX idx_dim_time_hour ON maintenance.DimTime(hour);

-- 3. DimFailureType
CREATE TABLE maintenance.DimFailureType (
    failure_type_key SERIAL PRIMARY KEY,
    failure_code VARCHAR(20) NOT NULL UNIQUE,
    failure_name VARCHAR(100),
    failure_category VARCHAR(50),
    severity_level INTEGER
);



-- 4. FactAI4I (Complete)
CREATE TABLE maintenance.FactAI4I (
    ai4i_measurement_id BIGSERIAL PRIMARY KEY,
    equipment_key INTEGER NOT NULL REFERENCES maintenance.DimEquipment(equipment_key),
    time_key INTEGER NOT NULL REFERENCES maintenance.DimTime(time_key),
    udi INTEGER NOT NULL,
    air_temperature_k FLOAT NOT NULL,
    process_temperature_k FLOAT NOT NULL,
    rotational_speed_rpm FLOAT NOT NULL,
    torque_nm FLOAT NOT NULL,
    tool_wear_min FLOAT NOT NULL,
    product_type CHAR(1),
    twf_failure BOOLEAN DEFAULT FALSE,
    hdf_failure BOOLEAN DEFAULT FALSE,
    pwf_failure BOOLEAN DEFAULT FALSE,
    osf_failure BOOLEAN DEFAULT FALSE,
    rnf_failure BOOLEAN DEFAULT FALSE,
    machine_failure BOOLEAN DEFAULT FALSE
);

CREATE INDEX idx_fact_ai4i_time ON maintenance.FactAI4I(time_key);
CREATE INDEX idx_fact_ai4i_failure ON maintenance.FactAI4I(machine_failure);

-- 5. FactSCANIA (Using JSONB for flexible sensors)
CREATE TABLE maintenance.FactScania (
    scania_measurement_id BIGSERIAL PRIMARY KEY,
    equipment_key INTEGER NOT NULL REFERENCES maintenance.DimEquipment(equipment_key),
    time_step INTEGER NOT NULL,
    has_failed BOOLEAN,
    sensor_readings JSONB
);

CREATE INDEX idx_fact_scania_equipment ON maintenance.FactScania(equipment_key);
CREATE INDEX idx_fact_scania_failed ON maintenance.FactScania(has_failed);
CREATE INDEX idx_fact_scania_sensors ON maintenance.FactScania USING GIN (sensor_readings);

-- 6. FactMetroPT3 (Complete with all sensors)
CREATE TABLE maintenance.FactMetroPT3 (
    metro_measurement_id BIGSERIAL PRIMARY KEY,
    equipment_key INTEGER NOT NULL REFERENCES maintenance.DimEquipment(equipment_key),
    time_key INTEGER NOT NULL REFERENCES maintenance.DimTime(time_key),
    tp2_pressure_bar FLOAT,
    tp3_pressure_bar FLOAT,
    h1_pressure_bar FLOAT,
    dv_pressure_bar FLOAT,
    reservoirs_pressure_bar FLOAT,
    oil_temperature_celsius FLOAT,
    motor_current_amps FLOAT,
    comp_signal BOOLEAN,
    dv_electric_signal BOOLEAN,
    towers_signal BOOLEAN,
    mpg_signal BOOLEAN,
    lps_signal BOOLEAN,
    pressure_switch BOOLEAN,
    oil_level_ok BOOLEAN,
    caudal_impulse BOOLEAN,
    label_status VARCHAR(20) DEFAULT 'unknown'
);

CREATE INDEX idx_fact_metro_time ON maintenance.FactMetroPT3(time_key);
CREATE INDEX idx_fact_metro_label ON maintenance.FactMetroPT3(label_status);

-- 7. FactPump (Complete)
CREATE TABLE maintenance.FactPump (
    pump_measurement_id BIGSERIAL PRIMARY KEY,
    equipment_key INTEGER NOT NULL REFERENCES maintenance.DimEquipment(equipment_key),
    time_key INTEGER NOT NULL REFERENCES maintenance.DimTime(time_key),
    temperature FLOAT,
    vibration FLOAT,
    pressure FLOAT,
    flow_rate FLOAT,
    rpm FLOAT,
    operational_hours FLOAT,
    is_failing BOOLEAN NOT NULL
);

CREATE INDEX idx_fact_pump_time ON maintenance.FactPump(time_key);
CREATE INDEX idx_fact_pump_failing ON maintenance.FactPump(is_failing);



-- New section for phase 2 modifications

-- (Combines AI4I + MetroPT3 + Pump for unified ML)
-- =====================================================

CREATE TABLE maintenance.FactSensorReadings (
    measurement_id BIGSERIAL PRIMARY KEY,
    equipment_key INTEGER NOT NULL REFERENCES maintenance.DimEquipment(equipment_key),
    time_key INTEGER NOT NULL REFERENCES maintenance.DimTime(time_key),
    
    -- Source tracking (identifies original dataset)
    source_system VARCHAR(20) NOT NULL,  -- 'AI4I', 'MetroPT3', 'Pump'
    
    -- === COMMON FEATURES (present in multiple datasets) ===
    temperature_celsius FLOAT,     -- All 3 datasets have temperature
    pressure_bar FLOAT,            -- MetroPT3 + Pump
    rpm FLOAT,                     -- AI4I + Pump
    
    -- === UNIQUE BUT VALUABLE FEATURES ===
    vibration FLOAT,               -- Pump only
    current_amps FLOAT,            -- MetroPT3 only
    torque_nm FLOAT,               -- AI4I only
    tool_wear_min FLOAT,           -- AI4I only
    
    -- === LABELS (ML target) ===
    label_binary INTEGER NOT NULL,  -- 0=normal, 1=failure (unified!)
    failure_type VARCHAR(20),       -- Detailed: 'TWF', 'HDF', 'Air_Leak', 'Pump_Failure', etc.
    
    -- Metadata
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for FactSensorReadings
CREATE INDEX idx_fsr_equipment ON maintenance.FactSensorReadings(equipment_key);
CREATE INDEX idx_fsr_time ON maintenance.FactSensorReadings(time_key);
CREATE INDEX idx_fsr_source ON maintenance.FactSensorReadings(source_system);
CREATE INDEX idx_fsr_label ON maintenance.FactSensorReadings(label_binary);

-- =====================================================
-- 9. RENAME FactScania to FactFleetEvents (clearer name)
-- =====================================================

ALTER TABLE maintenance.FactScania RENAME TO FactFleetEvents;

-- Note: Indexes automatically rename with the table

-- =====================================================
-- 11. EXTEND DimTime to cover 2020-2026 (for MetroPT3)
-- =====================================================

-- Add missing years (2020-2023, 2025-2026)
INSERT INTO maintenance.DimTime (time_key, full_timestamp, date, year, month, day, hour, shift)
SELECT 
    (EXTRACT(YEAR FROM hourly) * 1000000 + 
     EXTRACT(MONTH FROM hourly) * 10000 + 
     EXTRACT(DAY FROM hourly) * 100 + 
     EXTRACT(HOUR FROM hourly))::INTEGER,
    hourly,
    hourly::DATE,
    EXTRACT(YEAR FROM hourly)::INT,
    EXTRACT(MONTH FROM hourly)::INT,
    EXTRACT(DAY FROM hourly)::INT,
    EXTRACT(HOUR FROM hourly)::INT,
    CASE 
        WHEN EXTRACT(HOUR FROM hourly) BETWEEN 6 AND 13 THEN 'Morning'
        WHEN EXTRACT(HOUR FROM hourly) BETWEEN 14 AND 21 THEN 'Afternoon'
        ELSE 'Night'
    END
FROM generate_series('2020-01-01 00:00:00'::timestamp, '2023-12-31 23:00:00', '1 hour') as hourly
ON CONFLICT (time_key) DO NOTHING;

INSERT INTO maintenance.DimTime (time_key, full_timestamp, date, year, month, day, hour, shift)
SELECT 
    (EXTRACT(YEAR FROM hourly) * 1000000 + 
     EXTRACT(MONTH FROM hourly) * 10000 + 
     EXTRACT(DAY FROM hourly) * 100 + 
     EXTRACT(HOUR FROM hourly))::INTEGER,
    hourly,
    hourly::DATE,
    EXTRACT(YEAR FROM hourly)::INT,
    EXTRACT(MONTH FROM hourly)::INT,
    EXTRACT(DAY FROM hourly)::INT,
    EXTRACT(HOUR FROM hourly)::INT,
    CASE 
        WHEN EXTRACT(HOUR FROM hourly) BETWEEN 6 AND 13 THEN 'Morning'
        WHEN EXTRACT(HOUR FROM hourly) BETWEEN 14 AND 21 THEN 'Afternoon'
        ELSE 'Night'
    END
FROM generate_series('2025-01-01 00:00:00'::timestamp, '2026-12-31 23:00:00', '1 hour') as hourly
ON CONFLICT (time_key) DO NOTHING;











-- =====================================================
-- POPULATE REFERENCE DATA
-- =====================================================

-- Insert failure types
INSERT INTO maintenance.DimFailureType (failure_code, failure_name, failure_category, severity_level) VALUES
('TWF', 'Tool Wear Failure', 'Mechanical', 2),
('HDF', 'Heat Dissipation Failure', 'Thermal', 1),
('PWF', 'Power Failure', 'Electrical', 1),
('OSF', 'Overstrain Failure', 'Mechanical', 2),
('RNF', 'Random Failure', 'Unknown', 3),
('Air_Leak', 'Air Compressor Leak', 'Leak', 2),
('Pump_Failure', 'Pump Malfunction', 'Mechanical', 1);

-- Populate DimTime (all hours of 2024)
INSERT INTO maintenance.DimTime (time_key, full_timestamp, date, year, month, day, hour, shift)
SELECT 
    CAST(to_char(hourly, 'YYYYMMDDHH') AS INTEGER),
    hourly,
    CAST(hourly AS DATE),
    EXTRACT(YEAR FROM hourly)::INT,
    EXTRACT(MONTH FROM hourly)::INT,
    EXTRACT(DAY FROM hourly)::INT,
    EXTRACT(HOUR FROM hourly)::INT,
    CASE 
        WHEN EXTRACT(HOUR FROM hourly) BETWEEN 6 AND 13 THEN 'Morning'
        WHEN EXTRACT(HOUR FROM hourly) BETWEEN 14 AND 21 THEN 'Afternoon'
        ELSE 'Night'
    END
FROM generate_series('2024-01-01 00:00:00'::timestamp, '2024-12-31 23:00:00', '1 hour') as hourly;

-- Insert equipment records (one per dataset as placeholder)
INSERT INTO maintenance.DimEquipment (ai4i_machine_id, equipment_type, manufacturer, source_system) VALUES
('M001', 'CNC_Machine', 'Siemens', 'AI4I');

INSERT INTO maintenance.DimEquipment (metropt3_compressor_id, equipment_type, manufacturer, source_system) VALUES
('COMP_001', 'AirCompressor', 'Knorr-Bremse', 'MetroPT3');

-- Verify everything worked
SELECT 'Schema created successfully!' as status;


-- Check all tables exist
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'maintenance' 
ORDER BY table_name;

-- Check DimTime coverage
SELECT 
    COUNT(*) as total_hours,
    MIN(year) as earliest_year,
    MAX(year) as latest_year
FROM maintenance.DimTime;

-- Check DimEquipment
SELECT 
    source_system,
    COUNT(*) as equipment_count
FROM maintenance.DimEquipment
GROUP BY source_system;

-- Check new consolidated table is empty (ready for ETL)
SELECT 
    'FactSensorReadings' as table_name,
    COUNT(*) as current_rows
FROM maintenance.FactSensorReadings;


SELECT COUNT(*) as dimtime_rows FROM maintenance.DimTime;
SELECT COUNT(*) as dimequipment_rows FROM maintenance.DimEquipment;






-- =====================================================
-- MIGRATE DATA TO FACTSENSORREADINGS (CORRECTED)
-- =====================================================

-- 1. Migrate AI4I data (FIXED)
INSERT INTO maintenance.FactSensorReadings (
    equipment_key, time_key, source_system,
    temperature_celsius, rpm, torque_nm, tool_wear_min,
    label_binary, failure_type
)
SELECT 
    equipment_key, time_key, 'AI4I',
    air_temperature_k - 273.15, rotational_speed_rpm, torque_nm, tool_wear_min,
    machine_failure::INT,  -- ← FIXED: Convert boolean to integer
    CASE 
        WHEN twf_failure THEN 'TWF'
        WHEN hdf_failure THEN 'HDF'
        WHEN pwf_failure THEN 'PWF'
        WHEN osf_failure THEN 'OSF'
        WHEN rnf_failure THEN 'RNF'
        ELSE NULL
    END
FROM maintenance.FactAI4I;

-- 2. Migrate MetroPT3 data (FIXED)
INSERT INTO maintenance.FactSensorReadings (
    equipment_key, time_key, source_system,
    temperature_celsius, pressure_bar, current_amps,
    label_binary, failure_type
)
SELECT 
    equipment_key, time_key, 'MetroPT3',
    oil_temperature_celsius, tp2_pressure_bar, motor_current_amps,
    CASE WHEN label_status = 'failure' THEN 1 ELSE 0 END,  -- ← Already integer, OK
    CASE WHEN label_status = 'failure' THEN 'Air_Leak' ELSE NULL END
FROM maintenance.FactMetroPT3;

-- 3. Migrate Pump data (FIXED)
INSERT INTO maintenance.FactSensorReadings (
    equipment_key, time_key, source_system,
    temperature_celsius, pressure_bar, rpm, vibration,
    label_binary, failure_type
)
SELECT 
    equipment_key, time_key, 'Pump',
    temperature, pressure, rpm, vibration,
    is_failing::INT,  -- ← FIXED: Convert boolean to integer
    CASE WHEN is_failing THEN 'Pump_Failure' ELSE NULL END
FROM maintenance.FactPump;

-- 4. Verify migration
SELECT 
    source_system,
    COUNT(*) as row_count,
    COUNT(temperature_celsius) as has_temp,
    COUNT(pressure_bar) as has_pressure,
    COUNT(rpm) as has_rpm,
    AVG(label_binary) as failure_rate
FROM maintenance.FactSensorReadings
GROUP BY source_system;




-- Drop old fact tables (data now in consolidated tables)
DROP TABLE IF EXISTS maintenance.FactAI4I CASCADE;
DROP TABLE IF EXISTS maintenance.FactMetroPT3 CASCADE;
DROP TABLE IF EXISTS maintenance.FactPump CASCADE;
DROP TABLE IF EXISTS maintenance.dimfailuretype CASCADE;