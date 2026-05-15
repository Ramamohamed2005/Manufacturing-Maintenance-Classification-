-- DROP SCHEMA IF EXISTS maintenance CASCADE;

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




-- 2. DimTime
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
FROM generate_series('2020-01-01 00:00:00'::timestamp, '2026-12-31 23:00:00', '1 hour') as hourly
ON CONFLICT (time_key) DO NOTHING;

-- SELECT COUNT(*) as total_rows, 
--        MIN(time_key) as min_key, 
--        MAX(time_key) as max_key,
--        MIN(full_timestamp) as earliest,
--        MAX(full_timestamp) as latest
-- FROM maintenance.DimTime;

-- -- Show sample of time_keys
-- SELECT time_key, full_timestamp, shift 
-- FROM maintenance.DimTime 
-- LIMIT 10;

-- 3. DimFailureType
CREATE TABLE maintenance.DimFailureType (
    failure_type_key SERIAL PRIMARY KEY,
    failure_code VARCHAR(20) NOT NULL UNIQUE,
    failure_name VARCHAR(100),
    failure_category VARCHAR(50),
    severity_level INTEGER
);


-- 4. FactAI4I
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

-- 5. FactSCANIA
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

-- 6. FactMetroPT3
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

-- 7. FactPump
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


-- SELECT 'Schema created successfully!' as status;
-- SELECT 
--     table_name, 
--     (SELECT COUNT(*) FROM information_schema.columns WHERE table_name = t.table_name) as column_count
-- FROM information_schema.tables t
-- WHERE table_schema = 'maintenance'
-- ORDER BY table_name;


-- -- Check for locks
-- SELECT 
--     pid,
--     usename,
--     application_name,
--     state,
--     query
-- FROM pg_stat_activity 
-- WHERE datname = 'predictive_maintenance_dwh' 
-- AND state != 'idle';



-- -- Clear all data but keep structure
-- TRUNCATE TABLE maintenance.FactMetroPT3 CASCADE;
-- TRUNCATE TABLE maintenance.FactScania CASCADE;
-- TRUNCATE TABLE maintenance.FactAI4I CASCADE;
-- TRUNCATE TABLE maintenance.FactPump CASCADE;
-- TRUNCATE TABLE maintenance.DimEquipment CASCADE;
-- TRUNCATE TABLE maintenance.DimTime CASCADE;
-- TRUNCATE TABLE maintenance.DimFailureType CASCADE;