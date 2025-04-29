# app/utils/keybuilder.py
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# --- Helper for consistent datetime formatting ---
def _format_datetime(dt: datetime | None) -> str:
    if dt:
        return dt.isoformat()
    return "None"

# --- Key Builder for Aggregate Data (Korrigiert) ---
def aggregate_key_builder(func, *args, **kwargs) -> str:
    endpoint_kwargs = kwargs.get('kwargs', {}) 

    prefix = f"{func.__module__}:{func.__name__}"
    cache_key = (
        f"{prefix}:"
        f"sensor={endpoint_kwargs.get('sensor_id')}:"
        f"from={_format_datetime(endpoint_kwargs.get('from_date'))}:"
        f"to={_format_datetime(endpoint_kwargs.get('to_date'))}:"
        f"interval={endpoint_kwargs.get('interval')}:"
        f"agg_type={endpoint_kwargs.get('aggregation_type')}:"
        f"smooth={endpoint_kwargs.get('smoothing_window')}:"
        f"interp={endpoint_kwargs.get('interpolation_method')}"
    )
    logger.debug(f"Generated Cache Key: {cache_key}")
    return cache_key


def list_sensors_key_builder(func, *args, **kwargs) -> str:
    endpoint_kwargs = kwargs.get('kwargs', {}) 
    prefix = f"{func.__module__}:{func.__name__}"
    cache_key = (
        f"{prefix}:"
        f"skip={endpoint_kwargs.get('skip', 0)}:"
        f"limit={endpoint_kwargs.get('limit', 100)}:"
        f"filter={endpoint_kwargs.get('name_filter', '')}"
    )
    logger.debug(f"Generated Cache Key: {cache_key}")
    return cache_key

def box_detail_key_builder(func, *args, **kwargs) -> str:
    endpoint_kwargs = kwargs.get('kwargs', {}) 
    prefix = f"{func.__module__}:{func.__name__}"
    cache_key = f"{prefix}:box_id={endpoint_kwargs.get('box_id')}"
    logger.debug(f"Generated Cache Key: {cache_key}")
    return cache_key

def sensors_for_box_key_builder(func, *args, **kwargs) -> str:
    endpoint_kwargs = kwargs.get('kwargs', {}) 
    prefix = f"{func.__module__}:{func.__name__}"
    cache_key = (
        f"{prefix}:"
        f"box_id={endpoint_kwargs.get('box_id')}:"
        f"skip={endpoint_kwargs.get('skip', 0)}:"
        f"limit={endpoint_kwargs.get('limit', 100)}"
    )
    logger.debug(f"Generated Cache Key: {cache_key}")
    return cache_key

def summary_stats_key_builder(func, *args, **kwargs) -> str:
    endpoint_kwargs = kwargs.get('kwargs', {}) 
    prefix = f"{func.__module__}:{func.__name__}"
    cache_key = (
        f"{prefix}:"
        f"sensor={endpoint_kwargs.get('sensor_id')}:"
        f"from={_format_datetime(endpoint_kwargs.get('from_date'))}:"
        f"to={_format_datetime(endpoint_kwargs.get('to_date'))}"
    )
    logger.debug(f"Generated Cache Key: {cache_key}")
    return cache_key

def latest_data_key_builder(func, *args, **kwargs) -> str:
    endpoint_kwargs = kwargs.get('kwargs', {}) 
    prefix = f"{func.__module__}:{func.__name__}"
    cache_key = f"{prefix}:sensor_id={endpoint_kwargs.get('sensor_id')}"
    logger.debug(f"Generated Cache Key: {cache_key}")
    return cache_key

def raw_data_key_builder(func, *args, **kwargs) -> str:
    endpoint_kwargs = kwargs.get('kwargs', {}) 
    prefix = f"{func.__module__}:{func.__name__}"
    cache_key = (
        f"{prefix}:"
        f"sensor={endpoint_kwargs.get('sensor_id')}:"
        f"from={_format_datetime(endpoint_kwargs.get('from_date'))}:"
        f"to={_format_datetime(endpoint_kwargs.get('to_date'))}:"
        f"skip={endpoint_kwargs.get('skip', 0)}:"
        f"limit={endpoint_kwargs.get('limit', 1000)}" 
    )
    logger.debug(f"Generated Cache Key: {cache_key}")
    return cache_key