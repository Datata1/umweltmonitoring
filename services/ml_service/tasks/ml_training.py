# tasks/ml_training.py
import os
import pandas as pd
import numpy as np
import joblib
import lightgbm as lgb 
from sklearn.metrics import mean_squared_error, mean_absolute_error
from sklearn.model_selection import GridSearchCV
from prefect import task
from typing import Dict, Any

@task(name="Train Single Forecasting Model with LGBM")
def train_single_model(
    X_train_df: pd.DataFrame,
    y_train_series: pd.Series,
    horizon_hours: int,
    base_save_path: str,
    tune_hyperparameters: bool = False
) -> Dict[str, Any]:
    """
    Trainiert ein einzelnes LGBM-Modell für einen spezifischen Vorhersagehorizont,
    optional mit Hyperparameter-Tuning, speichert es und gibt Metriken zurück.
    """
    print(f"Starte LGBM-Training für Horizont: {horizon_hours}h...")
    print(f"Form von X_train_df: {X_train_df.shape}, Form von y_train_series: {y_train_series.shape}")

    if X_train_df.empty or y_train_series.empty:
        print(f"WARNUNG: Leere Trainingsdaten für Horizont {horizon_hours}h. Überspringe Training.")
        return {
            "horizon": horizon_hours,
            "model_path": None,
            "rmse_fit": None,
            "mae_fit": None,
            "n_samples_trained": 0,
            "error": "Empty training data"
        }

    # Optional: Hyperparameter-Tuning
    if tune_hyperparameters:
        print("Führe GridSearchCV für Hyperparameter-Tuning durch...")
        param_grid = {
            'n_estimators': [50, 100],
            'max_depth': [3, 5],
            'learning_rate': [0.05, 0.1]
        }
        model = GridSearchCV(
            estimator=lgb.LGBMRegressor(random_state=42),
            param_grid=param_grid,
            scoring='neg_mean_absolute_error',
            cv=3,
            verbose=0
        )
        model.fit(X_train_df, y_train_series)
        best_model = model.best_estimator_
        print(f"Beste Parameter: {model.best_params_}")
    else:
        best_model = lgb.LGBMRegressor(
            n_estimators=70,
            learning_rate=0.05,
            num_leaves=15,
            max_depth=5,
            random_state=42,
            n_jobs=-1,
            colsample_bytree=0.7,
            subsample=0.7,
            min_child_samples=5,
        )
        best_model.fit(X_train_df, y_train_series)

    # Fit-Metriken berechnen
    y_pred_fit = best_model.predict(X_train_df)
    rmse_fit = np.sqrt(mean_squared_error(y_train_series, y_pred_fit))
    mae_fit = mean_absolute_error(y_train_series, y_pred_fit)

    # Modell speichern
    model_path = os.path.join(base_save_path, f"model_h{horizon_hours}.pkl")
    joblib.dump(best_model, model_path)

    print(f"LGBM-Modell für Horizont {horizon_hours}h trainiert und gespeichert unter: {model_path}")

    return {
        "horizon": horizon_hours,
        "model_path": model_path,
        "rmse_fit": rmse_fit,
        "mae_fit": mae_fit,
        "n_samples_trained": len(X_train_df),
        "error": None
    }
