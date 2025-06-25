# =================================================================
# Datei: db_setup.py 
# Zweck: Logik zur Initialisierung der Datenbank.
# =================================================================
from sqlalchemy import inspect

from utils.db_utils import get_engine_instance
from custom_types.prediction import Base, TrainedModel

def initialize_database():
    print("Prüfe Datenbank-Schema...")
    
    engine = get_engine_instance()
    
    inspector = inspect(engine)
    table_name_to_check = TrainedModel.__tablename__

    if not inspector.has_table(table_name_to_check):
        print(f"Tabelle '{table_name_to_check}' nicht gefunden. Erstelle Tabellen...")
        Base.metadata.create_all(bind=engine)
        print("Datenbank-Tabellen erfolgreich erstellt.")
    else:
        print(f"Tabelle '{table_name_to_check}' existiert bereits. Überspringe Erstellung.")