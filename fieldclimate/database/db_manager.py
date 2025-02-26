"""Database manager for FieldClimate application."""

import json
import logging
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Tuple, Union

from fieldclimate.database.models import (
    dict_factory,
    initialize_database,
    json_deserializer,
    json_serializer,
)
from fieldclimate.utils.error_handler import DatabaseError

# Set up module logger
logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages database operations for FieldClimate application."""

    def __init__(self, db_path: str) -> None:
        """Initialize the database manager.
        
        Args:
            db_path: Path to the SQLite database file.
        """
        self.db_path = db_path
        
        # Ensure database exists and has the correct schema
        try:
            initialize_database(db_path)
            logger.info(f"Database initialized at {db_path}")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise DatabaseError(f"Database initialization failed: {e}")

    @contextmanager
    def _get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Get a database connection with proper configuration.
        
        Yields:
            Configured SQLite connection.
            
        Raises:
            DatabaseError: If connection fails.
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = dict_factory
            
            # Enable foreign keys
            conn.execute("PRAGMA foreign_keys = ON")
            
            yield conn
            
            conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Database error: {e}")
            if conn:
                conn.rollback()
            raise DatabaseError(f"Database operation failed: {e}")
        finally:
            if conn:
                conn.close()

    def add_station(self, station: Dict[str, Any]) -> None:
        """Add a new weather station to the database.
        
        Args:
            station: Station data dictionary with the following keys:
                - id: Station ID (required)
                - name: Station name (required)
                - latitude: Latitude coordinate
                - longitude: Longitude coordinate
                - elevation: Elevation in meters
                - metadata: Additional station metadata
                - last_updated: Last data update timestamp
                - enabled: Whether the station is enabled
                
        Raises:
            DatabaseError: If database operation fails.
        """
        # Serialize JSON fields
        if "metadata" in station and station["metadata"]:
            station["metadata"] = json_serializer(station["metadata"])
        
        with self._get_connection() as conn:
            try:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO stations
                    (id, name, latitude, longitude, elevation, metadata, last_updated, enabled)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        station["id"],
                        station["name"],
                        station.get("latitude"),
                        station.get("longitude"),
                        station.get("elevation"),
                        station.get("metadata"),
                        station.get("last_updated"),
                        1 if station.get("enabled", True) else 0,
                    ),
                )
                logger.info(f"Added station {station['id']} to database")
            except sqlite3.Error as e:
                logger.error(f"Failed to add station {station['id']}: {e}")
                raise DatabaseError(f"Failed to add station: {e}")

    def get_station(self, station_id: str) -> Optional[Dict[str, Any]]:
        """Get a station by ID.
        
        Args:
            station_id: Station ID.
            
        Returns:
            Station data dictionary, or None if not found.
            
        Raises:
            DatabaseError: If database operation fails.
        """
        with self._get_connection() as conn:
            try:
                result = conn.execute(
                    "SELECT * FROM stations WHERE id = ?", (station_id,)
                ).fetchone()
                
                if result and result.get("metadata"):
                    result["metadata"] = json_deserializer(result["metadata"])
                
                return result
            except sqlite3.Error as e:
                logger.error(f"Failed to get station {station_id}: {e}")
                raise DatabaseError(f"Failed to get station: {e}")

    def get_all_stations(self, enabled_only: bool = False) -> List[Dict[str, Any]]:
        """Get all stations from the database.
        
        Args:
            enabled_only: If True, return only enabled stations.
            
        Returns:
            List of station data dictionaries.
            
        Raises:
            DatabaseError: If database operation fails.
        """
        with self._get_connection() as conn:
            try:
                query = "SELECT * FROM stations"
                if enabled_only:
                    query += " WHERE enabled = 1"
                
                results = conn.execute(query).fetchall()
                
                # Deserialize JSON fields
                for result in results:
                    if result.get("metadata"):
                        result["metadata"] = json_deserializer(result["metadata"])
                
                return results
            except sqlite3.Error as e:
                logger.error(f"Failed to get stations: {e}")
                raise DatabaseError(f"Failed to get stations: {e}")

    def update_station_last_updated(
        self, station_id: str, timestamp: Union[str, datetime]
    ) -> None:
        """Update the last_updated timestamp for a station.
        
        Args:
            station_id: Station ID.
            timestamp: New timestamp (datetime or ISO format string).
            
        Raises:
            DatabaseError: If database operation fails.
        """
        # Convert datetime to string if needed
        if isinstance(timestamp, datetime):
            timestamp = timestamp.isoformat()
        
        with self._get_connection() as conn:
            try:
                conn.execute(
                    "UPDATE stations SET last_updated = ? WHERE id = ?",
                    (timestamp, station_id),
                )
                logger.debug(f"Updated last_updated for station {station_id} to {timestamp}")
            except sqlite3.Error as e:
                logger.error(f"Failed to update station {station_id} last_updated: {e}")
                raise DatabaseError(f"Failed to update station last_updated: {e}")

    def add_sensor(self, sensor: Dict[str, Any]) -> None:
        """Add a new sensor to the database.
        
        Args:
            sensor: Sensor data dictionary with the following keys:
                - id: Sensor ID (required)
                - station_id: Station ID (required)
                - name: Sensor name (required)
                - type: Sensor type (required)
                - unit: Measurement unit
                - position: Sensor position description
                - metadata: Additional sensor metadata
                
        Raises:
            DatabaseError: If database operation fails.
        """
        # Serialize JSON fields
        if "metadata" in sensor and sensor["metadata"]:
            sensor["metadata"] = json_serializer(sensor["metadata"])
        
        with self._get_connection() as conn:
            try:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO sensors
                    (id, station_id, name, type, unit, position, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        sensor["id"],
                        sensor["station_id"],
                        sensor["name"],
                        sensor["type"],
                        sensor.get("unit"),
                        sensor.get("position"),
                        sensor.get("metadata"),
                    ),
                )
                logger.info(f"Added sensor {sensor['id']} to database")
            except sqlite3.Error as e:
                logger.error(f"Failed to add sensor {sensor['id']}: {e}")
                raise DatabaseError(f"Failed to add sensor: {e}")

    def get_sensor(self, sensor_id: str) -> Optional[Dict[str, Any]]:
        """Get a sensor by ID.
        
        Args:
            sensor_id: Sensor ID.
            
        Returns:
            Sensor data dictionary, or None if not found.
            
        Raises:
            DatabaseError: If database operation fails.
        """
        with self._get_connection() as conn:
            try:
                result = conn.execute(
                    "SELECT * FROM sensors WHERE id = ?", (sensor_id,)
                ).fetchone()
                
                if result and result.get("metadata"):
                    result["metadata"] = json_deserializer(result["metadata"])
                
                return result
            except sqlite3.Error as e:
                logger.error(f"Failed to get sensor {sensor_id}: {e}")
                raise DatabaseError(f"Failed to get sensor: {e}")

    def get_sensors_for_station(self, station_id: str) -> List[Dict[str, Any]]:
        """Get all sensors for a station.
        
        Args:
            station_id: Station ID.
            
        Returns:
            List of sensor data dictionaries.
            
        Raises:
            DatabaseError: If database operation fails.
        """
        with self._get_connection() as conn:
            try:
                results = conn.execute(
                    "SELECT * FROM sensors WHERE station_id = ?", (station_id,)
                ).fetchall()
                
                # Deserialize JSON fields
                for result in results:
                    if result.get("metadata"):
                        result["metadata"] = json_deserializer(result["metadata"])
                
                return results
            except sqlite3.Error as e:
                logger.error(f"Failed to get sensors for station {station_id}: {e}")
                raise DatabaseError(f"Failed to get sensors for station: {e}")

    def add_measurements(self, measurements: List[Dict[str, Any]]) -> int:
        """Add multiple measurements to the database.
        
        Args:
            measurements: List of measurement data dictionaries with the following keys:
                - sensor_id: Sensor ID (required)
                - timestamp: Measurement timestamp (required)
                - value: Measurement value (required)
                - quality: Data quality indicator
                - raw_data: Raw data from API
                
        Returns:
            Number of measurements added.
            
        Raises:
            DatabaseError: If database operation fails.
        """
        if not measurements:
            return 0
        
        # Prepare data for batch insert
        values = []
        for m in measurements:
            # Serialize JSON fields
            raw_data = None
            if "raw_data" in m and m["raw_data"]:
                raw_data = json_serializer(m["raw_data"])
            
            values.append(
                (
                    m["sensor_id"],
                    m["timestamp"],
                    m["value"],
                    m.get("quality"),
                    raw_data,
                )
            )
        
        with self._get_connection() as conn:
            try:
                # Use executemany for batch insert
                cursor = conn.executemany(
                    """
                    INSERT OR IGNORE INTO measurements
                    (sensor_id, timestamp, value, quality, raw_data)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    values,
                )
                
                count = cursor.rowcount
                logger.debug(f"Added {count} measurements to database")
                return count
            except sqlite3.Error as e:
                logger.error(f"Failed to add measurements: {e}")
                raise DatabaseError(f"Failed to add measurements: {e}")

    def get_measurements(
        self,
        sensor_id: str,
        start_date: Optional[Union[str, datetime]] = None,
        end_date: Optional[Union[str, datetime]] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Get measurements for a sensor within a time range.
        
        Args:
            sensor_id: Sensor ID.
            start_date: Start date (inclusive).
            end_date: End date (inclusive).
            limit: Maximum number of records to return.
            
        Returns:
            List of measurement data dictionaries.
            
        Raises:
            DatabaseError: If database operation fails.
        """
        # Convert datetime to string if needed
        if isinstance(start_date, datetime):
            start_date = start_date.isoformat()
        if isinstance(end_date, datetime):
            end_date = end_date.isoformat()
        
        with self._get_connection() as conn:
            try:
                query = "SELECT * FROM measurements WHERE sensor_id = ?"
                params = [sensor_id]
                
                if start_date:
                    query += " AND timestamp >= ?"
                    params.append(start_date)
                
                if end_date:
                    query += " AND timestamp <= ?"
                    params.append(end_date)
                
                query += " ORDER BY timestamp"
                
                if limit:
                    query += " LIMIT ?"
                    params.append(limit)
                
                results = conn.execute(query, params).fetchall()
                
                # Deserialize JSON fields
                for result in results:
                    if result.get("raw_data"):
                        result["raw_data"] = json_deserializer(result["raw_data"])
                
                return results
            except sqlite3.Error as e:
                logger.error(
                    f"Failed to get measurements for sensor {sensor_id}: {e}"
                )
                raise DatabaseError(f"Failed to get measurements: {e}")

    def get_latest_measurement(self, sensor_id: str) -> Optional[Dict[str, Any]]:
        """Get the latest measurement for a sensor.
        
        Args:
            sensor_id: Sensor ID.
            
        Returns:
            Latest measurement data dictionary, or None if not found.
            
        Raises:
            DatabaseError: If database operation fails.
        """
        with self._get_connection() as conn:
            try:
                result = conn.execute(
                    """
                    SELECT * FROM measurements 
                    WHERE sensor_id = ? 
                    ORDER BY timestamp DESC 
                    LIMIT 1
                    """,
                    (sensor_id,),
                ).fetchone()
                
                if result and result.get("raw_data"):
                    result["raw_data"] = json_deserializer(result["raw_data"])
                
                return result
            except sqlite3.Error as e:
                logger.error(f"Failed to get latest measurement for sensor {sensor_id}: {e}")
                raise DatabaseError(f"Failed to get latest measurement: {e}")

    def optimize_database(self) -> None:
        """Optimize the database by running VACUUM.
        
        Raises:
            DatabaseError: If database operation fails.
        """
        with self._get_connection() as conn:
            try:
                conn.execute("VACUUM")
                logger.info("Database optimized")
            except sqlite3.Error as e:
                logger.error(f"Failed to optimize database: {e}")
                raise DatabaseError(f"Failed to optimize database: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics.
        
        Returns:
            Dictionary with database statistics.
            
        Raises:
            DatabaseError: If database operation fails.
        """
        stats = {}
        
        with self._get_connection() as conn:
            try:
                # Count stations
                stats["station_count"] = conn.execute(
                    "SELECT COUNT(*) as count FROM stations"
                ).fetchone()["count"]
                
                # Count enabled stations
                stats["enabled_station_count"] = conn.execute(
                    "SELECT COUNT(*) as count FROM stations WHERE enabled = 1"
                ).fetchone()["count"]
                
                # Count sensors
                stats["sensor_count"] = conn.execute(
                    "SELECT COUNT(*) as count FROM sensors"
                ).fetchone()["count"]
                
                # Count measurements
                stats["measurement_count"] = conn.execute(
                    "SELECT COUNT(*) as count FROM measurements"
                ).fetchone()["count"]
                
                # Database size
                db_path = Path(self.db_path)
                if db_path.exists():
                    stats["database_size_bytes"] = db_path.stat().st_size
                
                return stats
            except sqlite3.Error as e:
                logger.error(f"Failed to get database statistics: {e}")
                raise DatabaseError(f"Failed to get database statistics: {e}")