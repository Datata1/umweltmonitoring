import datetime
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    DateTime,
    Float,
    JSON,
    func
)
from sqlalchemy.orm import declarative_base, Mapped

Base = declarative_base()

class TrainedModel(Base):
    """
    SQLAlchemy-Modell zur Speicherung von Metadaten und Metriken
    trainierter Zeitreihen-Vorhersagemodelle mit automatischer Versionierung.
    """
    __tablename__ = 'trained_models'

    # --- Identifikation & Metadaten ---
    id: Mapped[int] = Column(Integer, primary_key=True)
    model_name: Mapped[str] = Column(String(255), nullable=False, index=True)
    forecast_horizon_hours: Mapped[int] = Column(Integer, nullable=False, index=True)
    model_path: Mapped[str] = Column(String(512), nullable=False, unique=True)
    
    # Sie muss ein Integer sein und darf nicht null sein.
    version_id: Mapped[int] = Column(Integer, nullable=False)
    
    last_trained_at: Mapped[datetime.datetime] = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # --- Trainings-Metriken ---
    training_duration_seconds: Mapped[float] = Column(Float, nullable=True)

    # --- Leistungsmetriken (aus der Validierung) ---
    val_mae: Mapped[float] = Column(Float, nullable=True)
    val_rmse: Mapped[float] = Column(Float, nullable=True)
    val_mape: Mapped[float] = Column(Float, nullable=True)
    val_r2: Mapped[float] = Column(Float, nullable=True)

    # Wir teilen SQLAlchemy mit, welche Spalte der Versionszähler ist.
    __mapper_args__ = {
        'version_id_col': version_id
    }

    def __repr__(self):
        return (
            f"<TrainedModel(id={self.id}, name='{self.model_name}', "
            f"horizon={self.forecast_horizon_hours}h, version={self.version_id})>"
        )

