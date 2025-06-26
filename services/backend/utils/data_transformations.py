# utils/data_transformations.py

import pandas as pd
import numpy as np
from typing import Dict

# Importiere die Helferfunktionen, die du bereits hast
from .feature_enhancer import get_solar_features, get_weather_features

TIMEZONE = "Europe/London" 

def create_features_for_prediction(historical_df: pd.DataFrame) -> pd.DataFrame:
    """
    Nimmt einen DataFrame mit historischen Daten, wendet das vollständige
    Feature-Engineering (inkl. externer Daten) an und gibt die Features
    für den letzten verfügbaren Zeitpunkt zurück.

    Args:
        historical_df: DataFrame mit stündlicher 'temperatur' und einem DatetimeIndex.

    Returns:
        Ein DataFrame mit einer einzigen Zeile, die alle Features für die Vorhersage enthält.
    """
    df = historical_df.copy()

    # --- SCHRITT 1: ZEITZONE KORRIGIEREN (Genau wie beim Training) ---
    if df.index.tz is None:
        df.index = df.index.tz_localize('UTC').tz_convert(TIMEZONE)
    else:
        df.index = df.index.tz_convert(TIMEZONE)

    # --- SCHRITT 2: EXTERNE FEATURES HOLEN ---
    solar_features = get_solar_features(df.index)
    weather_features = get_weather_features(df.index.min().strftime('%Y-%m-%d'), df.index.max().strftime('%Y-%m-%d'))

    # --- SCHRITT 3: ALLES VERBINDEN ---
    df = df.join(solar_features)
    if weather_features is not None:
        df = df.join(weather_features)
    
    df['hour_sin'] = np.sin(2 * np.pi * df.index.hour / 24.0)
    df['hour_cos'] = np.cos(2 * np.pi * df.index.hour / 24.0)

    lags_to_create = [1, 2, 3, 24] 
    for lag in lags_to_create:
        df[f'temp_lag_{lag}h'] = df['temperatur'].shift(lag)

    windows_to_create = [3, 6, 24, 48, 72, 168] 
    for window in windows_to_create:
        df[f'temp_roll_mean_{window}h'] = df['temperatur'].shift(1).rolling(window=window).mean()
        df[f'temp_roll_std_{window}h'] = df['temperatur'].shift(1).rolling(window=window).std()
    
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
    
    df.interpolate(method='linear', limit_direction='forward', inplace=True)
    df.fillna(method='bfill', inplace=True)

    # --- SCHRITT 5: FINALES FEATURE-SET ERSTELLEN ---
    df.drop(columns=['temperatur'], inplace=True, errors='ignore')

    latest_features = df.iloc[[-1]]
    
    return latest_features
