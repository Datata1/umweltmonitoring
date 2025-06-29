# Architektur

# `docker-compose.yml`

Dieses Dokument beschreibt die `docker-compose.yml`-Datei, die zur Definition und Ausführung der Multi-Container-Anwendung verwendet wird.

Diese `docker-compose.yml`-Datei definiert eine Multi-Container-Anwendung, die ein Umweltmonitoring-System mit einem Backend, Frontend, Datenbank, Redis-Cache, Prefect-Server, Prefect-Worker und einem Datenbank-Explorer bereitstellt, alles hinter einem Caddy-Proxy.

### Version
`3.8`

### Dienste (Services)

#### 1. `db`
* **Beschreibung**: Der PostgreSQL-Datenbankdienst mit TimescaleDB-Erweiterung.
* **Image**: `timescale/timescaledb:latest-pg16`
* **Container Name**: `timescale_db_umw`
* **Umgebungsvariablen**: Konfiguriert den PostgreSQL-Benutzer (`POSTGRES_USER`), das Passwort (`POSTGRES_PASSWORD`) und den Datenbanknamen (`POSTGRES_DB`) mittels Umgebungsvariablen oder Standardwerten.
* **Volumes**: Persistiert Datenbankdaten in `postgres_data` und führt Initialisierungsskripte aus dem `./init_scripts`-Verzeichnis aus.
* **Ports**: Exponiert Port `5432` des Containers nach außen.
* **Restart Policy**: Startet immer neu, es sei denn, er wird explizit gestoppt.
* **Healthcheck**: Überprüft die Datenbankverbindung mit `pg_isready`.

#### 2. `redis`
* **Beschreibung**: Der Redis-Cache-Dienst für FastAPI-Caching und andere Zwecke.
* **Image**: `redis:latest`
* **Container Name**: `redis_cache_umw`
* **Restart Policy**: Startet immer neu, es sei denn, er wird explizit gestoppt.
* **Volumes**: Persistiert Redis-Daten in `redis_data`.
* **Ports**: Exponiert Port `6379` des Containers nach außen.

#### 3. `backend`
* **Beschreibung**: Der FastAPI-Backend-Dienst.
* **Container Name**: `backend_fastapi_umw`
* **Build Kontext**: Baut das Docker-Image aus dem aktuellen Verzeichnis mit dem Dockerfile in `./services/backend/Dockerfile`.
* **Volumes**: Bindet lokale Verzeichnisse (`./services/backend`, `./shared`, `./host_models_dir`) in den Container ein.
* **Command**: Führt die FastAPI-Anwendung mit `uvicorn` im Reload-Modus aus.
* **Umgebungsvariablen**: Setzt `PREFECT_API_URL` zur Kommunikation mit dem Prefect-Server.
* **Working Directory**: Setzt das Arbeitsverzeichnis im Container auf `/app/backend`.
* **Dependencies**: Startet, nachdem `db`, `redis`, `prefect` und `prefect-worker` gestartet und als "healthy" (für `db`) oder "started" (für andere) befunden wurden.
* **Restart Policy**: Startet immer neu, es sei denn, er wird explizit gestoppt.
* **Ports**: Exponiert Port `8000` des Containers nach außen.
* **Healthcheck**: Überprüft die Erreichbarkeit des `/api/health`-Endpunkts des Backends.

#### 4. `frontend`
* **Beschreibung**: Der Dash-Frontend-Dienst.
* **Container Name**: `frontend_dash_umw`
* **Build Kontext**: Baut das Docker-Image aus dem aktuellen Verzeichnis mit dem Dockerfile in `./services/frontend/Dockerfile`.
* **Volumes**: Bindet lokale Verzeichnisse (`./services/frontend`, `./shared`) in den Container ein.
* **Command**: Führt die Dash-Anwendung mit `uvicorn` aus.
* **Umgebungsvariablen**: Setzt `BACKEND_API_URL` zur Kommunikation mit dem Backend-Dienst.
* **Working Directory**: Setzt das Arbeitsverzeichnis im Container auf `/app/frontend`.
* **Dependencies**: Startet, nachdem das `backend`-Service als "healthy" befunden wurde.
* **Restart Policy**: Startet immer neu, es sei denn, er wird explizit gestoppt.
* **Ports**: Exponiert Port `8050` des Containers nach außen.

#### 5. `prefect`
* **Beschreibung**: Der Prefect-Server-Dienst, der die Orchestrierung von Workflows verwaltet.
* **Container Name**: `prefect_server_umw`
* **Image**: `prefecthq/prefect:3-latest`
* **Command**: Startet den Prefect-Server.
* **Umgebungsvariablen**: Konfiguriert die Datenbankverbindung für den Prefect-Server und die API-URL.
* **Dependencies**: Startet, nachdem der `db`-Dienst als "healthy" befunden wurde.
* **Restart Policy**: Startet immer neu, es sei denn, er wird explizit gestoppt.
* **Ports**: Exponiert Port `4200` des Containers nach außen (für das Prefect UI und die API).

#### 6. `prefect-worker`
* **Beschreibung**: Der Prefect-Worker-Dienst, der Prefect Flows ausführt.
* **Container Name**: `prefect_worker_umw`
* **Build Kontext**: Baut das Docker-Image aus dem aktuellen Verzeichnis mit dem Dockerfile in `./services/ml_service/Dockerfile`.
* **Volumes**: Bindet lokale Verzeichnisse (`./services/ml_service`, `./shared`, `./host_models_dir`) in den Container ein.
* **Working Directory**: Setzt das Arbeitsverzeichnis im Container auf `/app/ml_service`.
* **Command**: Führt das `run_worker.py`-Skript aus, das die Deployments registriert und den Worker startet.
* **Umgebungsvariablen**: Setzt `PREFECT_API_URL` und `DATABASE_URL_PREFECT` für die Worker-Konfiguration.
* **Dependencies**: Startet, nachdem `db` als "healthy" und `prefect` als "started" befunden wurde.
* **Restart Policy**: Startet immer neu, es sei denn, er wird explizit gestoppt.
* **Ports**: Exponiert Port `8001` des Containers nach außen.

#### 7. `db-explorer`
* **Beschreibung**: Ein Web-basierter Datenbank-Explorer (pgweb) für PostgreSQL.
* **Container Name**: `pgweb_explorer_umw`
* **Image**: `sosedoff/pgweb:latest`
* **Command**: Startet `pgweb` und konfiguriert die Verbindung zur `db`-Datenbank.
* **Umgebungsvariablen**: Setzt Datenbank-Anmeldedaten, die vom `command` benötigt werden.
* **Dependencies**: Startet, nachdem der `db`-Dienst als "healthy" befunden wurde.
* **Restart Policy**: Startet immer neu, es sei denn, er wird explizit gestoppt.
* **Ports**: Exponiert Port `8081` des Containers nach außen.

#### 8. `caddy`
* **Beschreibung**: Ein Reverse-Proxy und Webserver (Caddy).
* **Container Name**: `caddy_proxy_umw`
* **Image**: `caddy:latest`
* **Restart Policy**: Startet immer neu, es sei denn, er wird explizit gestoppt.
* **Ports**: Exponiert Port `3000` des Containers nach außen.
* **Volumes**: Bindet die lokale `Caddyfile` und persistente Daten/Konfigurationen für Caddy ein.
* **Dependencies**: Stellt sicher, dass `backend`, `prefect` und `db-explorer` gestartet sind, bevor Caddy startet.

### Volumes
* `postgres_data`: Persistentes Volume für PostgreSQL-Daten.
* `redis_data`: Persistentes Volume für Redis-Daten.
* `caddy_data`: Persistentes Volume für Caddy-Daten.
* `caddy_config`: Persistentes Volume für Caddy-Konfigurationen.

---

# Backend

## backend/`main.py`

Diese Datei ist der zentrale Einstiegspunkt für die FastAPI-Anwendung. Sie konfiguriert die Anwendung, bindet API-Router ein, initialisiert Dienste wie den Redis-Cache und den Prefect Scheduler und handhabt den Anwendungslebenszyklus.

### Beschreibung
Die `main.py`-Datei startet die FastAPI-Anwendung für das Umweltmonitoring-Backend. Sie ist verantwortlich für:
* **Anwendungslebenszyklus (`lifespan`)**: Führt Startup-Logik aus, wie die initiale Datenaufnahme über einen Prefect Flow und die Initialisierung des Redis-Caches. Stoppt den Scheduler beim Herunterfahren.
* **Routing**: Bindet API-Router für Sensoren und Vorhersagen ein.
* **Gesundheitscheck**: Stellt einen einfachen Gesundheitscheck-Endpunkt bereit.
* **Statische Dateien**: Dient statische Dateien (z.B. Favicon) aus.

### Importe und Konfiguration
* `FastAPI`, `APIRouter`, `status`: FastAPI-Kernkomponenten.
* `logging`: Für die Protokollierung von Ereignissen.
* `asyncio`: Für asynchrone Operationen, insbesondere im `lifespan`-Kontext.
* `contextlib.asynccontextmanager`: Für den `lifespan`-Manager.
* `starlette.concurrency.run_in_threadpool`: Für das Ausführen blockierender I/O in einem Thread-Pool (wird hier deklariert, aber nicht direkt aufgerufen).
* `apscheduler.schedulers.asyncio.AsyncIOScheduler`, `apscheduler.triggers.interval.IntervalTrigger`: Für die Zeitplanung von Aufgaben (der Scheduler wird initialisiert, aber aktuell nicht verwendet, um Aufgaben hinzuzufügen).
* `datetime.timedelta`: Für Zeitintervalle (verwendet mit APScheduler).
* `fastapi.staticfiles.StaticFiles`, `starlette.responses.FileResponse`: Zum Servieren statischer Dateien.
* `utils.db_session.SessionLocal`: Für den Zugriff auf die Datenbank-Session.
* `core.config.settings`: Anwendungseinstellungen (z.B. Datenbank-Konfiguration, Redis-Host, Sensor-Box-ID).
* `shared.crud.crud_sensor`: CRUD-Operationen für Sensor-Datenbankmodelle.
* `api.v1.endpoints.sensors`, `api.v1.endpoints.predictions`: Router für die API-Endpunkte der Version 1.
* `fastapi_cache.FastAPICache`, `fastapi_cache.backends.redis.RedisBackend`, `redis.asyncio as aioredis`: Für die Konfiguration des FastAPI-Caches mit Redis.
* `prefect.deployments.run_deployment`, `prefect.exceptions.ObjectNotFound`: Zum Starten von Prefect Deployments.

### Globale Variablen und Initialisierung
* `logger`: Ein Logger-Objekt für die Anwendung.
* `BASE_DIR`, `project_root`, `STATIC_DIR`, `FAVICON_PATH`: Pfad-Konfigurationen für statische Dateien.
* `scheduler`: Eine Instanz von `AsyncIOScheduler`.

### `lifespan` Kontextmanager
Der `lifespan`-Kontextmanager handhabt Aufgaben, die beim Starten und Herunterfahren der FastAPI-Anwendung ausgeführt werden sollen.
* **Startup-Logik**:
    * **Datenbank-Check**: Überprüft, ob die konfigurierte `SENSOR_BOX_ID` bereits in der Datenbank existiert.
    * **Initiale Datenaufnahme (Prefect Flow)**: Wenn die SensorBox nicht in der Datenbank gefunden wird, versucht der Lebenszyklus, einen Prefect Flow namens `"data_ingestion_flow/timeseries-data-ingestion"` zu starten.
        * Es gibt eine Wiederholungslogik mit maximal 10 Versuchen und einer Verzögerung von 3 Sekunden, um auf das Deployment im Prefect Server zu warten.
        * Parameter wie `box_id`, `initial_fetch_days` und `fetch_chunk_days` werden an den Flow übergeben.
    * **Redis-Cache-Initialisierung**: Stellt eine Verbindung zu Redis her (`aioredis.from_url`) und initialisiert `FastAPICache` mit dem Redis-Backend.
* **Shutdown-Logik**:
    * Stoppt den `AsyncIOScheduler`, falls er läuft.

### FastAPI-Anwendung (`app`)
* Die FastAPI-Anwendung wird mit einem Titel (`"Umweltmonitoring Backend"`) und einer Version (`"0.1.0"`) initialisiert.
* Der `lifespan`-Kontextmanager wird an die App gebunden.

### Endpunkte
* **`/favicon.ico`**: Ein Endpunkt, der das Favicon aus dem `STATIC_DIR` dient.
* **`/assets`**: Ein Mount-Punkt für statische Dateien im `STATIC_DIR`.
* **`/api/health`**: Ein einfacher Gesundheitscheck-Endpunkt, der `{"status": "ok"}` zurückgibt.
* **API-Router**:
    * `sensors_router` wird unter `/api/v1` eingebunden, mit dem Tag `"sensors"`.
    * `predictions_router` wird unter `/api/v1` eingebunden, mit dem Tag `"predictions"`.
    * `health_router` wird unter `/api` eingebunden, mit dem Tag `"health-check"`.

### Fehlerbehandlung
* Der `lifespan`-Manager fängt kritische Fehler während des Startups ab, loggt sie und fährt den Scheduler herunter, bevor er eine `RuntimeError`-Ausnahme auslöst, um das Scheitern des Starts zu signalisieren.
* Die Wiederholungslogik für den Prefect Flow Run fängt `ObjectNotFound` (wenn das Deployment nicht sofort verfügbar ist) und andere generische `Exception`s ab.

---

# backend/utils

## 1. `db_session.py`

Diese Datei konfiguriert die SQLAlchemy-Datenbank-Engine und stellt eine Funktion zum Abrufen einer Datenbank-Session bereit.

### Beschreibung
Die `db_session.py`-Datei ist für die Einrichtung der Datenbankverbindung für die FastAPI-Anwendung verantwortlich. Sie verwendet die in `core.config.settings` definierten Datenbank-URLs, um eine SQLAlchemy Engine zu erstellen, und konfiguriert eine Session-Fabrik (`SessionLocal`). Außerdem bietet sie eine Dependency-Injektions-Funktion (`get_db`) für FastAPI, um Datenbank-Sessions sicher zu verwalten.

### Importe
* `sqlalchemy.create_engine`: Zum Erstellen der Datenbank-Engine.
* `sqlalchemy.orm.sessionmaker`: Zum Erstellen einer Session-Fabrik.
* `core.config.settings`: Die Anwendungseinstellungen, die die `DATABASE_URL` enthalten.

### Globale Variablen
* `engine`: Die SQLAlchemy Engine-Instanz, die beim Laden des Moduls erstellt wird. Sie ist mit `pool_pre_ping=True` konfiguriert, um die Konnektivität des Pools zu überprüfen.
* `SessionLocal`: Eine SQLAlchemy Session-Fabrik, die an die `engine` gebunden ist. Sie ist so konfiguriert, dass sie `autocommit=False` und `autoflush=False` verwendet, was manuelle Commits und Flushes erfordert und Transaktionen expliziter macht.

