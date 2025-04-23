# services/backend/Dockerfile

# 1. Wähle ein offizielles Python Base Image
# Ersetze 3.12 durch deine tatsächliche Python-Version, falls abweichend.
# Slim-Versionen sind kleiner.
FROM python:3.12.9-slim

# 2. Setze Umgebungsvariablen für Python
ENV PYTHONUNBUFFERED=1 \
    # Verhindert, dass Python .pyc Dateien schreibt (optional, aber sauberer in Containern)
    PYTHONDONTWRITEBYTECODE=1

# 3. Setze das Arbeitsverzeichnis im Container
WORKDIR /app

# 4. Installiere 'uv' (optional, aber du nutzt es im command)
RUN pipx install uv

# 5. Kopiere zuerst NUR die Dateien, die die Abhängigkeiten definieren
COPY pyproject.toml poetry.lock* ./
# ODER, falls du eine requirements.txt hast:
# COPY requirements.txt ./

# 6. Installiere die Python-Abhängigkeiten mit uv (oder pip)
RUN uv pip install --system  .


# 7. Kopiere den Rest deines Anwendungscodes ins Arbeitsverzeichnis
# Das './app' im COPY-Befehl bezieht sich auf das 'app'-Verzeichnis *innerhalb* deines Backend-Service-Ordners
# Das zweite '/app' ist das Ziel im Container (unser WORKDIR)
COPY ./app /app/app

# 8. Deklariere den Port, auf dem die Anwendung lauscht
EXPOSE 8000
