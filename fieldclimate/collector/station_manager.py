"""Station management for FieldClimate data collection."""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple

from fieldclimate.collector.api_client import FieldClimateClient
from fieldclimate.database.db_manager import DatabaseManager
from fieldclimate.utils.error_handler import APIError, retry_with_backoff
from fieldclimate.utils.helpers import parse_datetime

# Set up module logger
logger = logging.getLogger(__name__)


class StationManager:
    """Manages weather station discovery and sensor configuration."""

    def __init__(
        self, 
        api_client: FieldClimateClient, 
        db_manager: DatabaseManager,
        backfill_days: int = 7
    ) -> None:
        """Initialize the station manager.
        
        Args:
            api_client: Initialized FieldClimate API client.
            db_manager: Database manager for storing station and sensor data.
            backfill_days: Days to backfill data when adding a new station/sensor.
        """
        self.api_client = api_client
        self.db_manager = db_manager
        self.backfill_days = backfill_days

    @retry_with_backoff(max_retries=3)
    def discover_stations(self) -> List[Dict[str, Any]]:
        """Discover all available stations from the API.
        
        Returns:
            List of discovered stations.
        """
        logger.info("Discovering available stations")
        try:
            stations = self.api_client.get_stations()
            logger.info(f"Discovered {len(stations)} stations")
            return stations
        except APIError as e:
            logger.error(f"Failed to discover stations: {e}")
            raise

    @retry_with_backoff(max_retries=3)
    def get_station_details(self, station_id: str) -> Dict[str, Any]:
        """Get detailed information about a specific station.
        
        Args:
            station_id: ID of the station.
            
        Returns:
            Station details.
        """
        logger.info(f"Getting details for station {station_id}")
        try:
            station_details = self.api_client.get_station(station_id)
            return station_details
        except APIError as e:
            logger.error(f"Failed to get details for station {station_id}: {e}")
            raise

    @retry_with_backoff(max_retries=3)
    def discover_sensors(self, station_id: str) -> List[Dict[str, Any]]:
        """Discover all sensors for a station.
        
        Args:
            station_id: ID of the station.
            
        Returns:
            List of discovered sensors.
        """
        logger.info(f"Discovering sensors for station {station_id}")
        try:
            sensors = self.api_client.get_station_sensors(station_id)
            logger.info(f"Discovered {len(sensors)} sensors for station {station_id}")
            return sensors
        except APIError as e:
            logger.error(f"Failed to discover sensors for station {station_id}: {e}")
            raise

    def process_new_station(self, station_config: Dict[str, Any]) -> None:
        """Process a new station, adding it to the database with its sensors.
        
        Args:
            station_config: Station configuration dict with at least 'id' and 'name'.
        """
        station_id = station_config["id"]
        logger.info(f"Processing new station: {station_id} ({station_config.get('name', 'Unnamed')})")
        
        # Get detailed station information
        try:
            station_details = self.get_station_details(station_id)
            
            # Create station record
            station_data = {
                "id": station_id,
                "name": station_config.get("name") or station_details.get("name", "Unnamed Station"),
                "latitude": station_details.get("position", {}).get("latitude"),
                "longitude": station_details.get("position", {}).get("longitude"),
                "elevation": station_details.get("position", {}).get("altitude"),
                "metadata": station_details,
                "last_updated": None,
                "enabled": station_config.get("enabled", True),
            }
            
            # Save to database
            self.db_manager.add_station(station_data)
            
            # Discover and process sensors
            self._discover_and_process_sensors(station_id)
            
            logger.info(f"Successfully added station {station_id}")
            
        except Exception as e:
            logger.error(f"Failed to process new station {station_id}: {e}")
            raise

    def _discover_and_process_sensors(self, station_id: str) -> None:
        """Discover and process sensors for a station.
        
        Args:
            station_id: ID of the station.
        """
        try:
            # Get sensors from API
            sensors = self.discover_sensors(station_id)
            
            # Process each sensor
            for sensor in sensors:
                self._process_sensor(station_id, sensor)
                
        except Exception as e:
            logger.error(f"Failed to discover and process sensors for station {station_id}: {e}")
            raise

    def _process_sensor(self, station_id: str, sensor_data: Dict[str, Any]) -> None:
        """Process a sensor, adding it to the database.
        
        Args:
            station_id: ID of the station.
            sensor_data: Sensor data from the API.
        """
        sensor_id = sensor_data.get("id")
        if not sensor_id:
            logger.warning(f"Sensor without ID found for station {station_id}, skipping")
            return
            
        logger.info(f"Processing sensor {sensor_id} for station {station_id}")
        
        try:
            # Extract sensor information
            sensor = {
                "id": sensor_id,
                "station_id": station_id,
                "name": sensor_data.get("name", f"Sensor {sensor_id}"),
                "type": sensor_data.get("type", "unknown"),
                "unit": sensor_data.get("unit", ""),
                "position": sensor_data.get("position", ""),
                "metadata": sensor_data,
            }
            
            # Save to database
            self.db_manager.add_sensor(sensor)
            
            # Backfill historical data for this sensor
            self._backfill_sensor_data(station_id, sensor_id)
            
            logger.info(f"Successfully added sensor {sensor_id} for station {station_id}")
            
        except Exception as e:
            logger.error(f"Failed to process sensor {sensor_id} for station {station_id}: {e}")
            # Don't re-raise, continue with other sensors

    def _backfill_sensor_data(self, station_id: str, sensor_id: str) -> None:
        """Backfill historical data for a sensor.
        
        Args:
            station_id: ID of the station.
            sensor_id: ID of the sensor.
        """
        if self.backfill_days <= 0:
            logger.info(f"Backfilling disabled, skipping for {station_id}/{sensor_id}")
            return
            
        logger.info(f"Backfilling {self.backfill_days} days of data for sensor {sensor_id}")
        
        try:
            # Calculate time range for backfilling
            end_date = datetime.now()
            start_date = end_date - timedelta(days=self.backfill_days)
            
            # Get data from API
            data = self.api_client.get_sensor_data(
                station_id=station_id,
                sensor_id=sensor_id,
                start_date=start_date,
                end_date=end_date,
                data_group="raw"
            )
            
            # Process and store data
            self._process_sensor_data(station_id, sensor_id, data)
            
            logger.info(f"Successfully backfilled data for sensor {sensor_id}")
            
        except Exception as e:
            logger.error(f"Failed to backfill data for sensor {sensor_id}: {e}")
            # Don't re-raise, this is not critical

    def _process_sensor_data(
        self, 
        station_id: str, 
        sensor_id: str, 
        data: Dict[str, Any]
    ) -> int:
        """Process and store sensor data.
        
        Args:
            station_id: ID of the station.
            sensor_id: ID of the sensor.
            data: Sensor data from the API.
            
        Returns:
            Number of measurements stored.
        """
        if not data or not isinstance(data, dict):
            logger.warning(f"No valid data received for sensor {sensor_id}")
            return 0
            
        # Extract data points
        data_points = data.get("data", [])
        if not data_points:
            logger.info(f"No data points in response for sensor {sensor_id}")
            return 0
            
        logger.info(f"Processing {len(data_points)} data points for sensor {sensor_id}")
        
        measurements = []
        for point in data_points:
            try:
                # Extract timestamp and value
                timestamp = point.get("date_utc") or point.get("date")
                if not timestamp:
                    continue
                    
                value = point.get("value")
                if value is None:
                    continue
                    
                # Convert timestamp to datetime
                dt = parse_datetime(timestamp)
                
                # Create measurement record
                measurement = {
                    "sensor_id": sensor_id,
                    "timestamp": dt.isoformat(),
                    "value": float(value),
                    "quality": point.get("quality", ""),
                    "raw_data": point,
                }
                
                measurements.append(measurement)
                
            except Exception as e:
                logger.warning(f"Failed to process data point for sensor {sensor_id}: {e}")
                continue
                
        # Store measurements in database
        if measurements:
            self.db_manager.add_measurements(measurements)
            
        # Update last_updated for station
        if measurements:
            self.db_manager.update_station_last_updated(
                station_id, measurements[-1]["timestamp"]
            )
            
        return len(measurements)

    def sync_station_data(
        self, 
        station_id: str, 
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, int]:
        """Synchronize data for a station within a time range.
        
        Args:
            station_id: ID of the station.
            start_date: Start date for data retrieval. If None, uses last_updated.
            end_date: End date for data retrieval. If None, uses current time.
            
        Returns:
            Dictionary with sensor IDs as keys and number of measurements added as values.
        """
        # Get station from database
        station = self.db_manager.get_station(station_id)
        if not station:
            logger.error(f"Station {station_id} not found in database")
            return {}
            
        # If station is disabled, skip
        if not station.get("enabled", True):
            logger.info(f"Station {station_id} is disabled, skipping sync")
            return {}
            
        logger.info(f"Syncing data for station {station_id}")
        
        # Determine time range
        if start_date is None:
            # Use last_updated from database or backfill days
            last_updated = station.get("last_updated")
            if last_updated:
                start_date = parse_datetime(last_updated)
                # Add a 1 hour overlap to catch any late data
                start_date = start_date - timedelta(hours=1)
            else:
                start_date = datetime.now() - timedelta(days=self.backfill_days)
                
        if end_date is None:
            end_date = datetime.now()
            
        # Get all sensors for this station
        sensors = self.db_manager.get_sensors_for_station(station_id)
        if not sensors:
            logger.warning(f"No sensors found for station {station_id}")
            return {}
            
        # Process each sensor
        results = {}
        for sensor in sensors:
            sensor_id = sensor["id"]
            try:
                # Get data from API
                data = self.api_client.get_sensor_data(
                    station_id=station_id,
                    sensor_id=sensor_id,
                    start_date=start_date,
                    end_date=end_date,
                    data_group="raw"
                )
                
                # Process and store data
                count = self._process_sensor_data(station_id, sensor_id, data)
                results[sensor_id] = count
                
                logger.info(f"Added {count} measurements for sensor {sensor_id}")
                
            except Exception as e:
                logger.error(f"Failed to sync data for sensor {sensor_id}: {e}")
                results[sensor_id] = 0
                
        return results