### Funktionen
* `get_db()`:
    * **Beschreibung**: Eine Generatorfunktion, die als FastAPI-Dependency verwendet wird. Sie stellt eine frische Datenbank-Session für jeden Request bereit und stellt sicher, dass die Session nach Abschluss des Requests (oder im Fehlerfall) ordnungsgemäß geschlossen wird.
    * **Logik**:
        1.  Erstellt eine neue Session aus `SessionLocal`.
        2.  `yield`t die Session, wodurch der Request-Handler ausgeführt werden kann.
        3.  Im `finally`-Block wird `db.close()` aufgerufen, um die Session zu schließen und Ressourcen freizugeben, unabhängig davon, ob der Request erfolgreich war oder ein Fehler auftrat.

### Zweck
* Zentralisierte Datenbank-Initialisierung.
* Bereitstellung einer thread-sicheren und request-spezifischen Datenbank-Session für FastAPI-Endpunkte.
* Sicherstellung des ordnungsgemäßen Ressourcenmanagements der Datenbankverbindungen.

---

## 2. `keybuilder.py`

Diese Datei enthält mehrere Hilfsfunktionen, die dynamische Cache-Schlüssel für verschiedene API-Endpunkte der FastAPI-Anwendung generieren.

### Beschreibung
Die `keybuilder.py`-Datei stellt eine Sammlung von Funktionen bereit, die darauf ausgelegt sind, konsistente und eindeutige Cache-Schlüssel zu erstellen. Diese Schlüssel werden von `fastapi-cache` verwendet, um API-Antworten zu speichern und wiederherzustellen, wodurch die Notwendigkeit reduziert wird, wiederholt teure Operationen wie Datenbankabfragen oder externe API-Aufrufe durchzuführen. Jeder Schlüssel berücksichtigt die relevanten Parameter des API-Endpunkts, um sicherzustellen, dass unterschiedliche Anfragen unterschiedliche Cache-Einträge erhalten.

### Hilfsfunktionen
* `_format_datetime(dt: datetime | None) -> str`: Eine private Hilfsfunktion, die ein `datetime`-Objekt in einen ISO-formatierten String umwandelt oder "None" zurückgibt, wenn das Objekt `None` ist. Dies gewährleistet eine konsistente Datumsformatierung in den Cache-Schlüsseln.

### Cache-Schlüssel-Builder-Funktionen
Alle Schlüssel-Builder-Funktionen folgen einem ähnlichen Muster:
* Sie nehmen `func`, `*args`, `**kwargs` als Eingabe an. `func` ist die gecachte Funktion (der API-Endpunkt), und `kwargs` enthält die Parameter des Endpunkts.
* Ein `prefix` wird basierend auf dem Modul und Namen der Funktion generiert (`{func.__module__}:{func.__name__}`).
* Die spezifischen Endpunkt-Parameter werden aus `kwargs.get('kwargs', {})` extrahiert.
* Der `cache_key` wird durch Konkatenierung des Präfixes und der relevanten Parameter-Werte erstellt.
* Der generierte Schlüssel wird zu Debug-Zwecken geloggt.

Hier sind die spezifischen Schlüssel-Builder:

* **`aggregate_key_builder(func, *args, **kwargs) -> str`**:
    * **Zweck**: Erstellt einen Cache-Schlüssel für aggregierte Sensordaten.
    * **Parameter im Schlüssel**: `sensor_id`, `from_date`, `to_date`, `interval`, `aggregation_type`, `smoothing_window`, `interpolation_method`.

* **`list_sensors_key_builder(func, *args, **kwargs) -> str`**:
    * **Zweck**: Erstellt einen Cache-Schlüssel für die Auflistung von Sensoren.
    * **Parameter im Schlüssel**: `skip`, `limit`, `name_filter`.

* **`box_detail_key_builder(func, *args, **kwargs) -> str`**:
    * **Zweck**: Erstellt einen Cache-Schlüssel für die Details einer Sensorbox.
    * **Parameter im Schlüssel**: `box_id`.

* **`sensors_for_box_key_builder(func, *args, **kwargs) -> str`**:
    * **Zweck**: Erstellt einen Cache-Schlüssel für Sensoren, die zu einer bestimmten Box gehören.
    * **Parameter im Schlüssel**: `box_id`, `skip`, `limit`.

* **`summary_stats_key_builder(func, *args, **kwargs) -> str`**:
    * **Zweck**: Erstellt einen Cache-Schlüssel für zusammenfassende Statistiken.
    * **Parameter im Schlüssel**: `sensor_id`, `from_date`, `to_date`.

* **`latest_data_key_builder(func, *args, **kwargs) -> str`**:
    * **Zweck**: Erstellt einen Cache-Schlüssel für die neuesten Sensordaten.
    * **Parameter im Schlüssel**: `sensor_id`.

* **`raw_data_key_builder(func, *args, **kwargs) -> str`**:
    * **Zweck**: Erstellt einen Cache-Schlüssel für Rohsensordaten.
    * **Parameter im Schlüssel**: `sensor_id`, `from_date`, `to_date`, `skip`, `limit`.

### Zweck
* **Caching-Effizienz**: Ermöglicht `fastapi-cache`, die Antworten von Endpunkten basierend auf allen relevanten Anfragelparametern eindeutig zu identifizieren und zwischenzuspeichern.
* **Reduzierung der Last**: Minimiert die Notwendigkeit, wiederholt auf die Datenbank oder externe APIs zuzugreifen, wenn dieselbe Anfrage erneut gestellt wird.
* **Wartbarkeit**: Zentralisiert die Logik zur Schlüsselgenerierung, was die Verwaltung und Fehlerbehebung von Caching-Problemen erleichtert.

---

## 3. `data_transformations.py`

Diese Datei enthält eine Funktion zur Durchführung von Feature Engineering und zur Vorbereitung von historischen Sensordaten für die Vorhersage.

### Funktion
`create_features_for_prediction(historical_df: pd.DataFrame) -> pd.DataFrame`

### Beschreibung
Die Funktion `create_features_for_prediction` nimmt einen DataFrame mit historischen Temperaturdaten entgegen und wendet eine Reihe von Feature-Engineering-Schritten an. Ziel ist es, ein Feature-Set zu erstellen, das für die Eingabe in ein Machine-Learning-Vorhersagemodell geeignet ist. Die Funktion gibt die Features für den letzten verfügbaren Zeitpunkt zurück, was typisch für Inferenz-Szenarien ist.

### Parameter
* `historical_df` (pd.DataFrame): Ein Pandas DataFrame, das stündliche historische Temperaturdaten enthält. Es wird erwartet, dass es einen `DatetimeIndex` und eine Spalte namens `'temperatur'` hat.

### Rückgabewert
* `pd.DataFrame`: Ein DataFrame mit einer einzigen Zeile, die alle generierten Features für den letzten verfügbaren Zeitstempel in den Eingabedaten enthält.

### Konstanten
* `TIMEZONE` (str): Die Zeitzone, in die die Daten konvertiert werden sollen (Standard: `"Europe/London"`).

### Logik
1.  **Zeitzonen-Korrektur**: Stellt sicher, dass der Index des Eingabe-DataFrames zeitzonen-bewusst ist und in die konfigurierte `TIMEZONE` konvertiert wird.
2.  **Externe Features**: Ruft Solar-Features (`get_solar_features`) und Wetter-Features (`get_weather_features`) für den relevanten Zeitbereich ab und verbindet diese mit dem Haupt-DataFrame.
3.  **Zeit-Features**: Erstellt `hour_sin` und `hour_cos` aus der Stunde des Tages, um die zyklische Natur der Zeit zu erfassen.
4.  **Lag-Features**: Erzeugt verzögerte Versionen der `'temperatur'`-Spalte (z.B. 1, 2, 3, 24 Stunden zurück) und ausgewählter externer Features (Wettertemperatur, Globalstrahlung, Bewölkung).
5.  **Rolling Window Features**: Berechnet gleitende Durchschnitte und Standardabweichungen der Temperatur über verschiedene Zeitfenster (z.B. 3, 6, 24, 48, 72, 168 Stunden). Hierbei wird `shift(1)` verwendet, um sicherzustellen, dass die gleitenden Statistiken keine zukünftigen Daten enthalten.
6.  **Temperaturdifferenzen**: Berechnet die Differenz der Temperatur über verschiedene Zeitintervalle (z.B. 1, 3, 6, 12, 24 Stunden).
7.  **Imputation**: Führt eine lineare Interpolation durch, um fehlende Werte (z.B. durch Joins oder `shift`-Operationen) aufzufüllen. Anschließend werden verbleibende NaN-Werte (z.B. am Anfang des DataFrames) mit der nächstfolgenden gültigen Beobachtung gefüllt (`bfill`).
8.  **Spaltenbereinigung**: Entfernt die ursprüngliche `'temperatur'`-Spalte, da sie nicht Teil des Feature-Sets sein soll.
9.  **Letzte Zeile Extraktion**: Gibt die letzte Zeile des verarbeiteten DataFrames zurück, die alle Features für den neuesten verfügbaren Zeitpunkt enthält.

### Abhängigkeiten
* `utils.feature_enhancer.get_solar_features`: Zum Abrufen von Solar-Features.
* `utils.feature_enhancer.get_weather_features`: Zum Abrufen von Wetter-Features.

### Zweck
* Bereitstellung eines konsistenten Feature-Engineering-Prozesses für die Vorhersagephase.
* Sicherstellung, dass die Eingabedaten für das ML-Modell die gleiche Struktur und Qualität wie die Trainingsdaten aufweisen.

---

## 4. `feature_enhancer.py`

Diese Datei enthält Funktionen zur Berechnung zusätzlicher Features aus geografischen und Wetterdaten, die zur Verbesserung von Machine-Learning-Modellen dienen.

### Konstanten
* `LATITUDE` (float): Breitengrad des Standorts (Standard: `52.019364`).
* `LONGITUDE` (float): Längengrad des Standorts (Standard: `-1.73893`).
* `TIMEZONE` (str): Zeitzone des Standorts (Standard: `"Europe/London"`).

### Funktionen
* `get_solar_features(df_index: pd.DatetimeIndex) -> pd.DataFrame`
* `get_weather_features(start_date: str, end_date: str) -> Optional[pd.DataFrame]`

### Beschreibung

#### `get_solar_features()`
Berechnet Sonnenstand-Features (Höhe über dem Horizont und Azimut) für jeden Zeitstempel in einem gegebenen Pandas DatetimeIndex unter Verwendung der `pvlib`-Bibliothek und den konfigurierten Geokoordinaten. Die Werte werden in ein für ML-Modelle geeignetes Format transformiert (z.B. Sinus/Kosinus-Transformation für zyklische Werte).

#### `get_weather_features()`
Ruft historische Wetterdaten (Luftfeuchtigkeit, Bewölkung, Windgeschwindigkeit, Globalstrahlung) von der Open-Meteo Archive API für einen angegebenen Datumsbereich ab. Die abgerufenen Daten werden in ein Pandas DataFrame konvertiert und für die Nutzung in ML-Modellen vorbereitet (z.B. Umbenennung von Spalten, Zeitzonen-Handhabung).

### Logik

#### `get_solar_features()`
1.  Erstellt ein `pvlib.location.Location`-Objekt mit den Geodaten.
2.  Verwendet `location.get_solarposition()` um die Sonnenposition für jeden Zeitstempel im `df_index` zu berechnen.
3.  Wählt relevante Spalten aus (`apparent_elevation`, `azimuth`) und benennt sie um.
4.  Transformiert `solar_elevation` mit der Sinusfunktion und `solar_azimuth` in Sinus-/Kosinus-Paare, um zyklische Abhängigkeiten für Modelle besser abzubilden und die Werte zu normalisieren.

#### `get_weather_features()`
1.  Definiert die API-URL für Open-Meteo und die benötigten Wettervariablen (`hourly` parameters).
2.  Führt einen HTTP GET-Request an die Open-Meteo API aus und übergibt die Datumsbereiche und Parameter.
3.  Überprüft den HTTP-Statuscode (`raise_for_status`).
4.  Konvertiert die JSON-Antwort in ein Pandas DataFrame.
5.  Setzt den 'time'-Index und konvertiert ihn in die konfigurierte Zeitzone (`TIMEZONE`), wobei Besonderheiten wie Sommer-/Winterzeitübergänge berücksichtigt werden.
6.  Benennt die Spalten für eine bessere Lesbarkeit und Konsistenz um.

### Fehlerbehandlung
* `get_weather_features` fängt `requests.exceptions.RequestException` ab und gibt `None` zurück, falls ein Fehler beim Abrufen der Wetterdaten auftritt.

---

# backend/custom_types/`prediction.py`

Diese Datei definiert das SQLAlchemy-Modell `TrainedModel`, das zur Speicherung von Metadaten und Metriken trainierter Zeitreihen-Vorhersagemodelle in einer Datenbank verwendet wird.

### Klassenname
`TrainedModel`

### Beschreibung
Das `TrainedModel`-Modell ist eine SQLAlchemy-Klasse, die die Struktur der `trained_models`-Tabelle in der Datenbank abbildet. Sie dient dazu, wichtige Informationen über jedes trainierte ML-Modell zu persistieren, einschließlich seiner Identifikation, des Speicherpfads, der Trainingsmetriken und der Leistungsmetriken aus der Validierung. Das Modell unterstützt automatische Versionierung über die `version_id`-Spalte.

### Tabellenname
`trained_models`

### Spalten (Attribute)
* `id` (Integer, Primary Key): Eindeutiger Bezeichner des Modelleintrags.
* `model_name` (String(255), Not Null, Index): Der Name des Modells.
* `forecast_horizon_hours` (Integer, Not Null, Index): Der Vorhersagehorizont in Stunden, für den dieses Modell trainiert wurde.
* `model_path` (String(512), Not Null, Unique): Der Dateipfad, unter dem das trainierte Modell gespeichert ist. Dies muss eindeutig sein.
* `version_id` (Integer, Not Null): Die Versionsnummer des Modells. Diese Spalte wird für die automatische Optimistic Concurrency Control (OCC) von SQLAlchemy verwendet.
* `last_trained_at` (DateTime, Timezone True, Server Default: `func.now()`, On Update: `func.now()`): Zeitstempel des letzten Trainings oder der letzten Aktualisierung des Modelleintrags.
* `training_duration_seconds` (Float, Nullable): Die Dauer des Trainingsprozesses in Sekunden.
* `val_mae` (Float, Nullable): Mean Absolute Error (MAE) aus der Validierung.
* `val_rmse` (Float, Nullable): Root Mean Squared Error (RMSE) aus der Validierung.
* `val_mape` (Float, Nullable): Mean Absolute Percentage Error (MAPE) aus der Validierung.
* `val_r2` (Float, Nullable): R-squared (Bestimmtheitsmaß) aus der Validierung.

