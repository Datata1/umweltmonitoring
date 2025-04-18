# TODO: if we need to use alembic for migrations, we need to set up a naming convention for constraints

from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import MetaData

# Optional: Definiere ein Namensschema für Constraints, um Konflikte mit Alembic zu vermeiden
# Siehe SQLAlchemy und Alembic Dokumentation für Details, falls benötigt
# convention = {
#     "ix": "ix_%(column_0_label)s",
#     "uq": "uq_%(table_name)s_%(column_0_name)s",
#     "ck": "ck_%(table_name)s_%(constraint_name)s",
#     "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
#     "pk": "pk_%(table_name)s"
# }

# metadata_obj = MetaData(naming_convention=convention)

class Base(DeclarativeBase):
    # metadata = metadata_obj # Wenn naming convention verwendet wird
    pass