import pandas as pd
import numpy as np
from prefect import task
from typing import Dict # Für den Rückgabetyp

from utils.feature_enhancer import get_solar_features, get_weather_features

FORECAST_TIME_WINDOW = 48
LATITUDE = 52.019364
LONGITUDE = -1.73893
TIMEZONE = "Europe/London" 

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

    # --- SCHRITT 2: EXTERNE FEATURES HOLEN (mit dem jetzt korrekten Zeitindex) ---
    solar_features = get_solar_features(df.index)
    weather_features = get_weather_features(df.index.min().strftime('%Y-%m-%d'), df.index.max().strftime('%Y-%m-%d'))

    # --- SCHRITT 3: ALLES VERBINDEN ---
    df = df.join(solar_features)
    if weather_features is not None:
        df = df.join(weather_features)

    # --- 1. Sin/Cos Zeit-Features ---
    df['hour_sin'] = np.sin(2 * np.pi * df.index.hour / 24.0)
    df['hour_cos'] = np.cos(2 * np.pi * df.index.hour / 24.0)

    # --- 2. Lag Features der Temperatur ---
    lags_to_create = [1, 2, 3, 24] 
    for lag in lags_to_create:
        df[f'temp_lag_{lag}h'] = df['temperatur'].shift(lag)

    # --- 3. Rolling Window Features ---
    windows_to_create = [3, 6, 24, 48, 72, 168] 
    for window in windows_to_create:
        df[f'temp_roll_mean_{window}h'] = df['temperatur'].shift(1).rolling(window=window, min_periods=1).mean()
        df[f'temp_roll_std_{window}h'] = df['temperatur'].shift(1).rolling(window=window, min_periods=1).std()
    
    # Optional: Temperaturdifferenzen
    df['temp_diff_1h'] = df['temperatur'].shift(1).diff(periods=1)
    df['temp_diff_3h'] = df['temperatur'].shift(1).diff(periods=3)
    df['temp_diff_6h'] = df['temperatur'].shift(1).diff(periods=6)
    df['temp_diff_12h'] = df['temperatur'].shift(1).diff(periods=12) 
    df['temp_diff_24h'] = df['temperatur'].shift(1).diff(periods=24)

    feature_cols_for_lags = ['weather_temp', 'weather_radiation_ghi', 'weather_cloud_cover']
    lags_to_create = [1, 2, 3, 24] 
    for col in feature_cols_for_lags:
        if col in df.columns:
            for lag in lags_to_create:
                df[f'{col}_lag_{lag}h'] = df[col].shift(lag) 


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

    past_start = X.index.max() - pd.Timedelta(hours=FORECAST_TIME_WINDOW)
    X_train = X[X.index < past_start].copy()
    X_val = X[X.index >= past_start].copy()

    Y_targets_train = Y_targets[Y_targets.index < past_start].copy()

    return {
        "X_train": X_train,
        "X_val": X_val,
        "X": X,
        "Y_targets_train": Y_targets_train,
        "Y_targets": Y_targets,
        "original_features_df": df_processed[feature_columns + target_columns]
    }