### Besonderheiten
* **Automatische Versionierung**: Die `version_id`-Spalte ist als Versionszähler für SQLAlchemy konfiguriert (`__mapper_args__ = {'version_id_col': version_id}`). Dies ermöglicht Optimistic Concurrency Control, um Dateninkonsistenzen bei gleichzeitigen Schreibzugriffen zu vermeiden.
* **Zeitstempel-Automatisierung**: `last_trained_at` wird beim Erstellen und jeder Aktualisierung des Eintrags automatisch mit dem aktuellen Zeitstempel versehen.
* **Indizes**: `model_name` und `forecast_horizon_hours` sind indiziert, um effiziente Abfragen zu ermöglichen.
* **Eindeutiger Modellpfad**: `model_path` muss eindeutig sein, um sicherzustellen, dass jeder Modelleintrag auf einen spezifischen, einmaligen Dateipfad verweist.

---

# 1. backend/core/`config.py`

Diese Datei definiert die Anwendungseinstellungen unter Verwendung von Pydantic-Settings und lädt Umgebungsvariablen für die Datenbank- und Redis-Konfiguration.

### Klassenname
`Settings`

### Beschreibung
Die `Settings`-Klasse erbt von Pydantic's `BaseSettings` und wird verwendet, um Umgebungsvariablen und Standardwerte für die Anwendungskonfiguration zu verwalten. Sie ist speziell für Datenbank-, Redis- und Prefect-Verbindungsdetails konfiguriert und generiert automatisch die `DATABASE_URL` und `MAINTENANCE_DATABASE_URL` aus den einzelnen Komponenten.

### Attribute (Konfigurationen)
* `DB_USER` (str): Datenbank-Benutzername.
* `DB_PASSWORD` (str): Datenbank-Passwort.
* `DB_HOST` (str): Datenbank-Host.
* `DB_PORT` (str, Standard: `"5432"`): Datenbank-Port.
* `DB_NAME` (str): Name der Hauptdatenbank.
* `DATABASE_URL` (str | None): Die vollständige Datenbank-Verbindungs-URL für die Hauptdatenbank. Wird automatisch generiert, wenn nicht explizit gesetzt.
* `MAINTENANCE_DATABASE_URL` (str | None): Die Datenbank-Verbindungs-URL für die Maintenance-Datenbank (normalerweise `postgres`). Wird automatisch generiert, wenn nicht explizit gesetzt.
* `REDIS_HOST` (str, Standard: `"localhost"`): Host des Redis-Servers.
* `REDIS_PORT` (int, Standard: `6379`): Port des Redis-Servers.
* `PREFECT_DB_NAME` (str): Name der Prefect-Datenbank.
* `PREFECT_UI_SERVE_BASE` (str, Standard: `"/prefect"`): Basis-URL, unter der das Prefect UI bereitgestellt wird.
* `SENSOR_BOX_ID` (str): ID der Sensorbox, die für die initiale Datenaufnahme verwendet wird.
* `INITIAL_TIME_WINDOW_IN_DAYS` (int, Standard: `365`): Initiales Zeitfenster in Tagen für den Datenabruf einer neuen Box.
* `FETCH_TIME_WINDOW_DAYS` (int, Standard: `4`): Zeitfenster in Tagen für den chunk-weisen Datenabruf.

### Besonderheiten
* **Pydantic-Settings**: Die Klasse erbt von `BaseSettings`, was das Laden von Umgebungsvariablen (und optional aus `.env`-Dateien) automatisiert.
* **URL-Generierung**: Im `__init__`-Method wird die `DATABASE_URL` und `MAINTENANCE_DATABASE_URL` dynamisch aus den einzelnen Komponenten (`DB_USER`, `DB_PASSWORD`, etc.) erstellt, wobei das Passwort URL-sicher kodiert wird (`quote_plus`).
* **`.env`-Datei Unterstützung**: `model_config = SettingsConfigDict(env_file='../.env', env_file_encoding='utf-8', extra='ignore')` konfiguriert Pydantic, um Umgebungsvariablen aus einer `.env`-Datei zu laden. Der Pfad `../.env` deutet an, dass die `.env`-Datei eine Ebene über dem aktuellen `core`-Ordner erwartet wird (z.B. im `backend`-Ordner oder im Projekt-Root).
* **Globale Instanz**: Eine Instanz der `Settings`-Klasse (`settings = Settings()`) wird direkt in der Datei erstellt, um den einfachen Zugriff auf die Konfigurationseinstellungen zu ermöglichen.

---

# backend/api/v1/endpoints

## 1. `sensors.py`

Diese Datei definiert die API-Endpunkte für den Zugriff auf Sensoren und deren Daten. Sie bietet Funktionen zum Abrufen von Sensorboxen, einzelnen Sensoren, Rohdaten, aggregierten Daten und statistischen Zusammenfassungen.

### Beschreibung
Die `sensors.py`-Datei enthält FastAPI-Router-Definitionen, die es Clients ermöglichen, Informationen über Sensorboxen und Sensordaten abzurufen. Die Endpunkte nutzen Caching (`fastapi-cache`) zur Performance-Optimierung und interagieren mit der Datenbank über CRUD-Operationen.

### Importe
* `logging`: Für die Protokollierung von Informationen.
* `fastapi`: FastAPI-Core-Komponenten.
* `fastapi_cache.decorator.cache`: Decorator für das Caching von Endpunkt-Antworten.
* `sqlalchemy.orm.Session`: Für die Datenbank-Session.
* `datetime`: Für Datums-/Zeit-Manipulationen.
* `utils.db_session.get_db`: Dependency-Funktion zum Abrufen der Datenbank-Session.
* `shared.crud.crud_sensor`: CRUD-Operationen für Sensoren und Sensordaten.
* `shared.schemas.sensor as sensor_schema`: Pydantic-Schemas für Sensor-bezogene Datenmodelle.
* `utils.keybuilder`: Hilfsfunktionen zum Generieren von Cache-Schlüsseln.

### Router
`router = APIRouter()`: Eine Instanz von `APIRouter` zur Gruppierung der Sensor-Endpunkte.

### Endpunkte

#### `GET /sensor_boxes`
* **Zweck**: Ruft eine Liste aller Sensorboxen ab.
* **Parameter**: `skip` (int, optional), `limit` (int, optional).
* **Response Model**: `List[sensor_schema.SensorBox]`
* **Caching**: Ja, mit `list_sensors_key_builder`, expire 900 Sekunden.

#### `GET /sensor_boxes/{box_id}`
* **Zweck**: Ruft Details einer spezifischen Sensorbox ab.
* **Parameter**: `box_id` (str, Pfadparameter).
* **Response Model**: `sensor_schema.SensorBox`
* **Caching**: Ja, mit `box_detail_key_builder`, expire 900 Sekunden.
* **Fehler**: `404 Not Found`, wenn die Box nicht existiert.

#### `GET /sensor_boxes/{box_id}/sensors`
* **Zweck**: Ruft alle Sensoren ab, die zu einer spezifischen Sensorbox gehören.
* **Parameter**: `box_id` (str, Pfadparameter), `skip` (int, optional), `limit` (int, optional).
* **Response Model**: `List[sensor_schema.Sensor]`
* **Caching**: Ja, mit `sensors_for_box_key_builder`, expire 900 Sekunden.
* **Fehler**: `404 Not Found`, wenn die Box nicht existiert.

#### `GET /sensors/{sensor_id}/data`
* **Zweck**: Ruft Rohdatenpunkte für einen spezifischen Sensor ab.
* **Parameter**: `sensor_id` (str, Pfadparameter), `from_date` (datetime, optional), `to_date` (datetime, optional), `skip` (int, optional), `limit` (int, optional).
* **Response Model**: `List[sensor_schema.SensorData]`
* **Caching**: Ja, mit `raw_data_key_builder`, expire 900 Sekunden.
* **Fehler**: `404 Not Found`, wenn der Sensor nicht existiert.

#### `GET /sensors/{sensor_id}/data/daily_summary`
* **Zweck**: Ruft tägliche Zusammenfassungen (Min, Max, Avg, Count) für einen spezifischen Sensor in einem Zeitraum ab.
* **Parameter**: `sensor_id` (str, Pfadparameter), `from_date` (datetime, Query-Parameter, erforderlich), `to_date` (datetime, Query-Parameter, erforderlich).
* **Response Model**: `sensor_schema.SensorDataDailySummaries`
* **Caching**: Ja, mit `summary_stats_key_builder`, expire 900 Sekunden.
* **Fehler**: `404 Not Found`, wenn der Sensor nicht existiert.

#### `GET /sensors/{sensor_id}/stats/`
* **Zweck**: Ruft statistische Kennzahlen (Avg, Min, Max, Count, StdDev) für einen spezifischen Sensor in einem Zeitraum ab.
* **Parameter**: `sensor_id` (str, Pfadparameter), `from_date` (datetime, Query-Parameter, erforderlich), `to_date` (datetime, Query-Parameter, erforderlich).
* **Response Model**: `sensor_schema.SensorDataStatistics`
* **Caching**: Ja, mit `summary_stats_key_builder`, expire 900 Sekunden.
* **Fehler**: `404 Not Found`, wenn der Sensor nicht existiert.

#### `GET /sensors/{sensor_id}/data/aggregate/`
* **Zweck**: Ruft aggregierte Daten für einen spezifischen Sensor mit flexiblem Intervall und Aggregationstyp ab. Unterstützt optional Glättung und Interpolation.
* **Parameter**: `sensor_id` (str, Pfadparameter), `from_date` (datetime, Query-Parameter, erforderlich), `to_date` (datetime, Query-Parameter, erforderlich), `interval` (str, erforderlich), `aggregation_type` (str, erforderlich), `smoothing_window` (int, optional), `interpolation_method` (str, optional).
* **Response Model**: `sensor_schema.SensorDataAggregatedResponse`
* **Caching**: Ja, mit `aggregate_key_builder`, expire 900 Sekunden.
* **Fehler**: `404 Not Found`, wenn der Sensor nicht existiert; `400 Bad Request` bei ungültigen Aggregationsparametern.
* **Besonderheit**: Loggt, wenn ein Fallback auf Rohdatenaggregation erfolgt, falls keine kontinuierliche Aggregation verwendet werden kann.

---

## 2. `predictions.py`

Diese Datei definiert die API-Endpunkte für den Zugriff auf trainierte ML-Modelle und zur Generierung von Temperaturvorhersagen.

### Beschreibung
Die `predictions.py`-Datei enthält FastAPI-Router-Definitionen, die es Clients ermöglichen, Informationen über trainierte Vorhersagemodelle abzurufen und aktuelle Temperaturvorhersagen zu generieren. Die Vorhersagefunktion integriert den Abruf historischer Daten, Feature Engineering und die Anwendung der trainierten Modelle.

### Importe
* `logging`: Für die Protokollierung.
* `os`, `joblib`: Für Dateisystemoperationen und das Laden von Modellen.
* `datetime`, `timedelta`, `timezone`: Für Datums-/Zeit-Manipulationen.
* `typing`: Für Type-Hints.
* `fastapi`: FastAPI-Core-Komponenten.
* `pydantic`: Für Datenvalidierungsmodelle.
* `sqlalchemy.orm.Session`: Für die Datenbank-Session.
* `pandas`, `numpy`: Für Datenmanipulation.
* `custom_types.prediction.TrainedModel`: Das SQLAlchemy-Modell für trainierte Modelle.
* `utils.db_session.get_db`: Dependency-Funktion zum Abrufen der Datenbank-Session.
* `utils.feature_enhancer`: Für Solar- und Wetter-Features.
* `utils.data_transformations.create_features_for_prediction`: Zum Erstellen von Features für die Vorhersage.
* `shared.crud.crud_sensor`: CRUD-Operationen für Sensordaten.

### Konfiguration (Konstanten)
* `MODEL_PATH` (str): Der Basispfad, unter dem die trainierten Modelle gespeichert sind (`/app/backend/models`).
* `FORECAST_HORIZON` (int): Die Anzahl der Stunden, für die eine Vorhersage generiert werden soll (`48`).
* `TEMPERATURE_SENSOR_ID` (str): Die ID des Temperatursensors, für den Vorhersagen erstellt werden (`"5faeb5589b2df8001b980307"`).
* `TIMEZONE` (str): Die Zeitzone für Datums-/Zeit-Konvertierungen (`"Europe/London"`).

### Pydantic-Modelle (für API-Antworten)
* `ModelResponse`: Beschreibt die Struktur der Daten, die für ein einzelnes trainiertes Modell zurückgegeben werden.
* `PredictionPoint`: Beschreibt einen einzelnen Datenpunkt in der Vorhersage (Zeitstempel, Wert, Typ: historisch/vorhergesagt).
* `PredictionResponse`: Beschreibt die Gesamtstruktur der Vorhersage-Antwort (Liste von `PredictionPoint`s, `last_updated`-Zeitstempel, Nachricht).

### Modell-Cache
`loaded_models = {"models": {}, "timestamp": None}`: Ein globales Dictionary zum Zwischenspeichern der geladenen Modelle, um wiederholtes Laden vom Dateisystem zu vermeiden.

### Funktionen
* `load_prediction_models(db: Session) -> Dict[int, Any]`:
    * **Zweck**: Lädt alle trainierten Modelle aus der Datenbank und den zugehörigen `.joblib`-Dateien vom Dateisystem.
    * **Logik**: Prüft, ob Modelle bereits im Cache sind und ob der Cache noch gültig ist (gültig für 15 Minuten). Wenn nicht, werden alle `TrainedModel`-Einträge aus der Datenbank abgefragt. Für jeden Datenbankeintrag wird der Dateipfad korrigiert (z.B. von einem Trainingspfad zu einem Backend-Pfad) und das Modell mit `joblib.load()` geladen. Geladene Modelle werden im `loaded_models`-Cache gespeichert.

### API-Endpunkte

#### `GET /models`
* **Zweck**: Gibt eine Liste aller trainierten Modelle und ihrer Metriken aus der Datenbank zurück.
* **Response Model**: `List[ModelResponse]`
* **Logik**: Fragt alle `TrainedModel`-Einträge ab und gibt sie sortiert nach Vorhersagehorizont zurück.

