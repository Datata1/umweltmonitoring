# tasks/plotting.py 
import pandas as pd
import matplotlib.pyplot as plt
import io 
from prefect import task

@task(name="Create Forecast Plot")
async def create_forecast_plot_task(
    historical_data_df: pd.DataFrame, 
    forecast_df: pd.DataFrame         
) -> bytes:
    """Erstellt einen Plot der historischen Daten und der Vorhersage."""
    print("Erstelle Vorhersage-Plot...")
    
    plt.figure(figsize=(15, 7))
    
    # Historische Daten plotten
    if not historical_data_df.empty:
        plt.plot(historical_data_df.index, historical_data_df['temperatur'], label='Historische Temperatur', color='blue')
    
    # Vorhersage plotten
    if not forecast_df.empty:
        plt.plot(forecast_df.index, forecast_df['predicted_temp'], label='Vorhersage Temperatur', color='red', linestyle='--')
    
    plt.title('Temperatur: Historie und Vorhersage')
    plt.xlabel('Zeit')
    plt.ylabel('Temperatur (°C)')
    plt.legend()
    plt.grid(True)
    plt.xticks(rotation=45)
    plt.tight_layout() 
    
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    plt.close() 
    buf.seek(0) 
    
    image_bytes = buf.getvalue()
    buf.close()
    
    print("Vorhersage-Plot als Bytes erstellt.")
    return image_bytes