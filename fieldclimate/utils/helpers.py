"""Helper functions for the FieldClimate application."""

import hashlib
import hmac
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Union

import dateutil.parser


def generate_signature(
    method: str, 
    path: str, 
    timestamp: int, 
    private_key: str, 
    content: str = ""
) -> str:
    """Generate HMAC signature for FieldClimate API.
    
    Args:
        method: HTTP method (GET, POST, etc.).
        path: API endpoint path.
        timestamp: Current UTC timestamp in seconds.
        private_key: Private key for signature generation.
        content: Request body for POST/PUT requests.
        
    Returns:
        HMAC signature as a hexadecimal string.
    """
    # Construct the message string
    message = f"{method}{path}{timestamp}{content}"
    
    # Create signature using HMAC-SHA256
    signature = hmac.new(
        private_key.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()
    
    return signature


def utc_timestamp() -> int:
    """Get current UTC timestamp in seconds.
    
    Returns:
        Current UTC timestamp as an integer.
    """
    return int(time.time())


def parse_datetime(dt_str: str) -> datetime:
    """Parse datetime string to datetime object.
    
    Args:
        dt_str: Datetime string in ISO 8601 format.
        
    Returns:
        Datetime object with timezone information.
    """
    dt = dateutil.parser.parse(dt_str)
    
    # Ensure timezone is set
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
        
    return dt


def format_datetime(dt: datetime) -> str:
    """Format datetime object to ISO 8601 string.
    
    Args:
        dt: Datetime object to format.
        
    Returns:
        ISO 8601 formatted string.
    """
    # Ensure timezone is set
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
        
    return dt.isoformat()


def is_valid_measurement(
    value: float, 
    sensor_type: str,
    min_value: Optional[float] = None,
    max_value: Optional[float] = None
) -> bool:
    """Check if a measurement value is valid for a given sensor type.
    
    Args:
        value: The measurement value.
        sensor_type: Type of sensor (temperature, humidity, etc.).
        min_value: Optional minimum valid value.
        max_value: Optional maximum valid value.
        
    Returns:
        True if value is valid, False otherwise.
    """
    # Default min/max values for common sensor types
    sensor_ranges = {
        "temperature": (-50.0, 60.0),  # Celsius
        "humidity": (0.0, 100.0),      # Percentage
        "rain": (0.0, 300.0),          # mm
        "pressure": (800.0, 1200.0),   # hPa
        "wind_speed": (0.0, 80.0),     # m/s
        "wind_direction": (0.0, 360.0), # degrees
        "solar_radiation": (0.0, 2000.0), # W/m²
    }
    
    # Get range for sensor type or use provided values
    if min_value is None or max_value is None:
        sensor_min, sensor_max = sensor_ranges.get(sensor_type.lower(), (-1000.0, 1000.0))
        min_value = min_value if min_value is not None else sensor_min
        max_value = max_value if max_value is not None else sensor_max
    
    # Check if value is within range
    return min_value <= value <= max_value