import asyncio
import sys
import requests
import uuid
import json
from pathlib import Path

from prefect import get_client, deploy
from prefect.server.schemas.actions import WorkPoolCreate
from prefect.exceptions import ObjectNotFound
from prefect.workers.process import ProcessWorker
from prefect.filesystems import LocalFileSystem 
from prefect.deployments.runner import RunnerDeployment

from flows.data_ingestion import data_ingestion_flow as target_flow

# --- Konfiguration --- TODO: hole die konfigurationen aus .env oder utils.config.settings()
WORK_POOL_NAME = "timeseries"
DEPLOYMENT_NAME = "timeseries-data-ingestion"
FLOW_SCRIPT_PATH = Path("./flows/data_ingestion.py") 
FLOW_FUNCTION_NAME = "data_ingestion_flow" 
FLOW_ENTRYPOINT = f"./flows/data_ingestion.py:{FLOW_FUNCTION_NAME}" 
APP_BASE_PATH = Path("/app/ml_service/") 
DEFAULT_BOX_ID = "5faeb5589b2df8001b980304"
INITIAL_FETCH_DAYS = 365
CHUNK_DAYS = 4
INTERVAL_SECONDS = 300


async def create_or_get_work_pool(client, name: str):
    print(f"Prüfe Work Pool '{name}'...")
    try:
        pool = await client.read_work_pool(work_pool_name=name)
        print(f"Work Pool '{name}' existiert bereits.")
        return pool
    except ObjectNotFound:
        print(f"Work Pool '{name}' nicht gefunden. Erstelle...")
        try:
            pool_config = WorkPoolCreate(name=name, type="process")
            pool = await client.create_work_pool(work_pool=pool_config)
            print(f"Work Pool '{name}' erstellt.")
            return pool
        except Exception as e:
            print(f"FEHLER: Konnte Work Pool '{name}' nicht erstellen: {e}", file=sys.stderr)
            if hasattr(e, 'response') and e.response:
                try:
                    error_detail = await e.response.json()
                    print(f"Server Response: {error_detail}", file=sys.stderr)
                except:
                     print(f"Server Response (raw): {await e.response.text()}", file=sys.stderr)
            sys.exit(1)



