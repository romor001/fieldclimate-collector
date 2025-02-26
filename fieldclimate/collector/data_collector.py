"""Data collector for FieldClimate weather stations."""

import logging
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Union

from fieldclimate.collector.api_client import FieldClimateClient
from fieldclimate.collector.station_manager import StationManager
from fieldclimate.config.config_manager import ConfigManager
from fieldclimate.database.db_manager import DatabaseManager
from fieldclimate.utils.error_handler import APIError, DatabaseError

# Set up module logger
logger = logging.getLogger(__name__)


class DataCollector:
    """Main class for collecting weather data from FieldClimate API."""

    def __init__(self, config_manager: ConfigManager) -> None:
        """Initialize the data collector.
        
        Args:
            config_manager: Configuration manager instance.
        """
        self.config = config_manager
        
        # Initialize API client
        api_keys = self.config.get_api_keys()
        self.api_client = FieldClimateClient(
            public_key=api_keys["public_key"],
            private_key=api_keys["private_key"],
            base_url=self.config.get("api", "base_url", "https://api.fieldclimate.com/v1"),
            timeout=self.config.get("api", "request_timeout_seconds", 30),
            max_retries=self.config.get("api", "max_retries", 3),
        )
        
        # Initialize database manager
        db_path = self.config.get("database", "path", "data/fieldclimate.db")
        self.db_manager = DatabaseManager(db_path)
        
        # Initialize station manager
        backfill_days = self.config.get("collection", "backfill_days", 7)
        self.station_manager = StationManager(
            api_client=self.api_client,
            db_manager=self.db_manager,
            backfill_days=backfill_days,
        )

    def run(self) -> Dict[str, Any]:
        """Run the data collection process.
        
        Returns:
            Dictionary with collection statistics.
        """
        start_time = time.time()
        logger.info("Starting data collection")
        
        stats = {
            "start_time": datetime.now().isoformat(),
            "stations_processed": 0,
            "stations_successful": 0,
            "stations_failed": 0,
            "sensors_processed": 0,
            "measurements_added": 0,
            "errors": [],
        }
        
        try:
            # Initialize stations from configuration
            self._initialize_stations()
            
            # Get all enabled stations from database
            stations = self.db_manager.get_all_stations(enabled_only=True)
            logger.info(f"Found {len(stations)} enabled stations")
            
            # Process each station
            for station in stations:
                station_id = station["id"]
                station_name = station["name"]
                
                try:
                    logger.info(f"Processing station {station_name} ({station_id})")
                    stats["stations_processed"] += 1
                    
                    # Sync data for this station
                    result = self.station_manager.sync_station_data(station_id)
                    
                    # Update statistics
                    stats["sensors_processed"] += len(result)
                    measurements_added = sum(result.values())
                    stats["measurements_added"] += measurements_added
                    
                    logger.info(
                        f"Added {measurements_added} measurements from "
                        f"{len(result)} sensors for station {station_name}"
                    )
                    
                    stats["stations_successful"] += 1
                    
                except Exception as e:
                    logger.error(f"Failed to process station {station_name}: {e}")
                    stats["stations_failed"] += 1
                    stats["errors"].append(f"Station {station_name}: {str(e)}")
            
            # Run database optimization if needed
            # This is optional and can be skipped for frequent collections
            if self.config.get("database", "optimize_after_collection", False):
                try:
                    self.db_manager.optimize_database()
                except DatabaseError as e:
                    logger.warning(f"Database optimization failed: {e}")
                    stats["errors"].append(f"Database optimization: {str(e)}")
            
        except Exception as e:
            logger.error(f"Data collection failed: {e}")
            stats["errors"].append(f"General: {str(e)}")
        
        # Calculate duration
        duration = time.time() - start_time
        stats["duration_seconds"] = duration
        stats["end_time"] = datetime.now().isoformat()
        
        logger.info(
            f"Data collection completed in {duration:.2f} seconds. "
            f"Added {stats['measurements_added']} measurements from "
            f"{stats['stations_successful']}/{stats['stations_processed']} stations."
        )
        
        return stats

    def _initialize_stations(self) -> None:
        """Initialize stations from configuration.
        
        This checks if configured stations exist in the database
        and adds them if they don't.
        """
        logger.info("Initializing stations from configuration")
        
        # Get configured stations
        configured_stations = self.config.get_stations()
        if not configured_stations:
            logger.warning("No stations configured")
            return
        
        # Get existing stations from database
        existing_stations = self.db_manager.get_all_stations()
        existing_ids = {s["id"] for s in existing_stations}
        
        # Process new stations
        for station_config in configured_stations:
            station_id = station_config.get("id")
            if not station_id:
                logger.warning("Station without ID found in configuration, skipping")
                continue
                
            if station_id not in existing_ids:
                logger.info(f"New station found in configuration: {station_id}")
                try:
                    self.station_manager.process_new_station(station_config)
                except Exception as e:
                    logger.error(f"Failed to process new station {station_id}: {e}")
            else:
                # Update existing station if enabled status changed
                enabled = station_config.get("enabled", True)
                existing = next((s for s in existing_stations if s["id"] == station_id), None)
                if existing and existing.get("enabled", 1) != (1 if enabled else 0):
                    logger.info(f"Updating enabled status for station {station_id}")
                    existing["enabled"] = enabled
                    try:
                        self.db_manager.add_station(existing)
                    except Exception as e:
                        logger.error(f"Failed to update station {station_id}: {e}")

    def collect_station_data(
        self, 
        station_id: str, 
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, int]:
        """Collect data for a specific station within a time range.
        
        Args:
            station_id: ID of the station.
            start_date: Start date for data retrieval.
            end_date: End date for data retrieval.
            
        Returns:
            Dictionary with sensor IDs as keys and number of measurements added as values.
        """
        logger.info(
            f"Collecting data for station {station_id} "
            f"from {start_date or 'last update'} to {end_date or 'now'}"
        )
        
        try:
            result = self.station_manager.sync_station_data(
                station_id=station_id,
                start_date=start_date,
                end_date=end_date
            )
            
            total_measurements = sum(result.values())
            logger.info(
                f"Added {total_measurements} measurements from "
                f"{len(result)} sensors for station {station_id}"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to collect data for station {station_id}: {e}")
            raise

    def get_database_stats(self) -> Dict[str, Any]:
        """Get statistics about the database.
        
        Returns:
            Dictionary with database statistics.
        """
        try:
            return self.db_manager.get_stats()
        except DatabaseError as e:
            logger.error(f"Failed to get database statistics: {e}")
            raise