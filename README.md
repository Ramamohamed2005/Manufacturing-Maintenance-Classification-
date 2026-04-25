# Manufacturing Maintenance Classification

Dataset 1: AI4I 2020 Predictive Maintenance Dataset
This is a synthetic dataset created to mirror real industrial predictive maintenance scenarios when real data is hard to obtain . It was published in 2020 and has become a popular benchmark in the field.
Attribute Value
Data Type Synthetic (simulated)
Number of Instances 10,000 rows
Number of Features 14 columns
Time Span Not applicable (synthetic timestamps)

Feature Description Units
UID Unique identifier (1-10,000) -
Product ID Letter (L/M/H) + serial number -
Type Product quality variant (Low-50%, Medium-30%, High-20%) -
Air temperature Random walk, normalized to 300K ±2K Kelvin
Process temperature Air temp + 10K ±1K Kelvin
Rotational speed Derived from 2860W power + noise rpm
Torque Normal distribution around 40 Nm Nm
Tool wear H=5min, M=3min, L=2min added minutes

Failure Modes

The dataset includes 5 independent failure modes:
Code Failure Mode Description Occurrences
TWF Tool Wear Failure Tool fails at 200-240 mins of wear 120 instances
HDF Heat Dissipation Failure Temp difference <8.6K AND speed <1380 rpm 115 instances
PWF Power Failure Power <3500W OR >9000W 95 instances
OSF Overstrain Failure Tool wear × torque exceeds threshold 98 instances
RNF Random Failure 0.1% random chance regardless of parameters 5 instances

Target Variable: Machine failure = 1 if ANY failure mode is true, else 0

Dataset 2: SCANIA Component X Dataset
This is a real-world dataset from SCANIA (Sweden), collected from over 33,000 heavy-duty trucks . It's unique as public real-world industrial data is extremely rare because manufacturers typically keep this data confidential

Attribute Value
Data Type Real-world (SCANIA trucks)
Number of Instances 1,122,452 observations
Number of Features 107 columns
Number of Vehicles 23,550 unique vehicles
Time Series Yes, multivariate time series

The dataset consists of three sources combined:

1. Operational Readouts (train_operational_readouts.csv)
   Feature Description
   vehicle_id Anonymous vehicle identifier
   time_step Duration of Component X usage over lifespan
   14 anonymized attributes Single numerical counters and histograms with multiple bins
   Key characteristic: Vehicles don't have the same sampling frequency
2. Repair Records
   Maintenance and workshop visit information
   Component replacement/failure labeling
   Limited to SCANIA's own workshop network
3. Truck Specifications
   Engine type, weight capacities, dimensions
   Technical details from production system

Dataset 3: MetroPT-3 Dataset
This dataset comes from a metro train's air compressor system in an operational context . It was collected between February and August 2020 from a train's Air Production Unit (APU) at 0.1Hz (one reading every 10 seconds)

Attribute Value
Data Type Real-world (railway compressor)
Number of Instances 1,516,948 data points
Number of Features 15 features
Sampling Rate 0.1Hz (every 10 seconds)
Time Span February - August 2020 (approx. 6 months)

# Sensor Description Units

1 TP2 Pressure on the compressor bar
2 TP3 Pressure at pneumatic panel bar
3 H1 Pressure from cyclonic separator filter discharge bar
4 DV_pressure Pressure drop when towers discharge air bar
5 Reservoirs Downstream pressure of reservoirs bar
6 Motor_current Current of three-phase motor A
7 Oil_temperature Compressor oil temperature °C
8-15 Digital signals COMP, DV electric, TOWERS, MPG, LPS, Pressure Switch, Oil Level, Caudal Impulse binary

Failure Information

The dataset is UNLABELED – but failure reports are provided:
Report Start Time End Time Failure Severity
#1 4/18/2020 4/18/2020 Air leak High stress
#2 5/29/2020 23:30 5/30/2020 6:00 Air Leak High stress
#3 6/5/2020 10:00 6/7/2020 14:30 Air Leak High stress
#4 7/15/2020 14:30 7/15/2020 19:00 Air Leak High stress

Dataset 4: Large Industrial Pump Dataset
Overview

This dataset contains sensor readings from a large-scale industrial pump with 51 sensors recording at 1-minute intervals over 5 months

Attribute Value
Data Type Real-world (industrial pump)
Number of Instances 220,314 readings
Number of Sensors 51 sensors
Sampling Rate 1 minute
Time Span 5 months

Features
Measurement Type Examples
Vibration Various frequency bands
Electrical Operative voltage, current drawn, power factor
Thermal Heat generated, temperature
Mechanical RPM, pressure, flow rates

Label
Value Meaning
0 Pump working as expected (normal)
1 Pump malfunctioning, needs repair

Utility File: Repair_Sensor_Deviations.xlsm

This file helps identify which sensors are most useful by showing deviations from normal operating means during malfunction periods. Sensors with highest "entropy" contribute most to the classification boundary
