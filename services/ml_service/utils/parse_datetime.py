from datetime import datetime, timezone

def parse_api_datetime(date_str: str | None) -> datetime | None:
    """Versucht, einen ISO-String (mit Z) sicher in ein TZ-aware datetime zu parsen."""
    if not date_str:
        return None
    try:
        if date_str.endswith('Z'):
            date_str = date_str[:-1] + '+00:00'
        dt = datetime.fromisoformat(date_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc) 
    except (ValueError, TypeError):
        return None