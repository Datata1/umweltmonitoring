{ pkgs, postgresqlPackage }:
(
  pkgs.writeShellApplication {
    name = "start-postgres-app";
    runtimeInputs = with pkgs; [
      postgresqlPackage 
      glibcLocales
      coreutils
      bash
    ];
    text = ''
      #!${pkgs.bash}/bin/bash
      set -e # Exit on first error

      echo "--- Setting up PostgreSQL Environment (Foreground Mode) ---"

      PGDATA=$(pwd)/pgdata
      export PGDATA
      export PGPORT=''${PGPORT:-5432}
      PGSOCKETDIR=$(pwd)/pgsocket
      export PGSOCKETDIR
      export PGPASSWORD=''${PGPASSWORD:-"devpassword"}
      export LANG="C.UTF-8"
      export LC_ALL="C.UTF-8"

      POSTGRES_BIN="${postgresqlPackage}/bin"
      DB_USER=$(whoami)
      DB_NAME_FOR_INFO=''${DB_NAME:-"$DB_USER"}

      mkdir -p "$PGDATA" "$PGSOCKETDIR"

      if [ ! -f "$PGDATA/PG_VERSION" ]; then
        echo "Initializing database cluster in '$PGDATA' for user '$DB_USER'..."
        pwfile=$(mktemp)
        echo "$PGPASSWORD" > "$pwfile"
        "$POSTGRES_BIN/initdb" --locale=C.UTF-8 -E UTF8 -D "$PGDATA" -U "$DB_USER" --auth-host=scram-sha-256 --auth-local=scram-sha-256 --pwfile="$pwfile"
        rm "$pwfile"
        echo "Database cluster initialized."
        echo "host all all 0.0.0.0/0 scram-sha-256" >> "$PGDATA/pg_hba.conf"
        echo "listen_addresses = '*'" >> "$PGDATA/postgresql.conf"
        echo "shared_preload_libraries = 'vector,timescaledb'" >> "$PGDATA/postgresql.conf"
      else
        echo "Database cluster already initialized in '$PGDATA'."
      fi

      echo "--------------------------------------------------------------------"
      echo "Starting PostgreSQL server in the foreground."
      echo "User:       $DB_USER"
      echo "Password:   (set via PGPASSWORD env var)"
      echo "Port:       $PGPORT"
      echo "Data dir:   $PGDATA"
      echo "Socket dir: $PGSOCKETDIR"
      echo "Logs will be printed to this terminal (stdout/stderr)."
      echo "--------------------------------------------------------------------"
      echo "Connect to default 'postgres' DB using:"
      echo "  psql -h localhost -p $PGPORT -U $DB_USER postgres"
      echo "If needed, create your database and extension manually:"
      echo "  CREATE DATABASE \"$DB_NAME_FOR_INFO\";"
      echo "  \\c \"$DB_NAME_FOR_INFO\""
      echo "  CREATE EXTENSION IF NOT EXISTS vector timescaledb CASCADE;"
      echo "--------------------------------------------------------------------"
      echo "Press Ctrl+C here to stop the server gracefully."
      echo "--------------------------------------------------------------------"

      exec "$POSTGRES_BIN/postgres" -D "$PGDATA" -p "$PGPORT" -k "$PGSOCKETDIR"
      echo "PostgreSQL server exited."
      exit 0
    '';
  }
)