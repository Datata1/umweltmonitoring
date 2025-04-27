```
umweltmonitoring/              # ► Projekt-Root-Verzeichnis
├── assets/                    # ► Globale statische Assets für das Projekt
├── init_scripts/              # ► SQL-Skripte zur Datenbank-Initialisierung (für Docker Entrypoint)
├── services/                  # ► Verzeichnis für die einzelnen Anwendungs-Services
│   ├── backend/               #   ► FastAPI-Backend-Service
│   │   ├── api/               #     ► API-Endpunkte-Definitionen
│   │   │   └── v1/            #       ► Version 1 der API
│   │   │       └── endpoints/ #         ► Module für API-Endpunkte
│   │   │           └── sensors.py #       ► API-Endpunkte für Sensor-Operationen (CRUD, Aggregation etc.)
│   │   ├── core/              #     ► Kernkonfigurationen und allgemeine Hilfsprogramme für das Backend
│   │   │   └── config.py      #       ► Projekteinstellungen (geladen via Pydantic Settings)
│   │   ├── main.py            #     ► Haupt-Einstiegspunkt der FastAPI-Anwendung (App-Instanz, Lifespan Events)
│   │   └── utils/             #     ► Hilfsfunktionen spezifisch für das Backend
│   │       ├── db_session.py  #       ► Einrichtung der Datenbank-Session (SQLAlchemy Engine/Session)
│   │       └── keybuilder.py  #       ► Hilfsklasse/Funktion zum Bauen von Cache-Schlüsseln
│   ├── frontend/              #   ► Dash-Frontend-Anwendung
│   │   ├── app.py             #     ► Haupt-Dash-Instanz, Basis-Layout, Navigation
│   │   ├── assets/            #     ► Statische Assets für das Frontend (vom Browser zugänglich)
│   │   ├── components/        #     ► Wiederverwendbare Dash-Layout-Komponenten (UI-Elemente)
│   │   ├── maindash.py        #     ► Alternative/zusätzliche Hauptdatei oder Modul für Dash-App-Instanz/Calllbacks
│   │   ├── pages/             #     ► Einzelne Seiten/Layouts der Dash-Anwendung
│   │   └── utils/             #     ► Dienstprogramme und Hilfsfunktionen spezifisch für das Frontend
│   │       └── api_client.py  #       ► Client zur Kommunikation mit dem Backend-API
│   └── ml_service/            #   ► Machine Learning / Datenverarbeitungs-Service (z.B. mit Prefect)
│       ├── flows/             #     ► Definitionen von Prefect Flows (Automatisierte Workflows)
│       ├── tasks/             #     ► Definitionen von Prefect Tasks (Einzelschritte innerhalb von Flows)
│       └── utils/             #     ► Dienstprogramme und Hilfsfunktionen für den ML-Service
├── shared/                    # ► Geteilter Code zwischen den Services (eigenes Python-Package)
│   ├── crud/                  #   ► Geteilte Datenbank-Operationen (oft mit den Shared Models)
│   │   └── crud_sensor.py     #     ► Geteilte CRUD-Logik für Sensordaten
│   ├── models/                #   ► Geteilte SQLAlchemy ORM Modelle (Datenbank-Mapping)
│   │   └── __init__.py        #     ► Macht 'models' zu einem Python-Sub-Package
│   │   └── base.py            #     ► Basisklasse für ORM-Modelle (z.B. SQLAlchemy Declarative Base)
│   │   └── sensor.py          #     ► ORM-Modelle für SensorBox, Sensor, SensorData
│   └── schemas/               #   ► Geteilte Pydantic Modelle (Datenvalidierung, API Request/Response)
│       └── __init__.py        #     ► Macht 'schemas' zu einem Python-Sub-Package
│       └── sensor.py          #     ► Pydantic Schemas für SensorBox, Sensor, SensorData
├── pyproject.toml             # ► Haupt-Projekt-Konfiguration (Metadaten, Abhängigkeiten, Build-System)
├── README.md                  # ► Haupt-Projekt-Beschreibung und Dokumentation
├── Caddyfile                  # ► Konfigurationsdatei für den Caddy Reverse Proxy
├── db.drawio.pdf              # ► Diagramm der Datenbankstruktur (mit draw.io erstellt)
├── docker-compose.yml         # ► Definition und Konfiguration der Docker-Services
└── uv.lock                    # ► Lock-Datei für Abhängigkeiten (erzeugt von uv)
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
- plan backend endpoints
- reduce logs overall (especially in prefect since logs are stored in db)
- plan frontend design 
- plan frontend components
- plan prefect flows for ml workloads
- add prefect artifacts to flows to debug flows
- add more todos
