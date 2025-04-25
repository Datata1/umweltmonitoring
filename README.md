```
projekt-opensensebox-dashboard/
├── .env.sample              # Beispiel für Umgebungsvariablen
├── .gitignore               # Ignorierte Dateien für Git
├── docker-compose.yml       # Konfiguration für Docker-Services
├── pyproject.toml           # Projekt-Konfiguration (z.B. Poetry)
├── Caddyfile                # Konfiguration für den Reverse Proxy (Caddy)
├── init_script              # SQL Skripte bei DB Initialisierung
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
    │   ├── Dockerfile       #   Dockerfile für den Backend-Service
    ├── frontend/            # Frontend-Service (Dash)
    │   └── app/             #   Hauptverzeichnis der Dash-Anwendung
    │       ├── app.py       #     ► Haupt-Dash-Instanz, Basis-Layout, Navigation
    │       ├── maindash.py  #     ► Workaround für callback in verschiedenen Dateien
    │       ├── pages/       #     ► Verzeichnis für die einzelnen Seiten/Ansichten
    │       ├── components/  #     ► Wiederverwendbare Dash-Layout-Komponenten 
    │       ├── assets/      #     ► Statische Dateien (CSS, JS, Bilder) - Browser-zugänglich
    │       └── utils/       #     ► Hilfsfunktionen (z.B. API-Client, Datenverarbeitung)
    │   └── Dockerfile       #   Dockerfile für den Frontend-Service
    └── ml_service/          # Zukünftiger ML Service (z.B. mit Prefect)
        ├── flows/           # ► Prefect Flows
        ├── tasks/           # ► Prefect Tasks
        ├── utils/          
        ├── Dockerfile       
```

1. frontend `localhost:3000`
2. prefect `localhost:3000/prefect`
3. db-explorer `localhost:3000/db-admin`
4. api documentation `localhost:3000/docs#`

commands:

1. start docker-compose
```sh
sudo docker-compose up --build --force-recreate
```

2. tear-down docker container completly (persistent volumes too)
```sh
sudo docker-compose down --volumes
```

# TODO:
- set up prefect for ml workloads
- setup sql init script (./init_scripts) instead of doing it in the backend (services/backend/db/init_db.py)
- plan backend endpoints
- refactor code base
- reduce logs overall (especially in prefect since logs are stored in db)
- plan frontend design 
- plan frontend components
- add more todos