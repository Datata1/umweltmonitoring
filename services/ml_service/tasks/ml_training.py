# tasks/ml_training.py
import os
import pandas as pd
import joblib
import lightgbm as lgb 
from sklearn.experimental import enable_halving_search_cv
from sklearn.model_selection import GridSearchCV, TimeSeriesSplit, HalvingGridSearchCV
from prefect import task
from typing import Dict, Any, Tuple, Union, Optional


@task(name="Train Single Forecasting Model with LGBM", log_prints=True) # Name angepasst
def train_single_model(
    X_train_df: pd.DataFrame,
    y_train_series: pd.Series,
    horizon_hours: int,
    base_save_path: str,
    unvalidated: Optional[bool] = True,
    tscv_n_splits: Optional[int] = 5
) -> Union[Tuple[Dict[str, Any], Union[lgb.LGBMRegressor, None]], Dict[str, Any]]:
    """
    Trainiert ein einzelnes LGBM-Modell für einen spezifischen Vorhersagehorizont,
    speichert es und gibt Metriken zurück.
    """
    print(f"Starte LGBM-Training für Horizont: {horizon_hours}h...")
    print(f"Form von X_train_df: {X_train_df.shape}, Form von y_train_series: {y_train_series.shape}")
    print(f"Kreuzvalidierung wird durchgeführt mit `TimeSeriesSplit`, für {tscv_n_splits} Splits")

    tscv = TimeSeriesSplit(n_splits=tscv_n_splits)

    if X_train_df.empty or y_train_series.empty:
        print(f"WARNUNG: Leere Trainingsdaten für Horizont {horizon_hours}h. Überspringe Training.")
        
        if unvalidated:
            return {
                "horizon": horizon_hours,
                "model_path": None,
                "rmse_fit": None,
                "n_samples_trained": 0,
                "error": "Empty training data"
            }, None
        else:
            return {
                "horizon": horizon_hours,
                "model_path": None,
                "rmse_fit": None,
                "n_samples_trained": 0,
                "error": "Empty training data"
            }

    # 1. Modellwahl und Instanziierung: LGBMRegressor
    model = lgb.LGBMRegressor(random_state=42)

    param_grid = {
        "n_estimatiors": [70, 50, 40, 60],
        "learning_rate": [0.05, 0.03, 0.06, 0.04],
        "num_leaves": [15, 10, 5, 20],
        "max_depth": [5, 3, 1, 7]
    }

    gs = HalvingGridSearchCV(
        estimator=model,
        param_grid=param_grid,
        cv=tscv,
        scoring="neg_mean_squared_error",
        n_jobs=-1,
        verbose=1
    )

    try:
        # 2. Modelltraining
        gs.fit(X_train_df, y_train_series)

        print(f"Beste Parameter: {gs.best_params_}")

        best_est = gs.best_estimator_

        # 5. Modell speichern
        os.makedirs(base_save_path, exist_ok=True)
        model_filename = f"temp_forecast_lgbm_model_h{horizon_hours}.joblib" 
        model_full_path = os.path.join(base_save_path, model_filename)
        joblib.dump(best_est, model_full_path)
        print(f"Modell gespeichert unter: {model_full_path}")

        if unvalidated:
            return {
                "horizon": horizon_hours,
                "model_path": model_full_path,
                "rmse_fit": gs.best_score_,
                "n_samples_trained": len(X_train_df),
                "error": None
            }, best_est
        else:
            return {
                "horizon": horizon_hours,
                "model_path": model_full_path,
                "rmse_fit": gs.best_score_,
                "n_samples_trained": len(X_train_df),
                "error": None
            }
    except Exception as e:
        print(f"FEHLER beim Training/Speichern des LGBM-Modells für Horizont {horizon_hours}h: {e}")
        # Detailliertere Fehlerausgabe für LGBM-spezifische Probleme
        if isinstance(e, lgb.basic.LightGBMError):
            print(f"LightGBM spezifischer Fehler: {e}")

        if unvalidated:
            return {
                "horizon": horizon_hours,
                "model_path": None,
                "rmse_fit": None,
                "n_samples_trained": len(X_train_df) if 'X_train_df' in locals() else 0,
                "error": str(e)
            }, None
        else:
            return {
                "horizon": horizon_hours,
                "model_path": model_full_path,
                "rmse_fit": gs.best_score_,
                "n_samples_trained": len(X_train_df),
                "error": None
            }

