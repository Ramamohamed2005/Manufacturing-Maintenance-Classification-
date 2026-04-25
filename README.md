# Manufacturing Maintenance Classification: Dataset Collection

This repository contains a comprehensive suite of industrial datasets designed for predictive maintenance, anomaly detection, and classification modeling. These datasets range from synthetic benchmarks to complex, real-world multivariate time series.

---

## 1. AI4I 2020 Predictive Maintenance Dataset
*A synthetic benchmark designed to mirror complex industrial failure scenarios.*

| Attribute | Value |
| :--- | :--- |
| **Data Type** | Synthetic (Simulated) |
| **Instances** | 10,000 |
| **Features** | 14 |

### Failure Modes
| Code | Failure Mode | Description | Occurrences |
| :--- | :--- | :--- | :--- |
| **TWF** | Tool Wear Failure | Wear at 200–240 mins | 120 |
| **HDF** | Heat Dissipation | Temp diff < 8.6K AND speed < 1380 rpm | 115 |
| **PWF** | Power Failure | Power < 3500W OR > 9000W | 95 |
| **OSF** | Overstrain Failure | Wear $\times$ torque threshold exceeded | 98 |
| **RNF** | Random Failure | 0.1% random occurrence | 5 |

> **Target:** `Machine failure` (1 if any failure mode is active, else 0).

---

## 2. SCANIA Component X Dataset
*Real-world industrial data from over 33,000 heavy-duty trucks.*

| Attribute | Value |
| :--- | :--- |
| **Data Type** | Real-world (Time-series) |
| **Instances** | 1,122,452 |
| **Vehicles** | 23,550 |
| **Features** | 107 |

### Dataset Composition
* **Operational Readouts:** Anonymized counters and histogram bins (varying sampling frequencies).
* **Repair Records:** Workshop visit logs and component failure labels.
* **Truck Specs:** Technical metadata (engine type, weight, dimensions).

---

## 3. MetroPT-3 Dataset
*Real-world Air Production Unit (APU) sensor data from a railway metro train.*

| Attribute | Value |
| :--- | :--- |
| **Data Type** | Real-world (Railway) |
| **Instances** | 1,516,948 |
| **Sampling Rate** | 0.1Hz (every 10 seconds) |

### Sensor Suite
* **Pressure:** TP2, TP3, H1, DV_pressure, Reservoirs.
* **Electrical/Thermal:** Motor current, Oil temperature.
* **Digital:** 8 binary signals (Pressure Switch, Oil Level, etc.).

> **Failure Reporting:** Unlabeled data; failures provided via external incident reports (#1–#4, ranging from April to July 2020).

---

## 4. Large Industrial Pump Dataset
*Operational sensor monitoring for large-scale mechanical pumping systems.*

| Attribute | Value |
| :--- | :--- |
| **Instances** | 220,314 |
| **Sensors** | 51 |
| **Sampling Rate** | 1 minute |

* **Measured Metrics:** Vibration (frequency bands), Electrical (voltage/power factor), Thermal (heat), and Mechanical (RPM, pressure, flow).
* **Target Label:** 0 (Normal) vs. 1 (Malfunction).

## Analytical Utilities
### `Repair_Sensor_Deviations.xlsm`
A utility for feature selection and importance. It identifies which sensors provide the highest **entropy** (deviation from the operating mean) during malfunction periods, effectively highlighting key predictors for the classification boundary.
