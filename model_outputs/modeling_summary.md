# Predictive Maintenance Modeling Summary

Data source: demo
Best algorithm: random_forest

Algorithms implemented:
- Deep Neural Network
- Random Forest Classifier
- Gradient Boosting Classifier

Status rules:
- Normal: failure probability below 35%
- Maintenance required: failure probability from 35% to below 70%
- Failure imminent: failure probability 70% or higher

Generated files:
- model_metrics.csv
- maintenance_recommendations.csv
- best_failure_classifier.joblib