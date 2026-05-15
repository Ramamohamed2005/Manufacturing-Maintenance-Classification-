import argparse
import os
from pathlib import Path
from urllib.parse import quote_plus

import joblib
import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
from sklearn.neural_network import MLPClassifier
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


DEFAULT_OUTPUT_DIR = Path("model_outputs")
RANDOM_STATE = 42
FEATURE_COLUMNS = [
    "source_system",
    "temperature_celsius",
    "pressure_bar",
    "rpm",
    "vibration",
    "current_amps",
    "torque_nm",
    "tool_wear_min",
]


def get_database_url() -> str:
    """Build the database URL from environment variables, with local defaults."""
    explicit_url = os.getenv("DATABASE_URL")
    if explicit_url:
        return explicit_url

    user = os.getenv("DB_USER", "postgres")
    password = quote_plus(os.getenv("DB_PASSWORD", "Rana@2019!"))
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")
    database = os.getenv("DB_NAME", "predictive_maintenance_dwh")
    return f"postgresql://{user}:{password}@{host}:{port}/{database}"


def load_warehouse_data(limit: int | None = None) -> pd.DataFrame:
    query = """
        SELECT
            measurement_id,
            equipment_key,
            time_key,
            source_system,
            temperature_celsius,
            pressure_bar,
            rpm,
            vibration,
            current_amps,
            torque_nm,
            tool_wear_min,
            label_binary,
            failure_type
        FROM maintenance.FactSensorReadings
        WHERE label_binary IS NOT NULL
    """

    if limit:
        query += " LIMIT :limit"

    engine = create_engine(get_database_url())
    with engine.connect() as conn:
        return pd.read_sql(text(query), conn, params={"limit": limit} if limit else None)


def build_demo_data(rows: int = 1200) -> pd.DataFrame:
    """Create realistic demo data so the workflow can be tested without the database."""
    rng = np.random.default_rng(RANDOM_STATE)
    source_system = rng.choice(["AI4I", "MetroPT3", "Pump"], size=rows, p=[0.4, 0.25, 0.35])

    data = pd.DataFrame(
        {
            "measurement_id": np.arange(1, rows + 1),
            "equipment_key": rng.integers(1, 45, size=rows),
            "time_key": 2024010100 + np.arange(rows),
            "source_system": source_system,
            "temperature_celsius": rng.normal(62, 18, size=rows),
            "pressure_bar": rng.normal(8.5, 3.2, size=rows),
            "rpm": rng.normal(1550, 420, size=rows),
            "vibration": rng.normal(2.2, 1.1, size=rows),
            "current_amps": rng.normal(5.2, 1.8, size=rows),
            "torque_nm": rng.normal(40, 12, size=rows),
            "tool_wear_min": rng.normal(105, 62, size=rows),
        }
    )

    risk_score = (
        0.035 * (data["temperature_celsius"] - 65)
        + 0.45 * (data["vibration"] - 2.5)
        + 0.003 * (data["tool_wear_min"] - 120)
        + 0.0009 * np.maximum(data["rpm"] - 1900, 0)
        + 0.12 * np.maximum(data["pressure_bar"] - 11, 0)
        + rng.normal(0, 0.65, size=rows)
    )
    probability = 1 / (1 + np.exp(-risk_score))
    data["label_binary"] = (probability >= 0.58).astype(int)
    data["failure_type"] = np.where(data["label_binary"].eq(1), "Demo_Failure", None)
    return data


def load_data(limit: int | None, demo: bool) -> tuple[pd.DataFrame, str]:
    if demo:
        return build_demo_data(), "demo"

    try:
        data = load_warehouse_data(limit=limit)
        if len(data) >= 20 and data["label_binary"].nunique() == 2:
            return data, "warehouse"
        print("Warehouse data was empty or had only one class. Using demo data instead.")
    except Exception as exc:
        print(f"Could not load warehouse data ({exc}). Using demo data instead.")

    return build_demo_data(), "demo"


def make_status_label(failure_probability: float) -> str:
    if failure_probability >= 0.70:
        return "failure imminent"
    if failure_probability >= 0.35:
        return "maintenance required"
    return "normal"


def make_strategy(row: pd.Series) -> str:
    if row["predicted_status"] == "failure imminent":
        return "Stop or isolate equipment, inspect within 24 hours, and prepare spare parts."
    if row["predicted_status"] == "maintenance required":
        return "Schedule preventive maintenance in the next service window and monitor sensor trend."
    return "Continue normal operation with routine monitoring."


def build_preprocessor() -> ColumnTransformer:
    numeric_features = [col for col in FEATURE_COLUMNS if col != "source_system"]
    return ColumnTransformer(
        transformers=[
            (
                "numeric",
                Pipeline(
                    steps=[
                        ("imputer", SimpleImputer(strategy="median")),
                        ("scaler", StandardScaler()),
                    ]
                ),
                numeric_features,
            ),
            (
                "categorical",
                Pipeline(
                    steps=[
                        ("imputer", SimpleImputer(strategy="most_frequent")),
                        ("encoder", OneHotEncoder(handle_unknown="ignore")),
                    ]
                ),
                ["source_system"],
            ),
        ]
    )