#### `GET /predictions`
* **Zweck**: Erstellt und liefert eine neue Temperaturvorhersage, kombiniert mit historischen Daten für einen Plot.
* **Response (Schema)**: Gibt ein Dictionary zurück, das den `PredictionResponse` Modellen ähnelt, aber Zeitstempel als ISO-Strings enthält.
* **Logik**:
    1.  **Modellladen**: Lädt die Vorhersagemodelle über `load_prediction_models`.
    2.  **Historische Daten abrufen**: Ruft die neuesten historischen Temperatursensordaten (letzten 31 Tage) aus der Datenbank über `crud_sensor.sensor_data.get_aggregated_data_by_sensor_id` ab. Die Daten werden stündlich aggregiert (`1h`, `avg`).
    3.  **Datenaufbereitung**: Konvertiert die abgerufenen Daten in ein Pandas DataFrame, setzt den Zeitstempel als Index und sortiert/interpoliert fehlende Werte.
    4.  **Feature Engineering**: Verwendet `create_features_for_prediction`, um die Features für den letzten verfügbaren historischen Zeitpunkt zu generieren.
    5.  **Vorhersagegenerierung**: Iteriert über den `FORECAST_HORIZON`. Für jede Stunde wird das entsprechende Modell (`models.get(h)`) verwendet, um eine Vorhersage zu treffen. Wenn ein Modell oder die Vorhersage fehlschlägt, wird `None` als Wert gesetzt. Die Zeitstempel der Vorhersagepunkte werden korrekt als UTC-`datetime`s berechnet und dann in ISO-Strings umgewandelt.
    6.  **Kombination**: Kombiniert die historischen Datenpunkte und die generierten Vorhersagepunkte zu einer einzigen Liste.
    7.  **Antwort**: Gibt ein Dictionary zurück, das diese kombinierte Liste (`plot_data`), den Zeitstempel der letzten Aktualisierung (`last_updated`) und eine Erfolgsmeldung enthält.
* **Fehlerbehandlung**: Fängt `HTTPException`s (z.B. wenn keine Modelle oder historischen Daten gefunden werden) ab und reicht sie weiter. Fängt andere unerwartete Fehler ab, loggt sie detailliert (inkl. Traceback) und gibt eine generische `500 Internal Server Error`-Antwort zurück.
* **Zeitstempel-Handling**: Stellt sicher, dass alle Zeitstempel konsistent in UTC (`datetime.now(timezone.utc)`) sind und im ISO 8601-Format für die API-Antwort konvertiert werden.

---

# ML-Services

# ml_service/custom_types/`prediction.py`

Diese Datei definiert das SQLAlchemy-Modell `TrainedModel`, das zur Speicherung von Metadaten und Metriken trainierter Zeitreihen-Vorhersagemodelle in einer Datenbank verwendet wird.

### Klassenname
`TrainedModel`

### Beschreibung
Das `TrainedModel`-Modell ist eine SQLAlchemy-Klasse, die die Struktur der `trained_models`-Tabelle in der Datenbank abbildet. Sie dient dazu, wichtige Informationen über jedes trainierte ML-Modell zu persistieren, einschließlich seiner Identifikation, des Speicherpfads, der Trainingsmetriken und der Leistungsmetriken aus der Validierung. Das Modell unterstützt automatische Versionierung über die `version_id`-Spalte.

### Tabellenname
`trained_models`

### Spalten (Attribute)
* `id` (Integer, Primary Key): Eindeutiger Bezeichner des Modelleintrags.
* `model_name` (String(255), Not Null, Index): Der Name des Modells.
* `forecast_horizon_hours` (Integer, Not Null, Index): Der Vorhersagehorizont in Stunden, für den dieses Modell trainiert wurde.
* `model_path` (String(512), Not Null, Unique): Der Dateipfad, unter dem das trainierte Modell gespeichert ist. Dies muss eindeutig sein.
* `version_id` (Integer, Not Null): Die Versionsnummer des Modells. Diese Spalte wird für die automatische Optimistic Concurrency Control (OCC) von SQLAlchemy verwendet.
* `last_trained_at` (DateTime, Timezone True, Server Default: `func.now()`, On Update: `func.now()`): Zeitstempel des letzten Trainings oder der letzten Aktualisierung des Modelleintrags.
* `training_duration_seconds` (Float, Nullable): Die Dauer des Trainingsprozesses in Sekunden.
* `val_mae` (Float, Nullable): Mean Absolute Error (MAE) aus der Validierung.
* `val_rmse` (Float, Nullable): Root Mean Squared Error (RMSE) aus der Validierung.
* `val_mape` (Float, Nullable): Mean Absolute Percentage Error (MAPE) aus der Validierung.
* `val_r2` (Float, Nullable): R-squared (Bestimmtheitsmaß) aus der Validierung.

### Besonderheiten
* **Automatische Versionierung**: Die `version_id`-Spalte ist als Versionszähler für SQLAlchemy konfiguriert (`__mapper_args__ = {'version_id_col': version_id}`). Dies ermöglicht Optimistic Concurrency Control, um Dateninkonsistenzen bei gleichzeitigen Schreibzugriffen zu vermeiden.
* **Zeitstempel-Automatisierung**: `last_trained_at` wird beim Erstellen und jeder Aktualisierung des Eintrags automatisch mit dem aktuellen Zeitstempel versehen.
* **Indizes**: `model_name` und `forecast_horizon_hours` sind indiziert, um effiziente Abfragen zu ermöglichen.
* **Eindeutiger Modellpfad**: `model_path` muss eindeutig sein, um sicherzustellen, dass jeder Modelleintrag auf einen spezifischen, einmaligen Dateipfad verweist.

---

# ml_service/flows

## 1. `data_ingestion.py`

Dieser Flow ist verantwortlich für die Aufnahme von Sensordaten von einer externen API und deren Speicherung in einer Datenbank.

### Flow-Name
`data_ingestion_flow`

### Beschreibung
Der `data_ingestion_flow` ruft Metadaten und Sensordaten für eine bestimmte Box-ID ab, synchronisiert diese mit der Datenbank und speichert die Messdaten in Chunks. Er verwendet Dask als Task-Runner für parallele Datenabrufe.

### Parameter
* `box_id` (str): Die ID der Box, für die Daten abgerufen werden sollen.
* `initial_fetch_days` (int, optional, Standard: `365`): Die Anzahl der Tage historischer Daten, die beim ersten Abruf geholt werden sollen.
* `fetch_chunk_days` (int, optional, Standard: `4`): Die Größe der Zeit-Chunks (in Tagen) für den Datenabruf.

### Verwendete Tasks
* `fetch_box_metadata`: Ruft Metadaten für die angegebene Box ab.
* `sync_box_and_sensors_in_db`: Synchronisiert Box- und Sensordaten in der Datenbank.
* `determine_fetch_window`: Bestimmt das Zeitfenster für den Datenabruf basierend auf dem aktuellen DB-Status und dem letzten Messzeitpunkt der API.
* `fetch_store_sensor_chunk`: Ruft Sensordaten für einen bestimmten Sensor innerhalb eines Zeit-Chunks ab und speichert sie.
* `update_final_box_status`: Aktualisiert den letzten Datenabruf-Zeitstempel der Box in der Datenbank.

### Ablauf
1.  Die Metadaten der angegebenen `box_id` werden abgerufen.
2.  Die Box- und Sensordaten werden mit der Datenbank synchronisiert, und der aktuelle Datenbankstatus wird ermittelt.
3.  Das Abruf-Zeitfenster (`from_date`, `to_date`) wird bestimmt. Wenn keine Datenaktualisierung notwendig ist, wird der Flow beendet.
4.  Für jeden Sensor, der mit der Box verbunden ist, werden Daten in definierten `fetch_chunk_days`-Blöcken parallel abgerufen und gespeichert.
5.  Nach erfolgreichem Abschluss aller Chunks wird der finale `last_data_fetched`-Status der Box in der Datenbank aktualisiert.

### Besonderheiten
* Verwendet `DaskTaskRunner` für die Parallelisierung der `fetch_store_sensor_chunk`-Tasks.
* Erstellt ein Markdown-Artefakt, das den Status des Datenabrufs zusammenfasst.
* Loggt detaillierte Informationen über den Fortschritt und eventuelle Fehler.

---

## 2. `ml_training.py`

Dieser Flow orchestriert den gesamten Machine-Learning-Trainingsprozess von der Datenbeschaffung bis zur Modellvalidierung und Speicherung.

### Flow-Name
`train_all_models`

### Beschreibung
Der `train_all_models`-Flow lädt Sensordaten, erstellt daraus ML-Features und trainiert separate Modelle für verschiedene Vorhersagehorizonte. Es beinhaltet eine Validierungsphase und speichert die final trainierten Modelle sowie deren Metriken in einer Datenbank.

### Parameter
* Keine direkten Flow-Parameter, Konfiguration über Konstanten und importierte `settings`.

### Konstanten
* `FORECAST_TIME_WINDOW` (int): Die maximale Anzahl von Stunden, für die Vorhersagen generiert werden (Standard: `48`).
* `MODEL_PATH` (Path): Der Basispfad, unter dem die trainierten Modelle gespeichert werden (Standard: `/app/ml_service/models`).

### Verwendete Tasks / Sub-Flows
* `initialize_database`: Stellt sicher, dass die Datenbanktabelle für Modelle existiert.
* `fetch_sensor_data_for_ml`: Ruft Sensordaten für ML-Trainingszwecke ab.
* `create_ml_features`: Erzeugt Features (z.B. Lag-Features, gleitende Durchschnitte, Zeit-Features) und teilt die Daten in Trainings- und Validierungssätze.
* `train_single_model`: Trainiert ein einzelnes Modell für einen spezifischen Vorhersagehorizont.
* `generate_validation_flow` (Sub-Flow): Führt eine Validierung der Modelle durch und erstellt einen Plot der Vorhersagen im Vergleich zu den tatsächlichen Werten.
* `_update_or_create_model_in_db`: Aktualisiert oder erstellt einen Eintrag für ein Modell in der Datenbank mit seinen Metriken.
* `_create_beautiful_markdown`: Hilfsfunktion zur Erstellung eines formatierten Markdown-Berichts der Trainingsmetriken.

### Ablauf
1.  **Datenbank-Initialisierung**: Stellt sicher, dass die `models`-Tabelle in der Datenbank existiert.
2.  **Datenbeschaffung**: Ruft Rohdaten von Sensoren ab (standardmäßig für die letzten 16 Wochen). Ein Beispiel der Rohdaten wird als Markdown-Artefakt gespeichert.
3.  **Feature Engineering**: Erzeugt ML-Features aus den Rohdaten und teilt sie in `X_train`, `X_val`, `Y_targets_train` und `Y_targets` auf. Ein Beispiel der Features und Targets wird als Markdown-Artefakt gespeichert.
4.  **Erstes Modelltraining (für Validierung)**: Modelle werden auf einem Teil der Trainingsdaten (`X_train`, `Y_targets_train`) für jeden Vorhersagehorizont bis `FORECAST_TIME_WINDOW` trainiert. Die Modelle werden im Speicher gehalten.
5.  **Validierung**: Der `generate_validation_flow` wird als Sub-Flow aufgerufen, um Vorhersagen auf dem Validierungsdatensatz (`X_val`, `y_val`) zu generieren und einen Plot zu erstellen, der als Artefakt gespeichert wird.
6.  **Zweites Modelltraining (für Forecasting)**: Modelle werden auf dem *gesamten* verfügbaren Trainingsdatensatz (`X`, `Y_targets`) für jeden Vorhersagehorizont erneut trainiert. Diese Modelle werden auf die Festplatte gespeichert.
7.  **Ergebnispersistenz**: Die Metriken und Pfade der final trainierten Modelle werden in der Datenbank aktualisiert oder neu erstellt.
8.  **Artefakt-Erstellung**: Ein Markdown-Artefakt mit einer Zusammenfassung der Trainingsmetriken für alle Horizonte wird erstellt.

### Besonderheiten
* Verwendet `DaskTaskRunner` mit 3 Workern für paralleles Modelltraining.
* Führt zwei separate Trainingsrunden durch: eine für die Validierung und eine für die spätere Verwendung im Forecasting.
* Speichert relevante Zwischenschritte und Endergebnisse als Prefect-Artefakte (z.B. Datenproben, Validierungsplots, Trainingsmetriken).
* Umfassende Fehlerbehandlung und Logging.

---

## 3. `generate_forecast.py`

Dieser Flow dient dazu, aktuelle Temperaturvorhersagen zu generieren und visuell darzustellen.

### Flow-Name
`Generate Forecast and Plot`

### Beschreibung
Der `generate_forecast_flow` lädt zuvor trainierte Modelle, ruft die aktuellsten Daten ab, erstellt Vorhersagen für die nächsten `FORECAST_TIME_WINDOW` Stunden und visualisiert diese zusammen mit historischen Daten in einem Plot, der als Markdown-Artefakt gespeichert wird.

### Parameter
* Keine Parameter, da der Flow aktuelle Daten abruft und Vorhersagen generiert.

### Konstanten
* `FORECAST_TIME_WINDOW` (int): Die Anzahl der Stunden, für die eine Vorhersage generiert werden soll (Standard: `48`).
* `MODEL_PATH` (str): Der Pfad, unter dem die trainierten Modelle gespeichert sind (Standard: `./models`).

### Verwendete Tasks
* `load_all_trained_models_task`: Lädt alle trainierten Modelle aus dem angegebenen Pfad.
* `get_latest_features_for_prediction_task`: Ruft die neuesten Sensordaten ab und bereitet die Features für die Vorhersage vor, inklusive historischer Daten für den Plot.
* `generate_all_predictions_task`: Generiert Vorhersagen für alle Horizonte unter Verwendung der geladenen Modelle und der aktuellen Features.
* `create_forecast_plot_task`: Erstellt ein Bild des Vorhersage-Plots, das historische Daten und die generierte Vorhersage zeigt.
* `create_markdown_artifact`: Speichert den generierten Plot als Base64-kodiertes Bild in einem Markdown-Artefakt.

### Ablauf
1.  **Modellladen**: Alle für die Vorhersage benötigten Modelle werden vom `MODEL_PATH` geladen. Falls keine Modelle gefunden werden, wird ein Fehler gemeldet und der Flow beendet.
2.  **Feature-Vorbereitung**: Die aktuellsten Sensordaten werden abgerufen und zu Features für die Vorhersage transformiert. Es werden auch historische Daten für die Visualisierung gesammelt.
3.  **Vorhersagegenerierung**: Unter Verwendung der geladenen Modelle und der aktuellen Features werden Vorhersagen für die nächsten `FORECAST_TIME_WINDOW` Stunden generiert.
4.  **Plot-Erstellung**: Ein Plot, der die historischen Daten und die generierte Vorhersage kombiniert, wird erstellt.
5.  **Artefakt-Speicherung**: Der Plot wird in ein Base64-kodiertes Bild umgewandelt und zusammen mit beschreibendem Text als Markdown-Artefakt in Prefect gespeichert.

### Besonderheiten
* Überprüft, ob Modelle geladen werden konnten, bevor die Vorhersage fortgesetzt wird.
* Der generierte Plot ist direkt im Prefect UI als Artefakt sichtbar.
* Verwendet `base64` Encoding, um das Bild direkt in das Markdown-Artefakt einzubetten.

---

## 4. `generate_validation.py`

Diese Datei enthält einen Prefect Flow zur Durchführung der Validierung von trainierten Machine-Learning-Modellen und zur Erstellung eines Berichts der Validierungsmetriken.

### Flow-Name
`Generate Validation, Plot`

