import pandas as pd
import numpy as np
from prefect import task
from typing import Dict # Für den Rückgabetyp

FORECAST_TIME_WINDOW = 48

@task(name="Create ML Features and Targets")
def create_ml_features(df_hourly: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    """
    Erstellt Features (Lags, Rolling, Sin/Cos) und Target-Variablen 
    für das Training von Zeitreihenmodellen.

    Args:
        df_hourly: DataFrame mit stündlicher 'temperatur' und DatetimeIndex.

    Returns:
        Ein Dictionary mit 'X' (Feature DataFrame) und 'Y_targets' (Target DataFrame).
    """
    if not isinstance(df_hourly.index, pd.DatetimeIndex):
        raise ValueError("df_hourly muss einen DatetimeIndex haben.")
    if 'temperatur' not in df_hourly.columns:
        raise ValueError("df_hourly muss eine 'temperatur'-Spalte enthalten.")

    df = df_hourly.copy()

    # --- 1. Sin/Cos Zeit-Features ---
    df['hour_sin'] = np.sin(2 * np.pi * df.index.hour / 24.0)
    df['hour_cos'] = np.cos(2 * np.pi * df.index.hour / 24.0)

    # --- 2. Lag Features der Temperatur ---
    lags_to_create = [1, 2, 3, 24] 
    for lag in lags_to_create:
        df[f'temp_lag_{lag}h'] = df['temperatur'].shift(lag)

    # --- 3. Rolling Window Features ---
    windows_to_create = [3, 6, 12] 
    for window in windows_to_create:
        df[f'temp_roll_mean_{window}h'] = df['temperatur'].shift(1).rolling(window=window, min_periods=1).mean()
        df[f'temp_roll_std_{window}h'] = df['temperatur'].shift(1).rolling(window=window, min_periods=1).std()
    
    # Optional: Temperaturdifferenzen
    df['temp_diff_1h'] = df['temperatur'].shift(1).diff(periods=1) 
    df['temp_diff_24h'] = df['temperatur'].shift(1).diff(periods=24) 


    # --- 4. Target-Variablen erstellen (für t+1h bis t+48h) ---
    for h in range(1, FORECAST_TIME_WINDOW + 1):
        df[f'target_temp_plus_{h}h'] = df['temperatur'].shift(-h)

    # --- 5. Spaltenlisten definieren und NaNs entfernen ---
    feature_columns = [col for col in df.columns if not col.startswith('target_') and col != 'temperatur']
    
    target_columns = [f'target_temp_plus_{h}h' for h in range(1, FORECAST_TIME_WINDOW + 1)]

    df_processed = df.dropna()

    X = df_processed[feature_columns]
    Y_targets = df_processed[target_columns]
    
    if X.empty or Y_targets.empty:
        print("WARNUNG: Nach Feature Engineering und NaN-Entfernung sind keine Daten mehr übrig!")
        print(f"Ursprüngliche Länge df_hourly: {len(df_hourly)}, Länge df_processed: {len(df_processed)}")

    
    print(f"Feature Engineering abgeschlossen. X shape: {X.shape}, Y_targets shape: {Y_targets.shape}")

    return {"X": X, "Y_targets": Y_targets, "original_features_df": df_processed[feature_columns + target_columns]}