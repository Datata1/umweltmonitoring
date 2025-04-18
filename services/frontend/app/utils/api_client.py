# services/frontend/app/utils/api_client.py
import requests
import os
import logging

logger = logging.getLogger(__name__)

# Annahme: Die Backend URL kommt aus Umgebungsvariablen
BACKEND_API_URL = os.environ.get("BACKEND_API_URL", "http://localhost:3000") 

def get_sensor_boxes():
    """ Ruft eine Liste aller Sensorboxen vom Backend ab """
    url = f"{BACKEND_API_URL}/api/v1/sensor_boxes"
    logger.info(f"Requesting sensor boxes from backend: {url}")
    try:
        response = requests.get(url)
        response.raise_for_status() # Wirft HTTPError für schlechte Antworten
        data = response.json()
        logger.info(f"Received data from backend (first 100 chars): {str(data)[:100]}...") # Logge nur einen Teil der Daten
        return data # Rückgabe der Daten (erwartet wird eine Liste durch response_model)
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching sensor boxes from backend: {e}", exc_info=True)
        raise # Fehler weitergeben

# Füge hier weitere Funktionen für andere Endpunkte hinzu (z.B. get_sensor_box_details etc.)
# ...