### Beschreibung
Der `generate_validation_flow` nimmt Validierungs-Features (`X_val`), die zugehörigen tatsächlichen Werte (`y_val`) und ein Dictionary von trainierten Modellen entgegen. Er iteriert über die Validierungsdaten, generiert Vorhersagen für jeden Horizont und vergleicht diese mit den tatsächlichen Werten. Anschließend berechnet er wichtige Metriken wie Mean Absolute Error (MAE), Mean Absolute Percentage Error (MAEP) und R-squared (R2) für jeden Vorhersagehorizont. Die Ergebnisse werden in einem Markdown-Artefakt für Prefect visualisiert.

### Parameter
* `X_val` (Union[np.ndarray, pd.DataFrame, pd.Series]): Die Feature-Daten für die Validierung.
* `y_val` (Union[np.ndarray, pd.DataFrame, pd.Series]): Die tatsächlichen Zielwerte für die Validierung. Muss eine Pandas Series oder ein DataFrame mit genau einer Spalte sein.
* `trained_models` (Dict[int, Any]): Ein Dictionary, bei dem die Schlüssel die Vorhersagehorizonte in Stunden und die Werte die geladenen, trainierten Modelle sind.

### Rückgabewert
* `pd.DataFrame`: Ein Pandas DataFrame, das die berechneten Metriken (MAE, MAEP, R2) pro Vorhersagehorizont enthält.

### Konstanten
* `MODEL_PATH` (str): (Wird im Flow selbst nicht direkt verwendet, aber im Kontext der Datei deklariert) Basispfad für Modelle (Standard: `./models`).
* `FORECAST_TIME_WINDOW` (int): Die maximale Anzahl von Stunden, für die Vorhersagen und Metriken generiert werden (Standard: `48`).

### Hilfsfunktionen
* `calculate_robust_maep(y_true, y_pred)`: Eine Funktion, die einen robusten Mean Absolute Percentage Error (MAEP) berechnet. Sie filtert `NaN`-Werte und vermeidet Division durch Null durch Hinzufügen eines kleinen Offsets zum Nenner.

### Verwendete Tasks
* `generate_all_predictions_task`: Ein Task, der Vorhersagen für gegebene Features und Modelle generiert.

### Ablauf
1.  **Eingabevalidierung**: Überprüft, ob `X_val` oder `y_val` leer sind oder ob keine Modelle übergeben wurden. Stellt sicher, dass `y_val` eine Pandas Series ist.
2.  **Iterative Vorhersage**: Der Flow iteriert über jede Zeile (jeden potenziellen Startzeitpunkt) in `X_val`.
    * Für jede Zeile wird `generate_all_predictions_task` aufgerufen, um Vorhersagen für alle Horizonte ab diesem Startzeitpunkt zu generieren.
    * Die generierten Vorhersagen werden mit den entsprechenden tatsächlichen Werten aus `y_val` für jeden Horizont abgeglichen. Nur gültige (nicht-NaN) Paare von Vorhersage und tatsächlichem Wert werden gesammelt.
3.  **Metrikberechnung**: Für jeden Vorhersagehorizont (von 1 bis `FORECAST_TIME_WINDOW`):
    * Die gesammelten tatsächlichen Werte (`all_horizon_actuals[h]`) und vorhergesagten Werte (`all_horizon_predictions[h]`) werden verwendet.
    * `mean_absolute_error` und `r2_score` werden von `sklearn.metrics` verwendet.
    * `calculate_robust_maep` wird aufgerufen, um den MAEP zu berechnen.
    * Besondere Handhabung für den R2-Score, wenn die Standardabweichung der tatsächlichen Werte Null ist.
    * Die berechneten Metriken (MAE, MAEP, R2) werden in einem Dictionary `metrics_by_horizon` gespeichert.
4.  **Markdown-Artefakt**: Ein Markdown-String wird erstellt, der eine formatierte Tabelle der Metriken pro Horizont enthält.
5.  **Artefakt-Veröffentlichung**: Das Markdown-Artefakt wird über `create_markdown_artifact` in Prefect veröffentlicht.

### Fehlerbehandlung
* Gibt leere DataFrames zurück, wenn `X_val`, `y_val` oder `trained_models` leer sind.
* Fängt `TypeError` ab, wenn `y_val` nicht das erwartete Format hat.
* Fängt Fehler bei der Metrikberechnung ab und setzt die Metriken auf `np.nan`.

---

# ml_service/tasks

## 1. `predictions.py`

Diese Datei enthält den Task zum Generieren von Vorhersagen für verschiedene Horizonte unter Verwendung trainierter Modelle.

### Task-Name
`Generate All Predictions`

### Beschreibung
Der `generate_all_predictions_task` nimmt ein DataFrame mit den neuesten Features und ein Dictionary von trainierten Modellen entgegen. Er iteriert über einen definierten Vorhersagehorizont und generiert für jede Stunde eine separate Vorhersage mithilfe des entsprechenden Modells. Die Ergebnisse werden in einem Pandas DataFrame zusammengefasst.

### Parameter
* `current_features_df` (pd.DataFrame): Ein DataFrame, das die aktuellsten Features enthält, auf denen die Vorhersagen basieren sollen.
* `trained_models` (Dict[int, Any]): Ein Dictionary, bei dem die Schlüssel die Vorhersagehorizonte in Stunden (z.B. 1 für t+1h, 2 für t+2h) und die Werte die geladenen, trainierten Modelle sind.
* `forecast_window` (int): Die maximale Anzahl von Stunden, für die Vorhersagen generiert werden sollen.
* `prediction_start_time` (pd.Timestamp): Der Startzeitpunkt, ab dem die Vorhersagen generiert werden sollen. Die Zeitstempel im Ausgabe-DataFrame werden basierend auf diesem Wert und dem Horizont berechnet.

### Rückgabewert
* `pd.DataFrame`: Ein DataFrame mit zwei Spalten: `forecast_timestamp` (dem Zeitstempel der Vorhersage) und `predicted_temp` (dem vorhergesagten Temperaturwert). Der `forecast_timestamp` wird als Index gesetzt.

### Logik
1.  Es wird geprüft, ob das `current_features_df` leer ist oder keine trainierten Modelle übergeben wurden. Wenn dies der Fall ist, wird ein `ValueError` ausgelöst.
2.  Für jede Stunde im `forecast_window` (von 1 bis `forecast_window`) wird versucht, das entsprechende Modell aus dem `trained_models`-Dictionary abzurufen.
3.  Falls ein Modell für den aktuellen Horizont vorhanden ist, wird `model.predict()` aufgerufen, um eine Vorhersage zu erhalten.
4.  Die vorhergesagten Werte und die entsprechenden Zeitstempel werden gesammelt. Falls ein Fehler bei der Vorhersage auftritt oder kein Modell gefunden wird, wird `pd.NA` (oder `np.nan`) als Platzhalter verwendet.
5.  Abschließend wird ein DataFrame aus den gesammelten Vorhersagen und Zeitstempeln erstellt und der Zeitstempel als Index gesetzt.

### Fehlerbehandlung
* Fängt `ValueError` ab, wenn Eingabe-DataFrames leer sind oder keine Modelle vorhanden sind.
* Fängt allgemeine `Exception`s während der Modellvorhersage ab und setzt den Vorhersagewert auf `NaN`.
* Gibt Warnungen aus, wenn für einen bestimmten Horizont kein Modell gefunden wird.

---

## 2. `ml_training.py`

Diese Datei definiert den Task zum Trainieren eines einzelnen Machine-Learning-Modells, spezifisch eines LightGBM Regressors, inklusive Hyperparameter-Optimierung und Metrikberechnung.

### Task-Name
`Train Single Forecasting Model with LGBM`

### Beschreibung
Der `train_single_model`-Task trainiert ein LightGBM Regressionsmodell für einen bestimmten Vorhersagehorizont. Er führt eine Kreuzvalidierung mittels `TimeSeriesSplit` durch, optimiert Hyperparameter mittels `GridSearchCV` und berechnet wichtige Validierungsmetriken (MAE, RMSE, MAPE, R2). Das beste Modell wird gespeichert und ein Dictionary mit Trainingsergebnissen zurückgegeben.

### Parameter
* `X_train_df` (pd.DataFrame): DataFrame mit den Trainings-Features.
* `y_train_series` (pd.Series): Serie mit den Zielwerten für das Training.
* `horizon_hours` (int): Der Vorhersagehorizont in Stunden, für den dieses Modell trainiert wird.
* `base_save_path` (str): Der Basispfad, unter dem das trainierte Modell gespeichert werden soll.
* `return_model_object` (Optional[bool], Standard: `True`): Wenn `True`, wird neben dem Ergebnis-Dictionary auch das trainierte Modellobjekt zurückgegeben.
* `tscv_n_splits` (Optional[int], Standard: `3`): Die Anzahl der Splits für die `TimeSeriesSplit`-Kreuzvalidierung.

### Rückgabewert
* `Union[Tuple[Dict[str, Any], lgb.LGBMRegressor], Dict[str, Any]]`: Ein Dictionary mit Trainingsmetriken und Metadaten. Optional wird zusätzlich das trainierte `lgb.LGBMRegressor`-Objekt zurückgegeben, wenn `return_model_object` auf `True` gesetzt ist. Im Fehlerfall wird ein Dictionary mit der `forecast_horizon_hours` und der Fehlermeldung zurückgegeben.

### Logik
1.  Ein `LGBMRegressor`-Modell wird initialisiert und eine `TimeSeriesSplit`-Instanz für die Kreuzvalidierung erstellt.
2.  Ein `param_grid` für `GridSearchCV` wird definiert, um die besten Hyperparameter zu finden.
3.  `GridSearchCV` wird mit den definierten Parametern und Metriken (`neg_rmse`, `neg_mae`, `neg_mape`, `r2`) konfiguriert und auf den Trainingsdaten (`X_train_df`, `y_train_series`) gefittet.
4.  Nach dem Training werden die besten Parameter und das beste Estimator-Modell extrahiert.
5.  Die Validierungsmetriken (MAE, RMSE, MAPE, R2) werden manuell über alle Folds der Kreuzvalidierung berechnet, um eine konsistente Metrik zu gewährleisten.
6.  Das trainierte Modell (`best_estimator`) wird im `base_save_path` unter einem spezifischen Dateinamen (`temp_forecast_lgbm_model_h{horizon_hours}.joblib`) gespeichert.
7.  Ein Ergebnis-Dictionary mit allen relevanten Metadaten und Metriken wird erstellt und zurückgegeben.

### Fehlerbehandlung
* Fängt allgemeine `Exception`s während des Trainingsprozesses ab und gibt ein Fehler-Dictionary zurück.
* Loggt Warnungen, wenn MAE größer als RMSE ist, was auf Datenqualitätsprobleme hindeuten kann.
* Nutzt Prefect-eigene Retries, um bei temporären Problemen das Training erneut zu versuchen.

---

## 3. `persist_in_db.py`

Diese Datei enthält Tasks zur Synchronisierung von Sensorbox- und Sensordaten sowie zur Aktualisierung des finalen Status des Datenabrufs in der Datenbank.

### Task-Namen
* `Sync Box and Sensors in DB`
* `Update Final Box Status`

### Beschreibung

#### `sync_box_and_sensors_in_db`
Dieser Task ist dafür zuständig, die Metadaten einer Sensorbox und ihrer zugehörigen Sensoren in der Datenbank abzugleichen. Er prüft, ob eine Box bereits existiert, erstellt sie gegebenenfalls und synchronisiert dann die Liste ihrer Sensoren. Zudem wird das Feld `lastMeasurementAt` der Box in der Datenbank aktualisiert.

#### `update_final_box_status`
Dieser Task aktualisiert den `last_data_fetched`-Zeitstempel einer Sensorbox in der Datenbank. Er berücksichtigt die Ergebnisse der einzelnen Datenabruf-Chunks, um sicherzustellen, dass der Zeitstempel nur bis zum letzten erfolgreich verarbeiteten Datenpunkt aktualisiert wird.

### Parameter

#### `sync_box_and_sensors_in_db`
* `box_metadata` (Dict[str, Any]): Ein Dictionary, das die Metadaten der Sensorbox von der API enthält.
* `initial_fetch_days` (int): Die Anzahl der Tage, die zurückgerechnet werden sollen, um den initialen `last_data_fetched`-Zeitstempel für eine *neue* Box zu bestimmen.

#### `update_final_box_status`
* `box_id` (str): Die ID der Sensorbox, deren Status aktualisiert werden soll.
* `overall_to_date` (datetime): Das Enddatum des gesamten Abrufzeitfensters, das für die Aktualisierung verwendet werden soll, wenn alle Chunks erfolgreich waren.
* `fetch_results` (List[Dict[str, Any]]): Eine Liste von Dictionaries, die die Ergebnisse der einzelnen `fetch_store_sensor_chunk`-Tasks enthalten. Jedes Ergebnis-Dictionary sollte `success` (bool) und `last_timestamp_in_chunk` (datetime) enthalten.

### Rückgabewert

#### `sync_box_and_sensors_in_db`
* `Dict[str, Any]`: Ein Dictionary, das den aktuellen Zustand der Box in der Datenbank widerspiegelt, einschließlich `box_id`, `db_last_measurement_at`, `db_last_data_fetched` und `sensor_ids`.

#### `update_final_box_status`
* `None`

### Logik

#### `sync_box_and_sensors_in_db`
1.  Eine Datenbank-Session wird geöffnet.
2.  Es wird versucht, die Sensorbox anhand der `box_id` aus der Datenbank abzurufen.
3.  **Wenn die Box nicht existiert**: Eine neue Box wird erstellt. Der `last_data_fetched`-Zeitstempel wird initial auf `initial_fetch_days` vor dem `lastMeasurementAt` der API gesetzt. Pydantic-Schemas werden zur Validierung der Daten vor der Erstellung verwendet.
4.  **Sensorsynchronisation**: Bestehende Sensoren für die Box werden erfasst. Für jeden Sensor in den API-Metadaten wird geprüft, ob er bereits in der DB existiert. Nicht vorhandene Sensoren werden erstellt und mit der Box verknüpft.
5.  Das `lastMeasurementAt`-Feld der Box in der Datenbank wird aktualisiert, falls der Wert aus den API-Metadaten neuer ist.
6.  Ein Status-Dictionary mit relevanten DB-Informationen (inkl. aller synchronisierten `sensor_ids`) wird zurückgegeben.

#### `update_final_box_status`
1.  Der Task iteriert durch die `fetch_results`, um den spätesten erfolgreichen Zeitstempel (`latest_successful_ts`) in den abgerufenen Chunks zu finden.
2.  Eine Datenbank-Session wird geöffnet und die Sensorbox abgerufen.
3.  **Wenn alle Chunks erfolgreich waren**: `last_data_fetched` wird auf das `overall_to_date` des Flows gesetzt.
4.  **Wenn Fehler aufgetreten sind**: `last_data_fetched` wird auf den `latest_successful_ts` (oder den vorherigen Wert, falls kein neuerer Erfolg vorliegt) gesetzt, um den Fortschritt bis zum Fehlerpunkt zu speichern.
5.  Das `last_data_fetched`-Feld der Box wird in der Datenbank aktualisiert, falls ein gültiger und neuerer Zeitstempel ermittelt wurde.

