import asyncio
import sys
from pathlib import Path

from prefect import get_client
from prefect.server.schemas.actions import WorkPoolCreate
from prefect.exceptions import ObjectNotFound
from prefect.workers.process import ProcessWorker
from prefect.filesystems import LocalFileSystem 

# --- Konfiguration --- TODO: hole die konfigurationen aus .env oder utils.config.settings()
WORK_POOL_NAME = "timeseries"
DEPLOYMENT_NAME = "timeseries-data-ingestion"
FLOW_SCRIPT_PATH = Path("./flows/data_ingestion.py") 
FLOW_FUNCTION_NAME = "data_ingestion_flow" 
FLOW_ENTRYPOINT = f"flows/data_ingestion.py:{FLOW_FUNCTION_NAME}" 
APP_BASE_PATH = Path("/app") 
DEFAULT_BOX_ID = "5faeb5589b2df8001b980304"
INITIAL_FETCH_DAYS = 7
CHUNK_DAYS = 2
INTERVAL_SECONDS = 180


try:
    from flows.data_ingestion import data_ingestion_flow as target_flow

    if not hasattr(target_flow, 'deploy'):
         raise TypeError("Das importierte Objekt 'target_flow' ist kein gültiger Prefect Flow oder hat keine 'deploy' Methode.")

except ImportError as e:
    print(f"FEHLER: Konnte den Flow nicht importieren von 'flows.data_ingestion'. Stelle sicher, dass der Pfad korrekt ist ({FLOW_ENTRYPOINT}) und das Basisverzeichnis ({APP_BASE_PATH}) im Python-Pfad ist oder die Imports relativ korrekt sind. Fehler: {e}", file=sys.stderr)
    sys.exit(1)
except TypeError as e:
    print(f"FEHLER: {e}", file=sys.stderr)
    sys.exit(1)

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

async def deploy_flow_with_method(flow_obj, deployment_name, work_pool_name, interval_seconds, params, tags, description):
    """Erstellt oder aktualisiert ein Deployment mit der flow.deploy() Methode."""
    print(f"Erstelle/Aktualisiere Deployment '{deployment_name}' mit flow.deploy() Methode...")
    try:
        # source: https://orion-docs.prefect.io/latest/api-ref/prefect/flows/#prefect.flows.Flow.to_deployment
        # source: https://linen.prefect.io/t/26784682/ulva73b9p-i-am-trying-to-create-a-local-deployment-from-a-fl
        deployment_id = await flow_obj.to_deployment(
            deployment_name, 
            work_pool_name=work_pool_name,
            interval=interval_seconds,
            parameters=params,
            tags=tags,
            description=description,
        )

        if not deployment_id:
             raise RuntimeError("Deployment fehlgeschlagen, keine Deployment-ID zurückgegeben.")

        print(f"Deployment '{deployment_name}' (ID: {deployment_id}) erfolgreich konfiguriert.")
        return deployment_id
    except Exception as e:
        print(f"FEHLER: Konnte Deployment '{deployment_name}' nicht erstellen/aktualisieren: {e}", file=sys.stderr)
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

    # --- Speicherort definieren ---
    storage_block = LocalFileSystem(
        basepath=APP_BASE_PATH
    )
    await storage_block.save(
        name="local-storage",
        overwrite=True
    )

    # --- Deployment erstellen/aktualisieren ---
    deployment_params = {
        "box_id": DEFAULT_BOX_ID,
        "initial_fetch_days": INITIAL_FETCH_DAYS,
        "fetch_chunk_days": CHUNK_DAYS,
    }
    deployment_tags = ["ingestion", "opensensemap", "scheduled"]
    deployment_description = f"Holt alle {INTERVAL_SECONDS // 60} Minuten Daten von OpenSenseMap für Box {DEFAULT_BOX_ID}"

    await deploy_flow_with_method(
        flow_obj=target_flow, 
        deployment_name=DEPLOYMENT_NAME,
        work_pool_name=WORK_POOL_NAME,
        interval_seconds=INTERVAL_SECONDS,
        params=deployment_params,
        tags=deployment_tags,
        description=deployment_description
    )

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

