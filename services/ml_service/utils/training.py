from custom_types.prediction import TrainedModel
from sqlalchemy.orm import Session


def _update_or_create_model_in_db(db: Session, result: dict, logger):
    """
    Sucht nach einem bestehenden Modelleintrag für einen Horizont und aktualisiert ihn,
    oder erstellt einen neuen, falls keiner existiert (Upsert-Logik).
    """
    horizon = result.get('forecast_horizon_hours')
    if not horizon:
        logger.error(f"Ergebnis-Dictionary hat keinen 'horizon_hours'-Schlüssel: {result}")
        return

    # Suche nach einem existierenden Modell für diesen Horizont
    db_model = db.query(TrainedModel).filter(TrainedModel.forecast_horizon_hours == horizon).first()

    if db_model:
        # --- UPDATE-Pfad ---
        logger.info(f"Aktualisiere bestehenden DB-Eintrag für Horizont {horizon}h.")
        db_model.model_path = result.get('model_path')
        db_model.version_id = int(result.get('version_id', 1))
        db_model.training_duration_seconds = result.get('training_duration_seconds')
        db_model.val_mae = result.get('val_mae')
        db_model.val_rmse = result.get('val_rmse')
        db_model.val_mape = result.get('val_mape')
        db_model.val_r2 = result.get('val_r2')
        # last_trained_at wird durch onupdate in der DB automatisch aktualisiert
    else:
        # --- INSERT-Pfad ---
        logger.info(f"Erstelle neuen DB-Eintrag für Horizont {horizon}h.")
        new_model = TrainedModel(
            model_name=f"temperatur-vorhersage-{horizon}h", 
            forecast_horizon_hours=horizon,
            model_path=result.get('model_path'),
            version_id=int(result.get('version_id', 1)),
            training_duration_seconds=result.get('training_duration_seconds'),
            val_mae=result.get('val_mae'),
            val_rmse=result.get('val_rmse'),
            val_mape=result.get('val_mape'),
            val_r2=result.get('val_r2')
        )
        db.add(new_model)