### Fehlerbehandlung
* Beide Tasks nutzen Prefect-Logging und fangen `SQLAlchemyError`s sowie allgemeine `Exception`s ab, um detaillierte Fehlermeldungen zu protokollieren und den Fehler weiterzuleiten.
* `sync_box_and_sensors_in_db` prüft auf fehlende Box-IDs in Metadaten und Validierungsfehler bei der Payload-Erstellung.
* `update_final_box_status` handhabt Fälle, in denen keine Fetch-Ergebnisse vorliegen oder die Box nicht in der DB gefunden wird.

---

## 4. `fetch_data.py`

Diese Datei enthält Tasks zum Abrufen von Metadaten für Sensorboxen und von Messdaten für Sensoren von der OpenSenseMap API.

### Task-Namen
* `Fetch OpenSenseMap Box Metadata`
* `Fetch and Store Sensor Chunk`
* `Get Sensor Data for ML`

### Beschreibung

#### `fetch_box_metadata`
Ruft die Metadaten einer bestimmten Sensorbox von der OpenSenseMap API ab.

#### `fetch_store_sensor_chunk`
Holt Messdaten für einen spezifischen Sensor innerhalb eines definierten Zeitbereichs (Chunk) von der OpenSenseMap API, parst diese und speichert sie in der Datenbank.

#### `fetch_sensor_data_for_ml`
Ruft aggregierte stündliche Sensordaten für einen längeren Zeitraum (z.B. mehrere Wochen) von einer Backend-API ab und bereitet sie als Pandas DataFrame für Machine-Learning-Zwecke auf.

### Parameter

#### `fetch_box_metadata`
* `box_id` (str): Die eindeutige ID der Sensorbox.

#### `fetch_store_sensor_chunk`
* `sensor_id` (str): Die ID des Sensors, dessen Daten abgerufen werden sollen.
* `box_id` (str): Die ID der Box, zu der der Sensor gehört.
* `chunk_from_date` (datetime): Der Startzeitpunkt (inklusive) des Daten-Chunks.
* `chunk_to_date` (datetime): Der Endzeitpunkt (exklusive) des Daten-Chunks.

#### `fetch_sensor_data_for_ml`
* `weeks` (int, Standard: `8`): Die Anzahl der Wochen historischer Daten, die abgerufen werden sollen.

### Rückgabewert

#### `fetch_box_metadata`
* `Dict[str, Any]`: Ein Dictionary, das die JSON-Antwort der API mit den Metadaten der Box enthält.

#### `fetch_store_sensor_chunk`
* `Dict[str, Any]`: Ein Ergebnis-Dictionary, das `sensor_id`, `chunk_from`, `chunk_to`, `success` (bool), `points_fetched` (Anzahl der gespeicherten Punkte) und `last_timestamp_in_chunk` (der späteste Zeitstempel im Chunk) enthält.

#### `fetch_sensor_data_for_ml`
* `pd.DataFrame`: Ein Pandas DataFrame mit den Spalten `measurement_timestamp` (als Index) und `temperatur`, sortiert nach Zeitstempel.

### Logik

#### `fetch_box_metadata`
1.  Baut die API-URL für die spezifische Box-ID zusammen.
2.  Führt einen GET-Request an die OpenSenseMap API aus.
3.  Überprüft den HTTP-Statuscode und parst die JSON-Antwort.

#### `fetch_store_sensor_chunk`
1.  Initialisiert ein Ergebnis-Dictionary und formatiert die `chunk_from_date` und `chunk_to_date` für den API-Aufruf.
2.  Sendet einen GET-Request an die OpenSenseMap API, um die Sensordaten für den definierten Zeitbereich abzurufen.
3.  Iteriert durch die erhaltenen Messwerte: parst den Zeitstempel und den Wert, konvertiert den Wert zu Float und stellt sicher, dass der Zeitstempel UTC ist. Erstellt Pydantic-Schemas für jeden Datenpunkt.
4.  Verwendet `crud_sensor.sensor_data.create_multi` um die validierten Datenpunkte in einem Bulk-Insert in der Datenbank zu speichern.
5.  Aktualisiert das Ergebnis-Dictionary mit der Anzahl der gespeicherten Punkte und dem spätesten Zeitstempel im Chunk.

#### `fetch_sensor_data_for_ml`
1.  Bestimmt den Start- und Endzeitpunkt für den Datenabruf basierend auf der aktuellen Zeit und dem `weeks`-Parameter.
2.  Formuliert die API-Anfrage an den Backend-Aggregations-Endpunkt für stündliche Durchschnittswerte.
3.  Führt den GET-Request aus und verarbeitet die JSON-Antwort.
4.  Wandelt die aggregierten Daten in ein Pandas DataFrame um, benennt Spalten um und setzt den Zeitstempel als Index.

### Fehlerbehandlung
* Alle Tasks implementieren spezifische Fehlerbehandlung für `requests.exceptions` (HTTPError, ConnectionError, Timeout, RequestException) und `JSONDecodeError`.
* `fetch_store_sensor_chunk` fängt auch `ValueError`, `TypeError` und `KeyError` während des Parsens einzelner Messwerte ab und loggt Warnungen.
* `fetch_store_sensor_chunk` und `fetch_sensor_data_for_ml` nutzen Prefect-eigene Retries, um bei temporären Netzwerkproblemen erneut zu versuchen.
* Bei fehlenden Box-IDs oder leeren Daten wird ein `ValueError` ausgelöst.

---

## 5. `data_transformations.py`

Diese Datei enthält den Task zum Erstellen von Machine-Learning-Features und Zielvariablen aus stündlichen Temperaturdaten.

### Task-Name
`Create ML Features and Targets`

### Beschreibung
Der `create_ml_features`-Task transformiert ein DataFrame mit stundengenauen Temperaturdaten in ein Set von Features und entsprechenden Zielvariablen, die für das Training von Zeitreihen-Vorhersagemodellen geeignet sind. Dies beinhaltet die Generierung von Zeit-basierten Features (Sin/Cos der Stunde), Lag-Features der Temperatur und anderer relevanter Spalten, Rolling-Window-Statistiken sowie die Erstellung von Target-Variablen für verschiedene Vorhersagehorizonte.

### Parameter
* `df_hourly` (pd.DataFrame): Ein Pandas DataFrame mit stündlichen Temperaturdaten. Es muss einen `DatetimeIndex` haben und eine Spalte namens `temperatur` enthalten.

### Rückgabewert
* `Dict[str, pd.DataFrame]`: Ein Dictionary, das die folgenden Pandas DataFrames enthält:
    * `X_train`: Features für den Trainingsdatensatz.
    * `X_val`: Features für den Validierungsdatensatz.
    * `X`: Alle Features (vor der Aufteilung in Train/Val).
    * `Y_targets_train`: Zielvariablen für den Trainingsdatensatz.
    * `Y_targets`: Alle Zielvariablen (vor der Aufteilung in Train/Val).
    * `original_features_df`: Das DataFrame, das alle ursprünglichen und generierten Features sowie Targets enthält, bevor NaNs entfernt wurden.

### Konstanten
* `FORECAST_TIME_WINDOW` (int): Die maximale Anzahl von Stunden, für die Vorhersage-Targets erstellt werden (Standard: `48`).
* `LATITUDE` (float): Breitengrad für die Generierung von Solar-Features (Standard: `52.019364`).
* `LONGITUDE` (float): Längengrad für die Generierung von Solar-Features (Standard: `-1.73893`).
* `TIMEZONE` (str): Zeitzone für die Datums-/Zeitberechnungen (Standard: `"Europe/London"`).

### Logik
1.  **Validierung**: Überprüft, ob der Eingabe-DataFrame einen `DatetimeIndex` und eine `temperatur`-Spalte hat.
2.  **Externe Features**: Ruft Solar-Features (z.B. Sonneneinstrahlung) und Wetter-Features (z.B. Wettertemperatur, Bewölkung) ab und verbindet sie mit dem Haupt-DataFrame.
3.  **Zeit-Features**: Erstellt Sinus- und Kosinus-Transformationen der Stunden, um die zyklische Natur der Zeit abzubilden.
4.  **Lag-Features**: Erzeugt verzögerte (gelaggte) Versionen der `temperatur`-Spalte und ausgewählter externer Features für verschiedene Zeitverzögerungen (z.B. 1h, 24h).
5.  **Rolling Window Features**: Berechnet gleitende Durchschnitte und Standardabweichungen der Temperatur über verschiedene Fenstergrößen (z.B. 3h, 24h).
6.  **Temperaturdifferenzen**: Erstellt Features, die die Temperaturänderung über verschiedene Zeitintervalle darstellen.
7.  **Target-Variablen**: Erzeugt `target_temp_plus_Xh`-Spalten, indem die `temperatur`-Spalte um `X` Stunden in die Zukunft verschoben wird. Dies sind die Werte, die das Modell vorhersagen soll.
8.  **NaN-Entfernung**: Zeilen, die aufgrund der Feature-Generierung (z.B. durch Shifting) `NaN`-Werte enthalten, werden entfernt.
9.  **Datenaufteilung**: Die Daten werden in Feature- (`X`) und Target-DataFrames (`Y_targets`) unterteilt. Zusätzlich werden `X_train`, `X_val` und `Y_targets_train` basierend auf einem festgelegten Zeitraum für die Validierung erstellt.

### Fehlerbehandlung
* Löst `ValueError` aus, wenn der Eingabe-DataFrame nicht die erwartete Struktur (DatetimeIndex, 'temperatur'-Spalte) hat.
* Gibt eine Warnung aus, wenn nach dem Feature Engineering und der NaN-Entfernung keine Daten mehr übrig sind.

---

## 6. `load_models.py`

Diese Datei enthält den Task zum Laden von zuvor trainierten Machine-Learning-Modellen aus dem Dateisystem.

### Task-Name
`Load All Trained Models`

### Beschreibung
Der `load_all_trained_models_task` durchsucht ein angegebenes Verzeichnis nach serialisierten Modellobjekten für verschiedene Vorhersagehorizonte. Er lädt jedes gefundene Modell und speichert es in einem Dictionary, wobei der Horizont als Schlüssel dient.

### Parameter
* `model_base_path` (str): Der Basispfad des Verzeichnisses, in dem die Modelle gespeichert sind.
* `forecast_window` (int): Die maximale Anzahl von Stunden, für die Modelle geladen werden sollen (definiert den Bereich der Horizonte).

### Rückgabewert
* `Dict[int, Any]`: Ein Dictionary, bei dem die Schlüssel die Vorhersagehorizonte (z.B. 1, 2, ..., `forecast_window`) und die Werte die geladenen Modellobjekte sind. Falls ein Modell für einen Horizont nicht gefunden oder nicht geladen werden kann, ist der Wert für diesen Horizont `None` im Dictionary.

### Konstanten
* `FORECAST_TIME_WINDOW` (int): Standard-Vorhersagefenster, wenn nicht anders angegeben (Standard: `12`).
* `MODEL_PATH` (str): Standardpfad, unter dem die Modelle gespeichert sind (Standard: `"./models"`).

### Logik
1.  Initialisiert ein leeres Dictionary `trained_models`.
2.  Iteriert von Horizont `1` bis `forecast_window`.
3.  Für jeden Horizont wird ein erwarteter Dateiname (`temp_forecast_lgbm_model_h{h}.joblib`) konstruiert.
4.  Es wird geprüft, ob die Modelldatei existiert. Wenn ja, wird `joblib.load()` verwendet, um das Modell zu laden, und es wird im `trained_models`-Dictionary gespeichert.
5.  Wenn die Datei nicht existiert oder ein Fehler beim Laden auftritt, wird eine Warnung/Fehlermeldung protokolliert und der Wert für diesen Horizont im Dictionary auf `None` gesetzt.
6.  Nach dem Durchlaufen aller Horizonte wird geprüft, ob überhaupt Modelle erfolgreich geladen wurden. Wenn nicht, wird ein `FileNotFoundError` ausgelöst.

### Fehlerbehandlung
* Fängt `FileNotFoundError` ab, wenn keine Modelle geladen werden konnten.
* Fängt allgemeine `Exception`s beim Laden einzelner Modelle ab und loggt detaillierte Fehlermeldungen.

---

## 7. `plotting.py`

Diese Datei enthält einen Task zur Erstellung eines Plots, der historische Daten und Vorhersagedaten kombiniert, und gibt diesen Plot als Bytes zurück.

### Task-Name
`Create Forecast Plot`

### Beschreibung
Der `create_forecast_plot_task` generiert eine Visualisierung, die historische Temperaturdaten und eine entsprechende Temperaturvorhersage in einem einzigen Diagramm darstellt. Der erstellte Plot wird als PNG-Bild in Bytes zurückgegeben, was nützlich für die Speicherung als Artefakt oder die direkte Anzeige ist.

### Parameter
* `historical_data_df` (pd.DataFrame): Ein DataFrame mit historischen Temperaturdaten. Es sollte einen `DatetimeIndex` und eine Spalte `temperatur` enthalten.
* `forecast_df` (pd.DataFrame): Ein DataFrame mit vorhergesagten Temperaturdaten. Es sollte einen `DatetimeIndex` und eine Spalte `predicted_temp` enthalten.

### Rückgabewert
* `bytes`: Die Bytes des generierten Plots im PNG-Format.

### Logik
1.  Eine neue Matplotlib-Figur wird erstellt.
2.  Wenn `historical_data_df` nicht leer ist, werden die historischen Temperaturen geplottet.
3.  Wenn `forecast_df` nicht leer ist, werden die vorhergesagten Temperaturen geplottet, typischerweise mit einer gestrichelten Linie zur Unterscheidung.
4.  Titel, Achsenbeschriftungen, Legende und Gitterlinien werden hinzugefügt.
5.  Der Plot wird in ein `io.BytesIO`-Objekt im PNG-Format gespeichert.
6.  Das `BytesIO`-Objekt wird gelesen, um die Bild-Bytes zu erhalten, und anschließend geschlossen.

### Besonderheiten
* Verwendet `matplotlib.pyplot` für die Plot-Erstellung.
* Speichert den Plot direkt in einem In-Memory-Buffer (`io.BytesIO`), um ihn als Bytes zurückzugeben, anstatt ihn auf der Festplatte zu speichern.
* Sorgt dafür, dass die Matplotlib-Figur nach dem Speichern geschlossen wird (`plt.close()`), um Speicherlecks zu vermeiden.

---

## 8. `feature_preparation.py`

Diese Datei enthält einen Task, der die neuesten Sensordaten abruft und daraus die für die Vorhersage benötigten Features sowie historische Daten für die Visualisierung generiert.