def get_models() -> dict[str, Pipeline]:
    preprocessor = build_preprocessor()
    return {
        "deep_neural_network": Pipeline(
            steps=[
                ("preprocessor", preprocessor),
                (
                    "model",
                    MLPClassifier(
                        hidden_layer_sizes=(64, 32, 16),
                        activation="relu",
                        solver="adam",
                        alpha=0.001,
                        learning_rate_init=0.001,
                        max_iter=350,
                        early_stopping=True,
                        validation_fraction=0.15,
                        n_iter_no_change=20,
                        random_state=RANDOM_STATE,
                    ),
                ),
            ]
        ),
        "random_forest": Pipeline(
            steps=[
                ("preprocessor", preprocessor),
                (
                    "model",
                    RandomForestClassifier(
                        n_estimators=250,
                        max_depth=10,
                        min_samples_leaf=3,
                        class_weight="balanced",
                        random_state=RANDOM_STATE,
                        n_jobs=1,
                    ),
                ),
            ]
        ),
        "gradient_boosting": Pipeline(
            steps=[
                ("preprocessor", preprocessor),
                (
                    "model",
                    GradientBoostingClassifier(
                        n_estimators=180,
                        learning_rate=0.06,
                        max_depth=3,
                        random_state=RANDOM_STATE,
                    ),
                ),
            ]
        ),
    }


def train_and_evaluate(data: pd.DataFrame) -> tuple[dict[str, Pipeline], pd.DataFrame, str, pd.DataFrame, pd.Series]:
    data = data.copy()
    data["label_binary"] = data["label_binary"].astype(int)
    X = data[FEATURE_COLUMNS]
    y = data["label_binary"]

    stratify = y if y.nunique() == 2 and y.value_counts().min() >= 2 else None
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.25,
        random_state=RANDOM_STATE,
        stratify=stratify,
    )

    results = []
    fitted_models = {}
    for name, model in get_models().items():
        model.fit(X_train, y_train)
        predictions = model.predict(X_test)
        results.append(
            {
                "algorithm": name,
                "accuracy": accuracy_score(y_test, predictions),
                "f1_failure": f1_score(y_test, predictions, pos_label=1, zero_division=0),
                "confusion_matrix": confusion_matrix(y_test, predictions).tolist(),
                "classification_report": classification_report(
                    y_test,
                    predictions,
                    target_names=["normal", "failure"],
                    zero_division=0,
                    output_dict=True,
                ),
            }
        )
        fitted_models[name] = model

    metrics = pd.DataFrame(results).sort_values(["f1_failure", "accuracy"], ascending=False)
    best_model_name = metrics.iloc[0]["algorithm"]
    return fitted_models, metrics, best_model_name, X_test, y_test


def score_equipment(data: pd.DataFrame, model: Pipeline) -> pd.DataFrame:
    scored = data.copy()
    probabilities = model.predict_proba(scored[FEATURE_COLUMNS])[:, 1]
    scored["failure_probability"] = probabilities
    scored["predicted_status"] = scored["failure_probability"].apply(make_status_label)
    scored["maintenance_strategy"] = scored.apply(make_strategy, axis=1)

    return scored[
        [
            "measurement_id",
            "equipment_key",
            "time_key",
            "source_system",
            "failure_probability",
            "predicted_status",
            "maintenance_strategy",
            "failure_type",
        ]
    ].sort_values("failure_probability", ascending=False)


def save_outputs(
    output_dir: Path,
    models: dict[str, Pipeline],
    metrics: pd.DataFrame,
    best_model_name: str,
    maintenance_plan: pd.DataFrame,
    data_source: str,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    metrics_for_csv = metrics.copy()
    metrics_for_csv["classification_report"] = metrics_for_csv["classification_report"].astype(str)
    metrics_for_csv.to_csv(output_dir / "model_metrics.csv", index=False)

    maintenance_plan.to_csv(output_dir / "maintenance_recommendations.csv", index=False)
    joblib.dump(models[best_model_name], output_dir / "best_failure_classifier.joblib")

    summary = [
        "# Predictive Maintenance Modeling Summary",
        "",
        f"Data source: {data_source}",
        f"Best algorithm: {best_model_name}",
        "",
        "Algorithms implemented:",
        "- Deep Neural Network",
        "- Random Forest Classifier",
        "- Gradient Boosting Classifier",
        "",
        "Status rules:",
        "- Normal: failure probability below 35%",
        "- Maintenance required: failure probability from 35% to below 70%",
        "- Failure imminent: failure probability 70% or higher",
        "",
        "Generated files:",
        "- model_metrics.csv",
        "- maintenance_recommendations.csv",
        "- best_failure_classifier.joblib",
    ]
    (output_dir / "modeling_summary.md").write_text("\n".join(summary), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Train predictive maintenance classification models.")
    parser.add_argument("--limit", type=int, default=None, help="Optional row limit for warehouse training data.")
    parser.add_argument("--demo", action="store_true", help="Use generated demo data instead of the database.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="Folder for model outputs.")
    args = parser.parse_args()

    data, data_source = load_data(limit=args.limit, demo=args.demo)
    models, metrics, best_model_name, _, _ = train_and_evaluate(data)
    maintenance_plan = score_equipment(data, models[best_model_name])
    save_outputs(args.output_dir, models, metrics, best_model_name, maintenance_plan, data_source)

    print("Predictive maintenance modeling complete.")
    print(f"Data source: {data_source}")
    print(f"Best algorithm: {best_model_name}")
    print(metrics[["algorithm", "accuracy", "f1_failure"]].to_string(index=False))
    print(f"Outputs written to: {args.output_dir.resolve()}")


if __name__ == "__main__":
    main()
