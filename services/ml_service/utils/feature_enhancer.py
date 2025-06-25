import pandas as pd
import numpy as np
import requests
import pvlib
from typing import Dict, Optional

# --- 1. Konfiguration basierend auf deinem Geostandort ---
LATITUDE = 52.019364
LONGITUDE = -1.73893
# Wichtig für korrekte Zeitberechnungen, basierend auf der Longitude ist London passend
TIMEZONE = "Europe/London" 

def get_solar_features(df_index: pd.DatetimeIndex) -> pd.DataFrame:
    """
    Berechnet den Sonnenstand (Höhe und Azimut) für jeden Zeitstempel im Index.
    
    Args:
        df_index: Der DatetimeIndex des Haupt-DataFrames.

    Returns:
        Ein DataFrame mit den neuen Sonnenstand-Features.
    """
    print("Berechne Sonnenstand-Features mit pvlib...")
    # Erstelle ein Location-Objekt mit den Geodaten
    location = pvlib.location.Location(latitude=LATITUDE, longitude=LONGITUDE, tz=TIMEZONE)
    
    # Berechne die Sonnenposition für jeden Zeitstempel
    # 'apparent_elevation' ist der wichtigste Wert (Winkel der Sonne über dem Horizont)
    solar_position = location.get_solarposition(df_index)
    
    # Wir nehmen nur die für uns relevanten Spalten
    features = solar_position[['apparent_elevation', 'azimuth']].copy()
    features.rename(columns={
        'apparent_elevation': 'solar_elevation', 
        'azimuth': 'solar_azimuth'
    }, inplace=True)
    
    # Normalisiere die Werte in einen sinnvollen Bereich für das ML-Modell
    # Elevation: sin() wandelt Winkel in einen Bereich [-1, 1] um, der den Auf- und Untergang gut abbildet
    features['solar_elevation'] = np.sin(np.radians(features['solar_elevation']))
    
    # Azimut (0-360 Grad) in Sin/Cos-Paar umwandeln
    features['solar_azimuth_sin'] = np.sin(np.radians(features['solar_azimuth']))
    features['solar_azimuth_cos'] = np.cos(np.radians(features['solar_azimuth']))
    features.drop('solar_azimuth', axis=1, inplace=True)
    
    print("Sonnenstand-Features erfolgreich berechnet.")
    return features

def get_weather_features(start_date: str, end_date: str) -> Optional[pd.DataFrame]:
    """
    Holt Wetterdaten von der Open-Meteo API.
    Kann entweder historische Daten (fürs Training) oder Vorhersagedaten (für Live-Betrieb) abfragen.

    Args:
        start_date: Startdatum im Format 'YYYY-MM-DD'.
        end_date: Enddatum im Format 'YYYY-MM-DD'.
        forecast: Wenn True, werden Vorhersagedaten für die nächsten Tage abgefragt.

    Returns:
        Ein DataFrame mit den Wetter-Features oder None bei einem Fehler.
    """
    print(f"Hole Wetterdaten von Open-Meteo für den Zeitraum {start_date} bis {end_date}...")
    
    # Definiere die Wettervariablen, die wir haben wollen.
    # Globalstrahlung (ghi) ist am wichtigsten!
    params = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "hourly": "relative_humidity_2m,cloud_cover,wind_speed_10m,global_tilted_irradiance",
        "timezone": TIMEZONE
    }

    api_url = "https://archive-api.open-meteo.com/v1/archive"
    params["start_date"] = start_date
    params["end_date"] = end_date
        
    try:
        response = requests.get(api_url, params=params)
        response.raise_for_status()  # Wirft einen Fehler bei HTTP-Status 4xx oder 5xx
        data = response.json()
        
        # Konvertiere die JSON-Antwort in ein sauberes Pandas DataFrame
        df = pd.DataFrame(data['hourly'])
        df['time'] = pd.to_datetime(df['time'])
        df.set_index('time', inplace=True)

        # KORREKTUR: Stelle sicher, dass der Index die gleiche Zeitzonen-Information hat
        # wie der Haupt-DataFrame, um den TypeError zu vermeiden.
        if df.index.tz is None:
            # Wenn der Index "naiv" ist, weisen wir die Zeitzone zu und behandeln
            # die Übergänge zur Sommer-/Winterzeit ("nonexistent" und "ambiguous" times).
            # 'nonexistent' verschiebt nicht-existente Zeiten (Sommerzeit) auf die nächste gültige Zeit.
            # 'ambiguous' versucht, mehrdeutige Zeiten (Winterzeit) aus der Reihenfolge zu erschließen.
            df = df.tz_localize(TIMEZONE, ambiguous='infer', nonexistent='shift_forward')
        else:
            # Wenn der Index bereits eine Zeitzone hat (z.B. UTC), konvertieren wir sie in unsere Ziel-Zeitzone.
            df = df.tz_convert(TIMEZONE)
        
        # Umbenennen für Klarheit im Modell
        df.rename(columns={
            'relative_humidity_2m': 'weather_humidity',
            'cloud_cover': 'weather_cloud_cover',
            'wind_speed_10m': 'weather_wind_speed',
            'global_tilted_irradiance': 'weather_radiation_ghi'
        }, inplace=True)
        
        print(f"Wetterdaten erfolgreich geladen. (Shape: {df.shape})")
        return df

    except requests.exceptions.RequestException as e:
        print(f"FEHLER beim Abrufen der Wetterdaten von Open-Meteo: {e}")
        return None