### Task-Name
`Get Latest Features for Prediction`

### Beschreibung
Der `get_latest_features_for_prediction_task` orchestriert den Abruf aktueller Sensordaten und deren Transformation in ein Format, das für die Modellanwendung geeignet ist. Er liefert die aktuellste Feature-Zeile für die Vorhersage sowie einen Teil der historischen Daten, der für die Visualisierung der Vorhersage im Kontext der Vergangenheit nützlich ist.

### Parameter
* `fetch_data_task_fn`: Eine Funktion oder ein Prefect Task, der für den Abruf der rohen Sensordaten verantwortlich ist (z.B. `fetch_sensor_data_for_ml`).
* `create_features_task_fn`: Eine Funktion oder ein Prefect Task, der für die Erstellung von ML-Features aus den rohen Daten verantwortlich ist (z.B. `create_ml_features`).
* `lookback_days_for_plot` (int, Standard: `7`): Die Anzahl der Tage historischer Daten, die für den Plot zurückgegeben werden sollen.

### Rückgabewert
* `Tuple[pd.DataFrame, pd.DataFrame, pd.Timestamp]`: Ein Tupel, das Folgendes enthält:
    * Das neueste Feature-DataFrame (`latest_X_features`), eine einzelne Zeile, die für die aktuelle Vorhersage verwendet wird.
    * Ein DataFrame mit historischen Daten (`historical_data_for_plot`), das für die Visualisierung der Vorhersage im Kontext der Vergangenheit nützlich ist.
    * Der `prediction_start_base_time`, der den Zeitstempel des letzten bekannten Datenpunkts darstellt und als Basis für die Vorhersagestempel dient.

### Logik
1.  Ruft die neuesten stündlichen Daten über die `fetch_data_task_fn` ab.
2.  Ermittelt den aktuellsten Zeitstempel in den abgerufenen Daten (`current_time_for_features`).
3.  Ruft die `create_features_task_fn` auf, um die ML-Features aus den aktuellen Daten zu generieren.
4.  Extrahiert die *neueste Zeile* aus dem generierten Feature-DataFrame (`X_all_recent`), die die Eingabe für die Vorhersage darstellt. Falls der `current_time_for_features` nicht exakt im Index der Features gefunden wird (was durch NaN-Entfernung passieren kann), wird die allerletzte Zeile verwendet.
5.  Filtert die `historical_data_for_plot` aus den `recent_hourly_data` basierend auf dem `lookback_days_for_plot`-Parameter.

### Fehlerbehandlung
* Löst einen `ValueError` aus, wenn `fetch_data_task_fn` keine Daten zurückgibt oder wenn nach der Feature-Erstellung das Feature-DataFrame leer ist.

---

# ml_service/utils


## 1. `db_setup.py`

Diese Datei enthält die Logik zur Initialisierung des Datenbankschemas, insbesondere zur Überprüfung und Erstellung der `trained_models`-Tabelle.

### Funktion
`initialize_database()`

### Beschreibung
Die Funktion `initialize_database` prüft, ob die Datenbanktabelle `trained_models` bereits existiert. Falls die Tabelle nicht gefunden wird, erstellt sie alle Tabellen, die in der `Base.metadata` der SQLAlchemy-Deklaration definiert sind. Dies gewährleistet, dass das Datenbankschema vor der Nutzung korrekt eingerichtet ist.

### Logik
1.  Ruft eine Instanz der SQLAlchemy-Engine über `get_engine_instance()` ab.
2.  Verwendet `sqlalchemy.inspect`, um den Zustand der Datenbank zu überprüfen.
3.  Ermittelt den Tabellennamen der `TrainedModel`-Klasse.
4.  Wenn die Tabelle nicht existiert (`inspector.has_table` gibt `False` zurück), werden alle in `Base.metadata` registrierten Tabellen (`TrainedModel` ist dort registriert) in der Datenbank erstellt.
5.  Andernfalls, wenn die Tabelle bereits existiert, wird die Erstellung übersprungen.

### Abhängigkeiten
* `utils.db_utils.get_engine_instance`: Zum Abrufen der SQLAlchemy Engine.
* `custom_types.prediction.Base`, `custom_types.prediction.TrainedModel`: Das SQLAlchemy Base-Objekt und das Modell für die zu erstellende Tabelle.

---

## 2. `markdown.py`

Diese Datei enthält eine Hilfsfunktion zum Erstellen eines formatierten Markdown-Berichts aus den Trainingsergebnissen von ML-Modellen.

### Funktion
`_create_beautiful_markdown(training_results: List[Dict[str, Any]], forecast_window: int) -> str`

### Beschreibung
Die Funktion `_create_beautiful_markdown` generiert einen übersichtlichen Markdown-String, der eine Zusammenfassung der Modelltrainingsergebnisse enthält. Sie unterteilt die Ergebnisse in erfolgreich trainierte und fehlgeschlagene Modelle und stellt die Metriken der erfolgreichen Modelle in einer formatierten Tabelle dar.

### Parameter
* `training_results` (List[Dict[str, Any]]): Eine Liste von Dictionaries, wobei jedes Dictionary die Trainingsergebnisse und Metriken für ein einzelnes Modell enthält (wie sie z.B. von `ml_training.py` zurückgegeben werden).
* `forecast_window` (int): Die maximale Anzahl der Horizonte, für die Modelle trainiert werden sollten. Dies wird für die Zusammenfassung verwendet.

### Rückgabewert
* `str`: Ein Markdown-formatierter String, der den Bericht enthält.

### Logik
1.  **Leere Ergebnisse**: Prüft, ob `training_results` leer ist. Falls ja, wird ein einfacher Markdown-Text zurückgegeben.
2.  **Datenaufbereitung**: Konvertiert die Liste der Dictionaries in ein Pandas DataFrame und filtert die ersten 48 Zeilen heraus (vermutlich, da die ersten 48 Horizonte im Kontext der Validierung im Training anders behandelt werden könnten).
3.  **Zusammenfassungsabschnitt**: Zählt die Anzahl der erfolgreichen und fehlgeschlagenen Trainings und erstellt einen einleitenden Markdown-Text.
4.  **Erfolgreiche Trainings-Tabelle**:
    * Filtert die erfolgreichen Trainings aus dem DataFrame.
    * Wählt relevante Spalten aus und benennt sie für die Anzeige um.
    * Konvertiert `val_mape` von einem Dezimalwert in einen Prozentwert.
    * Formatiert die numerischen Spalten (`RMSE`, `MAE`, `MAPE`, `R²`, `Dauer`) auf eine bestimmte Anzahl von Dezimalstellen.
    * Erstellt eine Markdown-Tabelle aus dem vorbereiteten DataFrame.
5.  **Fehlgeschlagene Trainings-Tabelle**:
    * Filtert die fehlgeschlagenen Trainings aus dem DataFrame.
    * Wählt die Spalten für Horizont und Fehlermeldung aus und benennt sie um.
    * Erstellt eine Markdown-Tabelle.
6.  **Zusammensetzen**: Fügt alle erstellten Abschnitte (Titel, Zusammenfassung, erfolgreiche Tabelle, fehlgeschlagene Tabelle) zu einem finalen Markdown-String zusammen.

---

## 3. `db_utils.py`

Diese Datei stellt Dienstprogramme für die Datenbankverbindung und -session-Verwaltung mit SQLAlchemy bereit.

### Konstanten & Globale Variablen
* `DATABASE_URL` (str): Die URL der Datenbank, aus den Einstellungen geladen.
* `engine`: Die SQLAlchemy Engine-Instanz. Wird einmalig beim Laden des Moduls initialisiert.
* `SessionLocal`: Die SQLAlchemy Session-Fabrik. Wird einmalig beim Laden des Moduls initialisiert.

### Funktionen
* `get_db_session() -> Iterator[Session | None]`
* `get_engine_instance()`

### Beschreibung

#### Engine-Initialisierung
Beim Laden des Moduls versucht die Datei, eine SQLAlchemy Engine und eine Session-Fabrik (`SessionLocal`) zu erstellen. Die Engine wird mit Connection-Pooling-Parametern (`pool_pre_ping`, `pool_size`, `max_overflow`) konfiguriert, um eine effiziente und robuste Datenbankverbindung zu gewährleisten. Ein kurzer Verbindungstest wird durchgeführt.

#### `get_db_session()`
Dies ist ein Context Manager, der eine SQLAlchemy Session bereitstellt. Er handhabt das Öffnen, Committen, Rollbacken und Schließen der Datenbank-Session. Er ist dafür vorgesehen, in Prefect Tasks verwendet zu werden, um Datenbankoperationen sicher auszuführen.

#### `get_engine_instance()`
Diese Funktion gibt die global initialisierte SQLAlchemy Engine-Instanz zurück.

### Logik

#### Engine-Initialisierung (Modul-Ebene)
1.  Prüft, ob `DATABASE_URL` gesetzt ist.
2.  Wenn ja, wird `create_engine` aufgerufen, um die Engine mit spezifischen Pooling-Optionen zu erstellen.
3.  `sessionmaker` wird verwendet, um `SessionLocal` als konfigurierte Session-Fabrik zu erstellen.
4.  Ein kurzer Test der Verbindung wird durchgeführt.
5.  Bei Fehlern während der Initialisierung werden `engine` und `SessionLocal` auf `None` gesetzt und der Fehler geloggt.

#### `get_db_session()`
1.  Überprüft, ob `SessionLocal` initialisiert wurde. Falls nicht, wird ein Fehler geloggt und `None` zurückgegeben.
2.  Erstellt eine neue Session von `SessionLocal`.
3.  Verwendet einen `try...except...finally`-Block:
    * `yield session`: Gibt die Session an den aufrufenden Code zurück.
    * `session.commit()`: Nach erfolgreicher Ausführung des Blocks werden Änderungen festgeschrieben.
    * `session.rollback()`: Im Fehlerfall werden Änderungen rückgängig gemacht.
    * `session.close()`: Stellt sicher, dass die Session immer geschlossen wird, unabhängig vom Erfolg oder Misserfolg.

#### `get_engine_instance()`
1.  Prüft, ob die `engine` erfolgreich initialisiert wurde.
2.  Gibt die `engine`-Instanz zurück.

### Fehlerbehandlung
* Fängt Fehler während der `engine`-Erstellung ab und loggt diese.
* Der `get_db_session`-Context Manager fängt alle Ausnahmen ab, führt einen Rollback durch, loggt den Fehler und gibt ihn weiter.
* `get_engine_instance` löst einen `RuntimeError` aus, wenn die Engine nicht initialisiert werden konnte.

---

## 4. `feature_enhancer.py`

Diese Datei enthält Funktionen zur Berechnung zusätzlicher Features aus geografischen und Wetterdaten, die zur Verbesserung von Machine-Learning-Modellen dienen.

### Konstanten
* `LATITUDE` (float): Breitengrad des Standorts (Standard: `52.019364`).
* `LONGITUDE` (float): Längengrad des Standorts (Standard: `-1.73893`).
* `TIMEZONE` (str): Zeitzone des Standorts (Standard: `"Europe/London"`).

### Funktionen
* `get_solar_features(df_index: pd.DatetimeIndex) -> pd.DataFrame`
* `get_weather_features(start_date: str, end_date: str) -> Optional[pd.DataFrame]`

### Beschreibung

#### `get_solar_features()`
Berechnet Sonnenstand-Features (Höhe über dem Horizont und Azimut) für jeden Zeitstempel in einem gegebenen Pandas DatetimeIndex unter Verwendung der `pvlib`-Bibliothek und den konfigurierten Geokoordinaten. Die Werte werden in ein für ML-Modelle geeignetes Format transformiert (z.B. Sinus/Kosinus-Transformation für zyklische Werte).

#### `get_weather_features()`
Ruft historische Wetterdaten (Luftfeuchtigkeit, Bewölkung, Windgeschwindigkeit, Globalstrahlung) von der Open-Meteo Archive API für einen angegebenen Datumsbereich ab. Die abgerufenen Daten werden in ein Pandas DataFrame konvertiert und für die Nutzung in ML-Modellen vorbereitet (z.B. Umbenennung von Spalten, Zeitzonen-Handhabung).

### Logik

#### `get_solar_features()`
1.  Erstellt ein `pvlib.location.Location`-Objekt mit `LATITUDE`, `LONGITUDE` und `TIMEZONE`.
2.  Verwendet `location.get_solarposition()` um die Sonnenposition für jeden Zeitstempel im `df_index` zu berechnen.
3.  Wählt relevante Spalten aus (`apparent_elevation`, `azimuth`) und benennt sie um.
4.  Transformiert `solar_elevation` mit der Sinusfunktion und `solar_azimuth` in Sinus-/Kosinus-Paare, um zyklische Abhängigkeiten für Modelle besser abzubilden und die Werte zu normalisieren.

#### `get_weather_features()`
1.  Definiert die API-URL für Open-Meteo und die benötigten Wettervariablen (`hourly` parameters).
2.  Führt einen HTTP GET-Request an die Open-Meteo API aus und übergibt die Datumsbereiche und Parameter.
3.  Überprüft den HTTP-Statuscode (`raise_for_status`).
4.  Konvertiert die JSON-Antwort in ein Pandas DataFrame.
5.  Setzt den 'time'-Index und konvertiert ihn in die konfigurierte Zeitzone (`TIMEZONE`), wobei Besonderheiten wie Sommer-/Winterzeitübergänge berücksichtigt werden.
6.  Benennt die Spalten für eine bessere Lesbarkeit und Konsistenz um.

### Fehlerbehandlung
* `get_weather_features` fängt `requests.exceptions.RequestException` ab und gibt `None` zurück, falls ein Fehler beim Abrufen der Wetterdaten auftritt.

---

## 5. `config.py`

Diese Datei definiert die Anwendungseinstellungen unter Verwendung von Pydantic-Settings und lädt Umgebungsvariablen für die Datenbankkonfiguration.

### Klasse
`Settings`

### Beschreibung
Die `Settings`-Klasse erbt von Pydantic's `BaseSettings` und wird verwendet, um Umgebungsvariablen und Standardwerte für die Anwendungskonfiguration zu verwalten. Sie ist speziell für Datenbankverbindungsdetails konfiguriert und generiert automatisch die `DATABASE_URL` und `MAINTENANCE_DATABASE_URL` aus den einzelnen Komponenten.

### Attribute (Konfigurationen)
* `DB_USER` (str): Datenbank-Benutzername.
* `DB_PASSWORD` (str): Datenbank-Passwort.
* `DB_HOST` (str): Datenbank-Host.
* `DB_PORT` (str, Standard: `"5432"`): Datenbank-Port.
* `DB_NAME` (str): Name der Hauptdatenbank.
* `DATABASE_URL` (str | None): Die vollständige Datenbank-Verbindungs-URL für die Hauptdatenbank. Wird automatisch generiert, wenn nicht explizit gesetzt.
* `MAINTENANCE_DATABASE_URL` (str | None): Die Datenbank-Verbindungs-URL für die Maintenance-Datenbank (normalerweise `postgres`). Wird automatisch generiert, wenn nicht explizit gesetzt.
* `INITIAL_TIME_WINDOW_IN_DAYS` (int, Standard: `365`): Initiales Zeitfenster in Tagen für den Datenabruf.
* `FETCH_TIME_WINDOW_DAYS` (int, Standard: `2`): Zeitfenster in Tagen für den chunk-weisen Datenabruf.

