"""Database models and schema for FieldClimate application."""

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

# SQL statements for creating database tables
CREATE_STATIONS_TABLE = """
CREATE TABLE IF NOT EXISTS stations (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    latitude REAL,
    longitude REAL,
    elevation REAL,
    metadata TEXT,  -- JSON string
    last_updated TEXT,  -- ISO timestamp
    enabled INTEGER NOT NULL DEFAULT 1
)
"""

CREATE_SENSORS_TABLE = """
CREATE TABLE IF NOT EXISTS sensors (
    id TEXT PRIMARY KEY,
    station_id TEXT NOT NULL,
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    unit TEXT,
    position TEXT,
    metadata TEXT,  -- JSON string
    FOREIGN KEY (station_id) REFERENCES stations(id)
)
"""

CREATE_MEASUREMENTS_TABLE = """
CREATE TABLE IF NOT EXISTS measurements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sensor_id TEXT NOT NULL,
    timestamp TEXT NOT NULL,  -- ISO timestamp
    value REAL NOT NULL,
    quality TEXT,
    raw_data TEXT,  -- JSON string, optional
    FOREIGN KEY (sensor_id) REFERENCES sensors(id)
)
"""

# Indexes for query performance
CREATE_INDEXES = [
    """CREATE INDEX IF NOT EXISTS idx_measurements_sensor_time 
       ON measurements(sensor_id, timestamp)""",
    """CREATE INDEX IF NOT EXISTS idx_measurements_time 
       ON measurements(timestamp)""",
    """CREATE INDEX IF NOT EXISTS idx_sensors_station 
       ON sensors(station_id)""",
]

# Unique constraint to prevent duplicate measurements
CREATE_UNIQUE_CONSTRAINT = """
CREATE UNIQUE INDEX IF NOT EXISTS idx_measurements_unique 
ON measurements(sensor_id, timestamp, value)
"""


def initialize_database(db_path: str) -> None:
    """Initialize the database schema.
    
    Args:
        db_path: Path to the SQLite database file.
    """
    # Ensure directory exists
    db_dir = Path(db_path).parent
    db_dir.mkdir(parents=True, exist_ok=True)
    
    # Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create tables
    cursor.execute(CREATE_STATIONS_TABLE)
    cursor.execute(CREATE_SENSORS_TABLE)
    cursor.execute(CREATE_MEASUREMENTS_TABLE)
    
    # Create indexes
    for index_sql in CREATE_INDEXES:
        cursor.execute(index_sql)
        
    # Create unique constraint
    cursor.execute(CREATE_UNIQUE_CONSTRAINT)
    
    # Commit changes and close connection
    conn.commit()
    conn.close()


def dict_factory(cursor: sqlite3.Cursor, row: sqlite3.Row) -> Dict[str, Any]:
    """Convert SQLite row to dictionary.
    
    Args:
        cursor: SQLite cursor.
        row: SQLite row.
        
    Returns:
        Dictionary with column names as keys.
    """
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}


def json_serializer(obj: Any) -> str:
    """Convert object to JSON string.
    
    Args:
        obj: Object to serialize.
        
    Returns:
        JSON string representation.
    """
    if isinstance(obj, (dict, list)):
        return json.dumps(obj)
    return str(obj)


def json_deserializer(text: Optional[str]) -> Any:
    """Convert JSON string to object.
    
    Args:
        text: JSON string to deserialize.
        
    Returns:
        Deserialized object.
    """
    if not text:
        return None
        
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text