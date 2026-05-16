# Predictive Maintenance Modeling Summary

## Overview
- **Data source**: warehouse
- **Total samples**: 1,546,948
- **Failure rate**: 0.67%
- **Best algorithm**: Random Forest

## Model Performance
          algorithm  accuracy  f1_score
      Random Forest  0.993145  0.659386
  Gradient Boosting  0.993339  0.366765
Deep Neural Network  0.993344  0.295181

## Status Distribution
predicted_status
normal                  1525760
failure imminent          20495
maintenance required        693

## Critical Alerts
- **Failure Imminent**: 20,495 measurements
- **Maintenance Required**: 693 measurements
- **Normal**: 1,525,760 measurements

## Generated Files
- `model_metrics.csv` - Performance metrics for all models
- `maintenance_recommendations.csv` - Detailed recommendations for all equipment
- `best_failure_classifier.joblib` - Trained best model for deployment

## Rules Applied
- **Normal**: failure probability < 35%
- **Maintenance required**: 35% ≤ failure probability < 70%
- **Failure imminent**: failure probability ≥ 70%