### Besonderheiten
* **Pydantic-Settings**: Die Klasse erbt von `BaseSettings`, was das Laden von Umgebungsvariablen (und optional aus `.env`-Dateien) automatisiert.
* **URL-Generierung**: Im `__init__`-Method wird die `DATABASE_URL` und `MAINTENANCE_DATABASE_URL` dynamisch aus den einzelnen Komponenten (`DB_USER`, `DB_PASSWORD`, etc.) erstellt, wobei das Passwort URL-sicher kodiert wird.
* **`.env`-Datei Unterstützung**: `model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')` konfiguriert Pydantic, um Umgebungsvariablen aus einer `.env`-Datei zu laden.
* **Globale Instanz**: Eine Instanz der `Settings`-Klasse (`settings = Settings()`) wird direkt in der Datei erstellt, um den Zugriff auf die Konfigurationseinstellungen zu erleichtern.

---

## 6. `fetch_window.py`

Diese Datei enthält einen Task, der das Zeitfenster für den Abruf von Sensordaten bestimmt.

### Task-Name
`Determine Fetch Time Window`

### Beschreibung
Der `determine_fetch_window`-Task berechnet das Start- (`from_date`) und End-Datum (`to_date`) für den Datenabruf von Sensoren. Die Logik basiert auf dem `lastMeasurementAt` der API und dem `db_last_data_fetched`-Zeitstempel aus der Datenbank. Er stellt sicher, dass nur neue Daten abgerufen werden und verhindert redundante Abrufe.

### Parameter
* `db_box_state` (Dict[str, Any]): Ein Dictionary, das den aktuellen Status der Sensorbox in der Datenbank enthält. Es sollte `box_id`, `db_last_measurement_at` und `db_last_data_fetched` enthalten.
* `api_last_measurement_str` (str | None): Der String des letzten Messzeitpunkts, wie von der API gemeldet.

### Rückgabewert
* `Tuple[datetime | None, datetime | None]`: Ein Tupel, das den Start- und Endzeitpunkt des Abruf-Zeitfensters enthält. Wenn keine neuen Daten abgerufen werden müssen, wird `(None, None)` zurückgegeben.

### Logik
1.  **Bestimmung des Enddatums (`to_date`)**:
    * Vergleicht den `api_last_measurement_dt` mit der aktuellen UTC-Zeit (`now_utc`).
    * Das `target_to_date` ist entweder der API-Zeitstempel oder `now_utc`.
    * Das `actual_to_date` ist das Minimum aus `target_to_date` und `now_utc`, um sicherzustellen, dass nicht in die Zukunft abgefragt wird.
    * Stellt sicher, dass das `actual_to_date` Zeitzonen-aware (UTC) ist.
2.  **Bestimmung des Startdatums (`from_date`)**:
    * Verwendet den `db_last_data_fetched`-Wert aus `db_box_state`.
    * Wandelt diesen Wert in ein Zeitzonen-aware `datetime`-Objekt um.
3.  **Prüfung auf Notwendigkeit des Abrufs**:
    * Wenn `actual_from_date` existiert und größer oder gleich `actual_to_date` ist, sind die Daten aktuell, und es wird `(None, None)` zurückgegeben.
    * Andernfalls wird das berechnete `actual_from_date` und `actual_to_date` zurückgegeben.

### Fehlerbehandlung
* Protokolliert Warnungen, wenn `db_last_data_fetched` einen unerwarteten Typ hat.
* Stellt sicher, dass alle Datums-/Zeitobjekte im UTC-Format vorliegen, um Konsistenz zu gewährleisten.

---

## 7. `training.py`

Diese Datei enthält eine Hilfsfunktion zum Aktualisieren oder Erstellen von Modelleinträgen in der Datenbank.

### Funktion
`_update_or_create_model_in_db(db: Session, result: dict, logger)`

### Beschreibung
Die Funktion `_update_or_create_model_in_db` implementiert eine Upsert-Logik für Modelleinträge in der Datenbank. Sie sucht nach einem bestehenden `TrainedModel`-Eintrag für einen spezifischen Vorhersagehorizont. Wenn ein Eintrag gefunden wird, werden dessen Metadaten und Metriken aktualisiert. Andernfalls wird ein neuer `TrainedModel`-Eintrag in der Datenbank erstellt.

### Parameter
* `db` (Session): Die SQLAlchemy-Datenbanksession.
* `result` (dict): Ein Dictionary, das die Trainingsergebnisse und Metadaten eines Modells enthält (z.B. den Horizont, Pfad, Metriken).
* `logger`: Ein Logger-Objekt (z.B. von Prefect's `get_run_logger()`) zum Protokollieren von Informationen und Fehlern.

### Logik
1.  Extrahiert den `forecast_horizon_hours` aus dem `result`-Dictionary.
2.  Führt eine Datenbankabfrage aus, um zu prüfen, ob bereits ein `TrainedModel`-Eintrag für diesen Horizont existiert.
3.  **UPDATE-Pfad**: Wenn ein bestehendes Modell gefunden wird:
    * Die Attribute des `db_model`-Objekts (z.B. `model_path`, `version_id`, `training_duration_seconds`, Validierungsmetriken) werden mit den Werten aus dem `result`-Dictionary aktualisiert.
    * Der `last_trained_at`-Zeitstempel wird automatisch durch die `onupdate`-Konfiguration des `TrainedModel`-Modells in der Datenbank aktualisiert.
4.  **INSERT-Pfad**: Wenn kein bestehendes Modell gefunden wird:
    * Ein neues `TrainedModel`-Objekt wird erstellt, wobei alle relevanten Informationen aus dem `result`-Dictionary verwendet werden.
    * Das neue Modell wird der Datenbank-Session hinzugefügt (`db.add(new_model)`).

### Fehlerbehandlung
* Protokolliert einen Fehler, wenn das `result`-Dictionary den Schlüssel `forecast_horizon_hours` nicht enthält.

---

## 8. `parse_datetime.py`

Diese Datei enthält eine Hilfsfunktion zum sicheren Parsen von Datums-/Zeitstrings aus API-Antworten in zeitzonen-bewusste `datetime`-Objekte.

### Funktion
`parse_api_datetime(date_str: str | None) -> datetime | None`

### Beschreibung
Die Funktion `parse_api_datetime` versucht, einen Datums-/Zeitstring, der oft im ISO 8601-Format mit einem 'Z' für UTC (Zulu Time) endet, sicher in ein zeitzonen-bewusstes `datetime`-Objekt umzuwandeln. Sie stellt sicher, dass das resultierende `datetime`-Objekt immer auf UTC normalisiert ist.

### Parameter
* `date_str` (str | None): Der Eingabe-String, der das Datum und die Zeit enthält. Kann `None` sein.

### Rückgabewert
* `datetime | None`: Ein zeitzonen-bewusstes `datetime`-Objekt, das auf UTC normalisiert ist, oder `None`, falls der Eingabe-String leer, ungültig oder nicht parsenbar ist.

### Logik
1.  **Leere Eingabe**: Wenn `date_str` `None` oder ein leerer String ist, wird `None` zurückgegeben.
2.  **'Z' Handhabung**: Wenn der String mit 'Z' endet (was UTC anzeigt), wird das 'Z' durch `+00:00` ersetzt, um es mit `datetime.fromisoformat` kompatibel zu machen.
3.  **Parsing**: `datetime.fromisoformat` wird verwendet, um den String zu parsen.
4.  **Zeitzonen-Normalisierung**:
    * Wenn das geparste `datetime`-Objekt keine Zeitzoneninformationen hat (`dt.tzinfo is None`), wird es als UTC angenommen.
    * Anschließend wird das Objekt in die UTC-Zeitzone konvertiert (`dt.astimezone(timezone.utc)`), um Konsistenz zu gewährleisten.
5.  **Fehlerbehandlung**: Ein `try...except`-Block fängt `ValueError` oder `TypeError` ab, die während des Parsens auftreten können, und gibt in diesem Fall `None` zurück.

---

# ml_service/`prefect.yaml`

Diese Datei ist die zentrale Konfigurationsdatei für Prefect-Deployments in diesem Projekt. Sie definiert Metadaten des Projekts und dient als Blaupause für die Bereitstellung von Flows.

### Beschreibung
Die `prefect.yaml`-Datei ist eine standardmäßige Prefect-Konfigurationsdatei, die zur Verwaltung und Bereitstellung von Flows verwendet wird. Sie enthält grundlegende Projektinformationen und Platzhalter für Build-, Push-, Pull- und Deployment-Konfigurationen. In der vorliegenden Form ist sie ein Ausgangspunkt für die Definition von Deployments, die später durch Skripte oder manuelle Anpassungen gefüllt werden können.

### Abschnitte
* `name`: Der Name des Prefect-Projekts (`vorstandsvorlagen`).
* `prefect-version`: Die erforderliche Prefect-Version (`2.20.0`).
* `build`: Abschnitt für Build-bezogene Konfigurationen (z.B. Docker-Images). Aktuell auf `null` gesetzt.
* `push`: Abschnitt für Push-bezogene Konfigurationen (z.B. Upload zu Remote-Speichern). Aktuell auf `null` gesetzt.
* `pull`: Abschnitt für Pull-bezogene Konfigurationen (z.B. Klonen des Projekts von Remote-Speichern). Aktuell auf `null` gesetzt.
* `deployments`: Eine Liste von Deployment-Definitionen. Im aktuellen Zustand ist ein leeres Deployment-Template vorhanden, das Felder wie `name`, `flow_name`, `entrypoint`, `schedule` und `work_pool` enthält, die später gefüllt werden können.

### Zweck
* Dient als zentrale, versionierte Konfigurationsdatei für Prefect-Deployments.
* Kann manuell bearbeitet oder durch Prefect CLI-Befehle (`prefect deploy`) verwendet werden, um Deployments zu erstellen und zu verwalten.
* Bietet einen Überblick über die Deployments, die Teil des Projekts sind.

---

# ml_service/`run_worker.py`

Dieses Skript ist für die Einrichtung von Prefect Work Pools und Deployments über die Prefect API sowie für das Starten eines Prefect Process Workers zuständig.

### Beschreibung
Das `run_worker.py`-Skript automatisiert den Prozess des Setups der Prefect-Infrastruktur. Es interagiert direkt mit dem Prefect Server, um einen Work Pool zu erstellen (falls er nicht existiert) und mehrere Deployments für verschiedene Flows zu registrieren. Nach dem erfolgreichen Setup startet es einen lokalen `ProcessWorker`, der die Ausführung der geplanten Flow Runs überwacht und startet.

### Konfiguration (Konstanten)
* `WORK_POOL_NAME` (str): Name des zu erstellenden oder zu verwendenden Work Pools (`"timeseries"`).
* `DEPLOYMENT_NAME` (str): Name des Haupt-Deployments für die Datenaufnahme (`"timeseries-data-ingestion"`).
* `FLOW_SCRIPT_PATH` (Path): Pfad zum Flow-Skript (`./flows/data_ingestion.py`).
* `FLOW_FUNCTION_NAME` (str): Name der Flow-Funktion innerhalb des Skripts (`"data_ingestion_flow"`).
* `FLOW_ENTRYPOINT` (str): Kombinierter Entrypoint für das Haupt-Deployment (`./flows/data_ingestion.py:data_ingestion_flow`).
* `APP_BASE_PATH` (Path): Der Basispfad der Anwendung im Container (`/app/ml_service/`).
* `DEFAULT_BOX_ID` (str): Standard-Box-ID für das Datenaufnahme-Deployment (`"5faeb5589b2df8001b980304"`).
* `INITIAL_FETCH_DAYS` (int): Anzahl der Tage für den initialen Datenabruf (`365`).
* `CHUNK_DAYS` (int): Größe der Daten-Chunks in Tagen (`4`).
* `INTERVAL_SECONDS` (int): Intervall für die geplante Ausführung des Datenaufnahme-Flows (`180` Sekunden).

### Funktionen
* `create_or_get_work_pool(client, name: str)`: Eine asynchrone Funktion, die überprüft, ob ein Work Pool mit dem gegebenen Namen existiert. Falls nicht, wird ein neuer Work Pool vom Typ "process" erstellt.
* `main()`: Die Haupt-Asynchronous-Funktion, die den gesamten Setup- und Startprozess steuert.

### Ablauf der `main()`-Funktion
1.  **Prefect Client**: Stellt eine asynchrone Verbindung zum Prefect Server her.
2.  **Work Pool Setup**: Ruft `create_or_get_work_pool` auf, um sicherzustellen, dass der Work Pool `timeseries` vorhanden ist.
3.  **Deployment: `timeseries-data-ingestion`**:
    * Definiert Parameter und einen Zeitplan (alle `180` Sekunden) für das `data_ingestion_flow`.
    * Verwendet einen direkten HTTP POST-Request an die Prefect API, um das Deployment zu erstellen. Hierbei wird der `FLOW_ENTRYPOINT`, `APP_BASE_PATH`, Parameter, Zeitpläne, Tags (`ingestion`, `opensensemap`, `scheduled`) und eine Beschreibung übermittelt.
4.  **Deployment: `ml_training_temperature`**:
    * Definiert Tags (`ml_training`) und eine Beschreibung für das `train_all_models`-Flow.
    * Erstellt dieses Deployment ebenfalls über einen HTTP POST-Request an die Prefect API.
5.  **Deployment: `create_forecast`**:
    * Definiert Tags (`forecast`) und eine Beschreibung für das `generate_forecast_flow`.
    * Erstellt auch dieses Deployment über einen HTTP POST-Request an die Prefect API.
6.  **Worker-Start**: Initialisiert und startet einen `ProcessWorker`, der an den Work Pool `timeseries` gebunden ist. Dieser Worker ist dann bereit, Flow Runs auszuführen, die Prefect für diesen Work Pool plant.
7.  **Fehlerbehandlung**: Fängt `KeyboardInterrupt` ab, um einen sauberen Exit des Workers zu ermöglichen, und loggt andere unerwartete Fehler.

### Besonderheiten
* Verwendet `asyncio` für die asynchrone Interaktion mit der Prefect API.
* Nutzt `requests` für direkte HTTP-Aufrufe an die Prefect API, um Deployments zu erstellen.
* Das Skript ist idempotent für die Work Pool-Erstellung; es wird nur erstellt, wenn es nicht existiert.
* Die Pfade sind so konfiguriert, dass sie sowohl in der Entwicklungsumgebung als auch in Docker-Containern (`/app/ml_service/`) funktionieren.