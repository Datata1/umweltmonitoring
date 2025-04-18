```
projekt-opensensebox-dashboard/
├── .env.sample              # Beispiel für Umgebungsvariablen
├── .gitignore               # Ignorierte Dateien für Git
├── docker-compose.yml       # Konfiguration für Docker-Services
├── pyproject.toml           # Projekt-Konfiguration (z.B. Poetry)
├── Caddyfile                # Konfiguration für den Reverse Proxy (Caddy)
└── services/                # Verzeichnis für einzelne Service-Komponenten
    ├── backend/             # Backend-Service (FastAPI)
    │   ├── app/             #   Haupt-Anwendungscode
    │   │   ├── main.py      #     ► FastAPI App Instanz, Router Einbindung, Lifespan (DB Init, Scheduler)
    │   │   ├── api/         #     ► API Endpunkte
    │   │   │   └── v1/      #       ► API Version 1
    │   │   │       └── endpoints/ # ►  API Endpunkte Definitionen
    │   │   │           └── sensors.py # ►  Endpunkte für Sensordaten (CRUD, Aggregation, etc.)
    │   │   ├── core/        #     ► Kernkonfigurationen
    │   │   ├── crud/        #     ► Datenbank-Operationen (Create, Read, Update, Delete)
    │   │   ├── models/      #     ► SQLAlchemy ORM Modelle
    │   │   ├── schemas/     #     ► Pydantic Modelle (Datenvalidierung, API Request/Response)
    │   │   └── db/          #     ► Datenbank-Setup und Skripte
    │   ├── alembic/         #   Alembic Migrationsumgebung
    │   ├── alembic.ini      #   Alembic Konfigurationsdatei
    │   ├── Dockerfile       #   Dockerfile für den Backend-Service
    ├── frontend/            # Frontend-Service (Dash)
    │   └── app/             #   Hauptverzeichnis der Dash-Anwendung
    │       ├── app.py       #     ► Haupt-Dash-Instanz, Basis-Layout, Navigation
    │       ├── index.py     #     ► Optionale Startseite (Index-Seite)
    │       ├── pages/       #     ► Verzeichnis für die einzelnen Seiten/Ansichten
    │       ├── components/  #     ► Wiederverwendbare Dash-Layout-Komponenten (optional)
    │       ├── callbacks/   #     ► Zentralisierte Callback-Definitionen (optional)
    │       ├── assets/      #     ► Statische Dateien (CSS, JS, Bilder) - Browser-zugänglich
    │       └── utils/       #     ► Hilfsfunktionen (z.B. API-Client, Datenverarbeitung)
    │   └── Dockerfile       #   Dockerfile für den Frontend-Service
    └── ml_service/          # Zukünftiger ML Service (z.B. mit Prefect)
        ├── flows/           # ► Prefect Flows
        ├── tasks/           # ► Prefect Tasks
        ├── utils/          
        ├── Dockerfile       
```

# Note:
When changing the SQLAlchemy models then execute these commands in `services/backend`

1.
```
alembic revision --autogenerate -m "Beschreibung der Änderung"
```

2. 
```
alembic upgrade head
```