async def main():
    """Hauptfunktion zum Einrichten und Starten des Prefect Workers via API."""
    async with get_client() as client:
        # --- Work Pool sicherstellen ---
        await create_or_get_work_pool(client, WORK_POOL_NAME)

        # --- Deployment erstellen/aktualisieren ---
        deployment_params = {
            "box_id": DEFAULT_BOX_ID,
            "initial_fetch_days": INITIAL_FETCH_DAYS,
            "fetch_chunk_days": CHUNK_DAYS,
            "initial": False,
        }
        schedule_payload = [
            {
                "schedule": {
                    "interval": INTERVAL_SECONDS         
                },
            }
        ]
        deployment_tags = ["ingestion", "opensensemap", "scheduled"]
        deployment_description = f"Holt alle {INTERVAL_SECONDS // 60} Minuten Daten von OpenSenseMap für Box {DEFAULT_BOX_ID}"

        ingestion_flow_id = await client.create_flow_from_name(FLOW_FUNCTION_NAME)

        # --- Deployment erstellen ---
        ingestion_deployment = requests.post(
            f"http://prefect:4200/api/deployments",
            json={
                "name": DEPLOYMENT_NAME,
                "flow_id": str(ingestion_flow_id),  
                "work_pool_name": WORK_POOL_NAME,
                "entrypoint": FLOW_ENTRYPOINT,
                "path": str(APP_BASE_PATH),
                "parameter_openapi_schema": deployment_params,
                "parameters": deployment_params,
                "schedules": schedule_payload, 
                "tags": deployment_tags,
                "description": deployment_description,
                "concurrency_options": {
                    "collision_strategy": "CANCEL_NEW"
                },
            },
            headers={"Content-Type": "application/json"},
        )

        response_data = ingestion_deployment.json()

        print(f"Deployment '{DEPLOYMENT_NAME}' (ID: {json.dumps(response_data, indent=2)}) erfolgreich erstellt.")

        # --- Deployment ml_training ---
        deployment_tags = ["ml_training"]
        deployment_description = f"trainiert fprecast modelle"

        deployment_params = {
        }
        schedule_payload = [
            {
                "schedule": {
                    "cron": "0 2 * * *",
                    "timezone": "Europe/Berlin"
                }
            }
        ]

        flow_id = await client.create_flow_from_name("train_all_models")

        # --- Deployment erstellen ---
        deployment_json_payload = {
            "name": "ml_training_temperature",
            "flow_id": str(flow_id),  
            "work_pool_name": WORK_POOL_NAME,
            "entrypoint": f"./flows/ml_training.py:{'train_all_models'}",
            "path": str(APP_BASE_PATH),  
            "schedules": schedule_payload, # Corrected from "schedule" to "schedules"
            "tags": deployment_tags,
            "description": deployment_description,
        }

        # Make the API request
        deployment_response = requests.post(
            f"http://prefect:4200/api/deployments",
            json=deployment_json_payload,
            headers={"Content-Type": "application/json"},
        )

        # --- NEUE DEBUGGING-LOGIK ---

        # Check if the request was successful (status code 2xx)
        if 200 <= deployment_response.status_code < 300:
            deployment_id = deployment_response.json().get('id')
            print(f"✅ Deployment 'ml_training_temperature' (ID: {deployment_id}) erfolgreich erstellt.")

        # Handle client and server errors (status code 4xx or 5xx)
        else:
            print(f"❌ Fehler beim Erstellen des Deployments 'ml_training_temperature'.")
            print(f"   Status Code: {deployment_response.status_code}")

            try:
                # Try to parse the JSON error response from the API
                error_data = deployment_response.json()
                
                # Specifically format the detailed 422 error message
                if deployment_response.status_code == 422 and "detail" in error_data:
                    print("   Validierungsfehler von der API:")
                    for error_detail in error_data["detail"]:
                        # Extract location and message for each error
                        location = " -> ".join(map(str, error_detail.get("loc", [])))
                        message = error_detail.get("msg", "Keine Fehlermeldung vorhanden.")
                        print(f"     - Ort: {location}")
                        print(f"       Nachricht: {message}")
                else:
                    # Print the full JSON for other errors
                    print("   API-Antwort:")
                    print(json.dumps(error_data, indent=2))

            except json.JSONDecodeError:
                # Fallback if the response is not valid JSON
                print(f"   Die Fehlerantwort war kein gültiges JSON: {deployment_response.text}")

        # --- Deployment ml_training ---
        deployment_tags = ["forecast"]
        deployment_description = f"Erstellt predictions"

        deployment_params = {
        }

        flow_id = await client.create_flow_from_name("generate_forecast_flow")

        # --- Deployment erstellen ---
        deployment = requests.post(
            f"http://prefect:4200/api/deployments",
            json={
                "name": "create_forecast",
                "flow_id": str(flow_id),  
                "work_pool_name": WORK_POOL_NAME,
                "entrypoint": f"./flows/generate_forecast.py:{'generate_forecast_flow'}",
                "path": str(APP_BASE_PATH),  
                "parameter_openapi_schema": deployment_params,
                "parameters": deployment_params,
                "tags": deployment_tags,
                "description": deployment_description,
            },
            headers={"Content-Type": "application/json"},
        )

        print(f"Deployment '{DEPLOYMENT_NAME}' (ID: {deployment}) erfolgreich erstellt.")

        # print(f"\nTriggering initial run for deployment '{response_data.get('id')}'...")
        # try:
        #     await client.create_flow_run_from_deployment(
        #         deployment_id=response_data.get('id'),
        #         parameters={"initial": True}
        #     )
        #     print(f"Initialer Lauf für '{DEPLOYMENT_NAME}' erfolgreich zur Warteschlange hinzugefügt.")
        # except Exception as e:
        #     print(f"Fehler beim Auslösen des initialen Laufs: {e}", file=sys.stderr)

    # --- Worker starten ---
    print(f"Starte Worker für Pool '{WORK_POOL_NAME}'...")
    try:
        worker = ProcessWorker(work_pool_name=WORK_POOL_NAME)
        await worker.start() 

    except KeyboardInterrupt:
        print("\nWorker gestoppt.")
        sys.exit(0)
    except Exception as e:
        print(f"Ein unerwarteter Fehler ist beim Starten des Workers aufgetreten: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"Ein kritischer Fehler ist aufgetreten: {e}", file=sys.stderr)
        sys.exit(1)

