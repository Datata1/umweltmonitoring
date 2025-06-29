import pandas as pd
from typing import List, Dict, Any


def _create_beautiful_markdown(training_results: List[Dict[str, Any]], forecast_window: int) -> str:
    """
    Erstellt einen schön formatierten Markdown-Bericht aus den Trainingsergebnissen.
    """
    if not training_results:
        return "## Trainingsmetriken der Modelle\n\nKeine Trainingsergebnisse vorhanden."

    metrics_df = pd.DataFrame(training_results).iloc[24:]
    
    # --- 1. Zusammenfassung erstellen ---
    successful_trainings = metrics_df['error'].isnull().sum()
    failed_trainings = metrics_df['error'].notnull().sum()
    
    summary_section = (
        f"**Zusammenfassung vom {pd.Timestamp.now(tz='Europe/Berlin').strftime('%d.%m.%Y, %H:%M:%S')}**\n\n"
        f"- ✅ **Erfolgreich trainiert:** {successful_trainings} von {forecast_window} Modellen\n"
        f"- ❌ **Fehlgeschlagen:** {failed_trainings} Modelle\n\n"
    )

    # --- 2. Tabelle für erfolgreiche Trainings ---
    success_df = metrics_df[metrics_df['error'].isnull()].copy()
    success_section = ""
    if not success_df.empty:
        # Spalten für die Anzeige auswählen und umbenennen
        display_columns = {
            "forecast_horizon_hours": "Horizont (h)",
            "val_rmse": "RMSE",
            "val_mae": "MAE",
            "val_mape": "MAPE (%)",
            "val_r2": "R²",
            "training_duration_seconds": "Dauer (s) ⏱️"
        }
        
        # MAPE in Prozent umrechnen
        if 'val_mape' in success_df.columns:
            success_df['val_mape'] = success_df['val_mape'] * 100

        success_df_display = success_df[list(display_columns.keys())].rename(columns=display_columns)

        # KORREKTUR: Formatierer für die Zahlenspalten definieren
        formatters = {
            "RMSE": "{:.3f}".format,
            "MAE": "{:.3f}".format,
            "MAPE (%)": "{:.2f}".format,
            "R²": "{:.3f}".format,
            "Dauer (s) ⏱️": "{:.2f}".format
        }

        # KORREKTUR: Wende die Formatierung auf den DataFrame an, BEVOR to_markdown aufgerufen wird.
        for col, formatter in formatters.items():
            if col in success_df_display.columns:
                success_df_display[col] = success_df_display[col].apply(formatter)
        
        success_section = (
            "### ✅ Erfolgreiche Trainings\n\n" +
            # KORREKTUR: Entferne die nicht unterstützten Parameter 'formatters' und 'floatfmt'.
            success_df_display.to_markdown(index=False)
        )

    # --- 3. Tabelle für fehlgeschlagene Trainings ---
    failures_df = metrics_df[metrics_df['error'].notnull()].copy()
    failures_section = ""
    if not failures_df.empty:
        failures_display = failures_df[["forecast_horizon_hours", "error"]].rename(columns={
            "forecast_horizon_hours": "Horizont (h)",
            "error": "Fehlermeldung"
        })
        failures_section = (
            "\n\n### ❌ Fehlgeschlagene Trainings\n\n" +
            failures_display.to_markdown(index=False)
        )

    # --- 4. Alles zusammensetzen ---
    final_markdown = (
        "## 💎 Trainingsmetriken der Modelle\n\n" +
        summary_section +
        success_section +
        failures_section
    )
    
    return final_markdown