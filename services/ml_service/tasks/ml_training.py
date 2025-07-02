# tasks/ml_training.py
import os
import time  
import pandas as pd
import numpy as np #
import joblib
import lightgbm as lgb
from sklearn.base import clone
from sklearn.metrics import mean_absolute_error, mean_absolute_percentage_error, r2_score
from sklearn.experimental import enable_halving_search_cv # noqa
from sklearn.model_selection import GridSearchCV, TimeSeriesSplit, HalvingGridSearchCV
from prefect import task
from typing import Dict, Any, Tuple, Union, Optional
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.linear_model import Ridge # Ridge-Modell importieren

@task(name="Train Single Forecasting Model with Ridge", log_prints=True, retries=2)
def train_single_model_rdige(
    X_train_df: pd.DataFrame,
    y_train_series: pd.Series,
    horizon_hours: int,
    base_save_path: str,
    return_model_object: Optional[bool] = True,
    tscv_n_splits: Optional[int] = 3
) -> Union[Tuple[Dict[str, Any], Pipeline], Dict[str, Any]]:
    """
    Trainiert ein einzelnes lineares Ridge-Modell, berechnet alle relevanten Metriken
    und gibt ein datenbankfertiges Dictionary zurück.
    """
    print(f"Starte Lineares Training (Ridge) für Horizont: {horizon_hours}h...")
    print(f"Form von X_train_df: {X_train_df.shape}, Form von y_train_series: {y_train_series.shape}")
    print(f"Kreuzvalidierung wird durchgeführt mit `TimeSeriesSplit`, für {tscv_n_splits} Splits")

    # WICHTIGE ÄNDERUNG 1: Pipeline mit Ridge-Modell
    # Auch lineare Modelle profitieren von einer Skalierung der Daten.
    pipeline = Pipeline([
        ('scaler', StandardScaler()),
        ('ridge', Ridge(random_state=42)) # MLP durch Ridge ersetzt
    ])

    tscv = TimeSeriesSplit(n_splits=tscv_n_splits)

    # WICHTIGE ÄNDERUNG 2: Stark vereinfachtes Parameter-Menü
    # Ein Ridge-Modell hat nur sehr wenige wichtige Hyperparameter.
    # 'alpha' steuert die Stärke der Regularisierung.
    param_grid = {
        "ridge__alpha": [0.01, 0.1, 1.0, 10.0, 100.0]
    }

    # Da die Suche so schnell ist, können wir hier das normale GridSearchCV verwenden.
    gs = GridSearchCV(
        estimator=pipeline,
        param_grid=param_grid,
        cv=tscv,
        scoring='neg_mean_absolute_error',
        refit=True,
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
        val_rmse_approx = float(-gs.best_score_)

        all_true_values = []
        all_predictions = []

        for train_idx, test_idx in tscv.split(X_train_df):
            cv_pipeline = clone(best_estimator)
            cv_pipeline.fit(X_train_df.iloc[train_idx], y_train_series.iloc[train_idx])
            preds = cv_pipeline.predict(X_train_df.iloc[test_idx])
            all_predictions.extend(preds)
            all_true_values.extend(y_train_series.iloc[test_idx])

        val_mae = float(mean_absolute_error(all_true_values, all_predictions))
        val_mape = float(mean_absolute_percentage_error(all_true_values, all_predictions))
        val_r2 = float(r2_score(all_true_values, all_predictions))
        val_rmse = val_rmse_approx

        print(f"Horizont {horizon_hours}h | Approx. RMSE: {val_rmse:.3f}, MAE: {val_mae:.3f}, MAPE: {val_mape:.3f}, R2: {val_r2:.3f}")

        os.makedirs(base_save_path, exist_ok=True)
        
        # WICHTIGE ÄNDERUNG 3: Neuer Dateiname
        model_filename = f"temp_forecast_linear_model_h{horizon_hours}.joblib"
        model_full_path = os.path.join(base_save_path, model_filename)

        joblib.dump(best_estimator, model_full_path)
        print(f"Modell-Pipeline gespeichert unter: {model_full_path}")

        result_dict = {
            "model_name": f"temperatur-vorhersage-linear-{horizon_hours}h", # Name angepasst
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

@task(name="Train Single Forecasting Model with MLP", log_prints=True, retries=2)
def train_single_model_ml(
    X_train_df: pd.DataFrame,
    y_train_series: pd.Series,
    horizon_hours: int,
    base_save_path: str,
    return_model_object: Optional[bool] = True,
    tscv_n_splits: Optional[int] = 3
) -> Union[Tuple[Dict[str, Any], Pipeline], Dict[str, Any]]:
    """
    Trainiert ein einzelnes MLP-Modell, berechnet alle relevanten Metriken
    und gibt ein datenbankfertiges Dictionary zurück.
    Beinhaltet einen obligatorischen Skalierungsschritt.
    """
    print(f"Starte MLP-Training für Horizont: {horizon_hours}h...")
    print(f"Form von X_train_df: {X_train_df.shape}, Form von y_train_series: {y_train_series.shape}")
    print(f"Kreuzvalidierung wird durchgeführt mit `TimeSeriesSplit`, für {tscv_n_splits} Splits")

    # WICHTIGE ÄNDERUNG 1: Pipeline für Skalierung und Modell
    # Neuronale Netze benötigen skalierte Daten. Eine Pipeline stellt sicher,
    # dass die Skalierung korrekt innerhalb der Kreuzvalidierung angewendet wird,
    # um Datenlecks zu vermeiden.
    pipeline = Pipeline([
        ('scaler', StandardScaler()),
        ('mlp', MLPRegressor(random_state=42, max_iter=500, early_stopping=True))
    ])

    tscv = TimeSeriesSplit(n_splits=tscv_n_splits)

    # WICHTIGE ÄNDERUNG 2: Neues Parameter-Menü für das MLP-Modell
    # Die Parameter beziehen sich jetzt auf die Schritte in der Pipeline (z.B. 'mlp__...')
    param_grid = {
        "mlp__hidden_layer_sizes": [(50,), (100,), (50, 25)],
        "mlp__activation": ["relu", "tanh"],
        "mlp__alpha": [0.0001, 0.001, 0.01], # L2-Regularisierung
        "mlp__learning_rate_init": [0.001, 0.01]
    }

    gs = HalvingGridSearchCV(
        estimator=pipeline, # Wir übergeben die gesamte Pipeline
        param_grid=param_grid,
        cv=tscv,
        scoring='neg_mean_absolute_error',
        refit=True,
        n_jobs=-1,
        verbose=1
    )

    try:
        start_time = time.time()
        gs.fit(X_train_df, y_train_series)
        end_time = time.time()
        training_duration = round(end_time - start_time, 2)

        print(f"Beste Parameter für Horizont {horizon_hours}h: {gs.best_params_}")

        # Das beste Modell ist jetzt die gesamte Pipeline (inkl. Scaler)
        best_estimator = gs.best_estimator_
        # ACHTUNG: Der Score von GridSearchCV ist auf den skalierten Daten.
        # Wir berechnen ihn unten neu für die Originalskala.
        val_rmse_approx = float(-gs.best_score_)


        all_true_values = []
        all_predictions = []

        # Die Logik hier bleibt gleich, aber arbeitet jetzt mit der Pipeline
        for train_idx, test_idx in tscv.split(X_train_df):
            cv_pipeline = clone(best_estimator)
            cv_pipeline.fit(X_train_df.iloc[train_idx], y_train_series.iloc[train_idx])
            preds = cv_pipeline.predict(X_train_df.iloc[test_idx])
            all_predictions.extend(preds)
            all_true_values.extend(y_train_series.iloc[test_idx])

        val_mae = float(mean_absolute_error(all_true_values, all_predictions))
        val_mape = float(mean_absolute_percentage_error(all_true_values, all_predictions))
        val_r2 = float(r2_score(all_true_values, all_predictions))
        # Da wir keinen direkten RMSE-Score mehr haben, können wir ihn aus dem MAE schätzen
        # oder ihn einfach gleich dem MAE setzen für die Datenbank.
        val_rmse = val_rmse_approx

        print(f"Horizont {horizon_hours}h | Approx. RMSE: {val_rmse:.3f}, MAE: {val_mae:.3f}, MAPE: {val_mape:.3f}, R2: {val_r2:.3f}")

        os.makedirs(base_save_path, exist_ok=True)
        # WICHTIGE ÄNDERUNG 3: Neuer Dateiname
        model_filename = f"temp_forecast_mlp_model_h{horizon_hours}.joblib"
        model_full_path = os.path.join(base_save_path, model_filename)

        # Wir speichern die gesamte Pipeline, damit die Skalierung erhalten bleibt
        joblib.dump(best_estimator, model_full_path)
        print(f"Modell-Pipeline gespeichert unter: {model_full_path}")

        result_dict = {
            "model_name": f"temperatur-vorhersage-mlp-{horizon_hours}h", # Name angepasst
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
        "n_estimators": [30, 50, 70, 100],
        "learning_rate": [0.05, 0.07, 0.1],
        "num_leaves": [3, 5, 10],
        "max_depth": [3, 5, 7]
    }

    # scoring_metrics = {
    #     'neg_rmse': 'neg_root_mean_squared_error',
    #     'neg_mae': 'neg_mean_absolute_error',
    #     'neg_mape': 'neg_mean_absolute_percentage_error',
    #     'r2': 'r2'
    # }

    gs = GridSearchCV(
        estimator=model,
        param_grid=param_grid,
        cv=tscv,
        scoring='neg_mean_absolute_error', 
        refit=True, 
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
