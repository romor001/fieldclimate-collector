"""Command-line interface for FieldClimate data collector."""

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fieldclimate.collector.data_collector import DataCollector
from fieldclimate.config.config_manager import ConfigManager, ConfigError
from fieldclimate.utils.logging import setup_logging
from fieldclimate.utils.helpers import parse_datetime


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments.
    
    Returns:
        Parsed arguments.
    """
    parser = argparse.ArgumentParser(
        description="FieldClimate weather station data collector"
    )
    
    parser.add_argument(
        "--config",
        "-c",
        type=str,
        help="Path to configuration file (default: config.yaml)",
    )
    
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output",
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Collect command
    collect_parser = subparsers.add_parser(
        "collect", help="Collect data from all enabled stations"
    )
    
    # Collect specific station command
    station_parser = subparsers.add_parser(
        "station", help="Collect data for a specific station"
    )
    station_parser.add_argument(
        "station_id", type=str, help="ID of the station"
    )
    station_parser.add_argument(
        "--start-date",
        "-s",
        type=str,
        help="Start date (ISO format, e.g., 2023-01-01T00:00:00Z)",
    )
    station_parser.add_argument(
        "--end-date",
        "-e",
        type=str,
        help="End date (ISO format, e.g., 2023-01-31T23:59:59Z)",
    )
    station_parser.add_argument(
        "--days",
        "-d",
        type=int,
        help="Number of days to collect (from now if no end date, or before end date)",
    )
    
    # Stats command
    stats_parser = subparsers.add_parser(
        "stats", help="Show database statistics"
    )
    stats_parser.add_argument(
        "--json",
        "-j",
        action="store_true",
        help="Output statistics as JSON",
    )
    
    return parser.parse_args()


def setup_environment(args: argparse.Namespace) -> tuple:
    """Set up environment based on command line arguments.
    
    Args:
        args: Parsed command-line arguments.
        
    Returns:
        Tuple of (config_manager, data_collector).
        
    Raises:
        ConfigError: If configuration is invalid.
    """
    # Initialize configuration
    try:
        config_manager = ConfigManager(args.config)
    except ConfigError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Set up logging
    log_config = config_manager.get("logging") or {}
    if args.verbose:
        log_config["level"] = "DEBUG"
    logger = setup_logging(log_config)
    
    # Initialize data collector
    data_collector = DataCollector(config_manager)
    
    return config_manager, data_collector


def run_collect(
    data_collector: DataCollector, args: argparse.Namespace
) -> None:
    """Run data collection for all stations.
    
    Args:
        data_collector: Data collector instance.
        args: Parsed command-line arguments.
    """
    try:
        stats = data_collector.run()
        
        # Print summary
        print("\nCollection Summary:")
        print(f"- Started: {stats['start_time']}")
        print(f"- Ended: {stats['end_time']}")
        print(f"- Duration: {stats['duration_seconds']:.2f} seconds")
        print(f"- Stations processed: {stats['stations_processed']}")
        print(f"- Stations successful: {stats['stations_successful']}")
        print(f"- Stations failed: {stats['stations_failed']}")
        print(f"- Sensors processed: {stats['sensors_processed']}")
        print(f"- Measurements added: {stats['measurements_added']}")
        
        if stats["errors"]:
            print("\nErrors:")
            for error in stats["errors"]:
                print(f"- {error}")
    
    except Exception as e:
        print(f"Error during data collection: {e}", file=sys.stderr)
        sys.exit(1)


def run_station_collect(
    data_collector: DataCollector, args: argparse.Namespace
) -> None:
    """Run data collection for a specific station.
    
    Args:
        data_collector: Data collector instance.
        args: Parsed command-line arguments.
    """
    try:
        station_id = args.station_id
        
        # Parse dates
        start_date = None
        end_date = None
        
        if args.start_date:
            start_date = parse_datetime(args.start_date)
        
        if args.end_date:
            end_date = parse_datetime(args.end_date)
        
        # Handle days parameter
        if args.days:
            if end_date and not start_date:
                # Calculate start date based on end date and days
                start_date = end_date - timedelta(days=args.days)
            elif not end_date:
                # Calculate start date based on now and days
                end_date = datetime.now()
                start_date = end_date - timedelta(days=args.days)
        
        # Collect data
        result = data_collector.collect_station_data(
            station_id=station_id,
            start_date=start_date,
            end_date=end_date,
        )
        
        # Print summary
        total_measurements = sum(result.values())
        print(f"\nCollected {total_measurements} measurements from {len(result)} sensors")
        
        # Print per-sensor breakdown
        if result:
            print("\nSensor breakdown:")
            for sensor_id, count in result.items():
                print(f"- {sensor_id}: {count} measurements")
    
    except Exception as e:
        print(f"Error during station data collection: {e}", file=sys.stderr)
        sys.exit(1)


def run_stats(
    data_collector: DataCollector, args: argparse.Namespace
) -> None:
    """Show database statistics.
    
    Args:
        data_collector: Data collector instance.
        args: Parsed command-line arguments.
    """
    try:
        stats = data_collector.get_database_stats()
        
        if args.json:
            # Format database size to make it more readable
            if "database_size_bytes" in stats:
                stats["database_size_mb"] = stats["database_size_bytes"] / (1024 * 1024)
            print(json.dumps(stats, indent=2))
        else:
            print("\nDatabase Statistics:")
            print(f"- Total stations: {stats.get('station_count', 0)}")
            print(f"- Enabled stations: {stats.get('enabled_station_count', 0)}")
            print(f"- Total sensors: {stats.get('sensor_count', 0)}")
            print(f"- Total measurements: {stats.get('measurement_count', 0)}")
            
            # Format database size to make it more readable
            if "database_size_bytes" in stats:
                size_mb = stats["database_size_bytes"] / (1024 * 1024)
                print(f"- Database size: {size_mb:.2f} MB")
    
    except Exception as e:
        print(f"Error retrieving database statistics: {e}", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    """Main entry point for the CLI."""
    args = parse_args()
    
    # Set default command if not specified
    if not args.command:
        args.command = "collect"
    
    # Set up environment
    _, data_collector = setup_environment(args)
    
    # Execute command
    if args.command == "collect":
        run_collect(data_collector, args)
    elif args.command == "station":
        run_station_collect(data_collector, args)
    elif args.command == "stats":
        run_stats(data_collector, args)


if __name__ == "__main__":
    main()