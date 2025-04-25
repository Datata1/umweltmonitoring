#!/bin/bash

# --- Konfiguration ---
WORK_POOL_NAME="timeseries"
DEPLOYMENT_NAME="timeseries-data-ingestion" 
FLOW_ENTRYPOINT="./flows/data_ingestion.py:data_ingestion_flow" 
DEFAULT_BOX_ID="5faeb5589b2df8001b980304" 
INITIAL_FETCH_DAYS=7
CHUNK_DAYS=2
INTERVAL_SECONDS=180 

# --- Work Pool erstellen (falls nicht vorhanden) ---
echo "Prüfe Work Pool '$WORK_POOL_NAME'..."
if ! uv run prefect work-pool inspect "$WORK_POOL_NAME" > /dev/null 2>&1; then
    echo "Work Pool '$WORK_POOL_NAME' nicht gefunden. Erstelle..."
    uv run prefect work-pool create "$WORK_POOL_NAME" --type process
    if [ $? -ne 0 ]; then
        echo "FEHLER: Konnte Work Pool '$WORK_POOL_NAME' nicht erstellen."
        exit 1
    fi
    echo "Work Pool '$WORK_POOL_NAME' erstellt."
else
    echo "Work Pool '$WORK_POOL_NAME' existiert bereits."
fi

echo "Erstelle/Aktualisiere Deployment '$DEPLOYMENT_NAME' mit $INTERVAL_SECONDS Sekunden Intervall..."

uv run prefect deploy \
    --pool "$WORK_POOL_NAME" \
    --name "$DEPLOYMENT_NAME" \
    --interval "$INTERVAL_SECONDS" \
    --param "box_id=$DEFAULT_BOX_ID" \
    --param "initial_fetch_days=$INITIAL_FETCH_DAYS" \
    --param "fetch_chunk_days=$CHUNK_DAYS" \
    --description "Holt alle 3 Minuten Daten von OpenSenseMap für Box $DEFAULT_BOX_ID" \
    --tag "ingestion" \
    --tag "opensensemap" \
    --tag "scheduled" \
    "$FLOW_ENTRYPOINT" 

if [ $? -ne 0 ]; then
    echo "FEHLER: Konnte Deployment '$DEPLOYMENT_NAME' nicht erstellen/aktualisieren."
    exit 1
fi
echo "Deployment '$DEPLOYMENT_NAME' erfolgreich konfiguriert."

# --- Worker starten ---
echo "Starte Worker für Pool '$WORK_POOL_NAME'..."
uv run prefect worker start --pool "$WORK_POOL_NAME"