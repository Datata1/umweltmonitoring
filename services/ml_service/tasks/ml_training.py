# tasks/ml_training.py
import os
import time  
import pandas as pd
import numpy as np #
import joblib
import lightgbm as lgb
from sklearn.base import clone
from sklearn.experimental import enable_halving_search_cv
from sklearn.metrics import mean_absolute_error, mean_absolute_percentage_error, r2_score
from sklearn.model_selection import GridSearchCV, TimeSeriesSplit
from prefect import task
from typing import Dict, Any, Tuple, Union, Optional


@task(name="Train Single Forecasting Model with LGBM", log_prints=True, retries=2)
def train_single_model(
    X_train_df: pd.DataFrame,
    y_train_series: pd.Series,
    horizon_hours: int,
    base_save_path: str,
    return_model_object: Optional[bool] = True, 
    tscv_n_splits: Optional[int] = 3
) -> Union[Tuple[Dict[str, Any], lgb.LGBMRegressor], Dict[str, Any]]:
    """
    Trainiert ein einzelnes LGBM-Modell, berechnet alle relevanten Metriken
    und gibt ein datenbankfertiges Dictionary zurück.
    """
    print(f"Starte LGBM-Training für Horizont: {horizon_hours}h...")
    print(f"Form von X_train_df: {X_train_df.shape}, Form von y_train_series: {y_train_series.shape}")
    print(f"Kreuzvalidierung wird durchgeführt mit `TimeSeriesSplit`, für {tscv_n_splits} Splits")

    model = lgb.LGBMRegressor()
    tscv = TimeSeriesSplit(n_splits=tscv_n_splits)

    param_grid = {
        "n_estimators": [30],
        "learning_rate": [0.05],
        "num_leaves": [5],
        "max_depth": [3]
    }

    scoring_metrics = {
        'neg_rmse': 'neg_root_mean_squared_error',
        'neg_mae': 'neg_mean_absolute_error',
        'neg_mape': 'neg_mean_absolute_percentage_error',
        'r2': 'r2'
    }

    gs = GridSearchCV(
        estimator=model,
        param_grid=param_grid,
        cv=tscv,
        scoring=scoring_metrics, 
        refit='neg_rmse', 
        n_jobs=-1,
        verbose=1
    )

    try:
        start_time = time.time()
        
        gs.fit(X_train_df, y_train_series)
        
        end_time = time.time()
        training_duration = round(end_time - start_time, 2)

        print(f"Beste Parameter für Horizont {horizon_hours}h: {gs.best_params_}")

        best_estimator = gs.best_estimator_
        val_rmse = float(-gs.best_score_)

        all_true_values = []
        all_predictions = []
        
        for train_idx, test_idx in tscv.split(X_train_df):
            # Erstelle eine saubere Kopie des besten Modells
            cv_model = clone(best_estimator)
            
            # Trainiere das Modell nur auf dem Trainings-Split dieses Folds
            cv_model.fit(X_train_df.iloc[train_idx], y_train_series.iloc[train_idx])
            
            # Mache Vorhersagen für den Test-Split
            preds = cv_model.predict(X_train_df.iloc[test_idx])
            
            all_predictions.extend(preds)
            all_true_values.extend(y_train_series.iloc[test_idx])
        
        val_mae = float(mean_absolute_error(all_true_values, all_predictions))
        val_mape = float(mean_absolute_percentage_error(all_true_values, all_predictions))
        val_r2 = float(r2_score(all_true_values, all_predictions))

        print(f"Horizont {horizon_hours}h | RMSE: {val_rmse:.3f}, MAE: {val_mae:.3f}, MAPE: {val_mape:.3f}, R2: {val_r2:.3f}")

        # Prüfe die reparierte Logik
        if val_mae > val_rmse:
             print(f"WARNUNG: MAE ({val_mae:.3f}) ist immer noch größer als RMSE ({val_rmse:.3f}). Prüfe die Datenqualität.")

        os.makedirs(base_save_path, exist_ok=True)
        model_filename = f"temp_forecast_lgbm_model_h{horizon_hours}.joblib" 
        model_full_path = os.path.join(base_save_path, model_filename)
        joblib.dump(best_estimator, model_full_path)
        print(f"Modell gespeichert unter: {model_full_path}")

        result_dict = {
            "model_name": f"temperatur-vorhersage-{horizon_hours}h",
            "forecast_horizon_hours": horizon_hours,
            "model_path": model_full_path,
            "training_duration_seconds": training_duration,
            "val_mae": val_mae,
            "val_rmse": val_rmse,
            "val_mape": val_mape,
            "val_r2": val_r2,
            "hyperparameters": gs.best_params_,
            "n_samples_trained": len(X_train_df),
            "error": None
        }

        if return_model_object:
            return result_dict, best_estimator
        else:
            return result_dict

    except Exception as e:
        print(f"FEHLER beim Training des Modells für Horizont {horizon_hours}h: {e}")
        error_dict = {
            "forecast_horizon_hours": horizon_hours, 
            "error": str(e)
        }
        if return_model_object:
            return error_dict, None
        else:
            return error_dict
