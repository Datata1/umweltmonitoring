# tasks/ml_training.py
import os
import pandas as pd
import numpy as np
import joblib
import lightgbm as lgb 
from sklearn.metrics import mean_squared_error, mean_absolute_error
from prefect import task
from typing import Dict, Any

@task(name="Train Single Forecasting Model with LGBM") # Name angepasst
def train_single_model(
    X_train_df: pd.DataFrame,
    y_train_series: pd.Series,
    horizon_hours: int,
    base_save_path: str
) -> Dict[str, Any]:
    """
    Trainiert ein einzelnes LGBM-Modell für einen spezifischen Vorhersagehorizont,
    speichert es und gibt Metriken zurück.
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

    # 1. Modellwahl und Instanziierung: LGBMRegressor
    model = lgb.LGBMRegressor(
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

    try:
        # 2. Modelltraining
        model.fit(X_train_df, y_train_series)

        # 3. Vorhersagen auf den Trainingsdaten machen (um "Fit"-Metriken zu erhalten)
        y_pred_fit = model.predict(X_train_df)

        # 4. Metriken berechnen
        rmse_fit = np.sqrt(mean_squared_error(y_train_series, y_pred_fit))
        mae_fit = mean_absolute_error(y_train_series, y_pred_fit)

        print(f"LGBM-Modell für Horizont {horizon_hours}h trainiert. RMSE (Fit): {rmse_fit:.4f}, MAE (Fit): {mae_fit:.4f}")

        # 5. Modell speichern
        os.makedirs(base_save_path, exist_ok=True)
        model_filename = f"temp_forecast_lgbm_model_h{horizon_hours}.joblib" 
        model_full_path = os.path.join(base_save_path, model_filename)
        joblib.dump(model, model_full_path)
        print(f"Modell gespeichert unter: {model_full_path}")

        return {
            "horizon": horizon_hours,
            "model_path": model_full_path,
            "rmse_fit": rmse_fit,
            "mae_fit": mae_fit,
            "n_samples_trained": len(X_train_df),
            "error": None
        }
    except Exception as e:
        print(f"FEHLER beim Training/Speichern des LGBM-Modells für Horizont {horizon_hours}h: {e}")
        # Detailliertere Fehlerausgabe für LGBM-spezifische Probleme
        if isinstance(e, lgb.basic.LightGBMError):
            print(f"LightGBM spezifischer Fehler: {e}")
        return {
            "horizon": horizon_hours,
            "model_path": None,
            "rmse_fit": None,
            "mae_fit": None,
            "n_samples_trained": len(X_train_df) if 'X_train_df' in locals() else 0,
            "error": str(e)
        }