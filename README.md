projekt-opensensebox-dashboard/
├── .env.sample
├── .gitignore
├── docker-compose.yml
├── pyproject.toml
├── Caddyfile  # reverse proxy
├── services/           
│   ├── backend/
│   │   ├── app/
│   │   │   ├── main.py       # FastAPI App Instanz, Router Einbindung
│   │   │   ├── api/          
│   │   │   │   └── v1/
│   │   │   │       └── endpoints/
│   │   │   │           └── sensors.py # Endpunkte für Sensordaten
│   │   │   ├── core/         # Konfiguration
│   │   │   │   └── config.py
│   │   │   ├── crud/         # Datenbank-Operationen (Create, Read, Update, Delete)
│   │   │   │   └── crud_sensordata.py
│   │   │   ├── models/       # SQLAlchemy ORM Modelle
│   │   │   │   ├── base.py     # Basisklasse für Modelle
│   │   │   │   └── sensor.py   # ORM Modell Sensordaten
│   │   │   ├── schemas/      # Pydantic Modelle (Datenvalidierung, API Request/Response)
│   │   │   │   └── sensor.py
│   │   │   └── db/           # Datenbank-Setup
│   │   │       ├── init_db.py  # initialisiert db
│   │   │       └── session.py  # Datenbank-Session Management
│   │   ├── alembic/
│   │   ├── alembic.ini
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   ├── frontend/
│   │   ├── app/
│   │   │   ├── app.py        # Dash App Instanz, Layout Definition
│   │   │    ├── callbacks.py  # Alle Callbacks
│   │   │   ├── components/   # Wiederverwendbare Layout-Teile (optional)
│   │   │   ├── assets/       # CSS, JS Dateien
│   │   │   └── utils/     # Funktionen zum Abrufen von Daten vom Backend API
│   │   │       └── api_client.py
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   ├── data_ingestion/
│   │   ├── ingest.py  # schedule oder APScheduler
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   └── ml_service/     # (Zukünftig)
│       ├── flows/      # Prefect Flows
│       ├── tasks/      # Prefect Tasks
│       ├── models/     # Gespeicherte Modelle
│       ├── Dockerfile
│       └── requirements.txt
└── README.md