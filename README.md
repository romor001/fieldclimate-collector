# FieldClimate Weather Station Data Collection and Visualization

This project collects weather data from Pessl's FieldClimate platform and visualizes it through interactive dashboards. The system consists of two decoupled components: a data collection service that periodically fetches data from weather stations and stores it in a local database, and a visualization component that presents this data through Quarto dashboards.

## Features

- **Automatic Data Collection**: Periodically fetches data from FieldClimate weather stations
- **Sensor Auto-Discovery**: Automatically detects and configures sensors for new stations
- **Efficient Data Storage**: Optimized SQLite database with indexing for fast queries
- **Interactive Dashboards**: Rich visualizations using Quarto and Plotly
- **Multi-Station Support**: Manage and monitor multiple weather stations in one system
- **Historical Data Backfilling**: Retrieve past data for new stations or recovery
- **HMAC Authentication**: Secure API interactions with FieldClimate platform
- **Rate Limiting Controls**: Respect API limits to prevent throttling
- **Flexible Configuration**: Extensive configuration options with sensible defaults

## Architecture

The system is structured into two main components:

1. **Data Collection Service**:
   - API client for secure communication with FieldClimate
   - Station manager for discovering and tracking stations and sensors
   - Database manager for efficient data storage
   - Error handling with retry capabilities

2. **Data Visualization**:
   - Overview dashboard showing all stations status and locations
   - Detailed station dashboards with interactive charts
   - Time range selection for data exploration
   - Categorized sensor data visualization

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/fieldclimate-collector.git
   cd fieldclimate-collector
   ```

2. Create a virtual environment and install dependencies:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   pip install -e .
   ```

3. Create a secrets directory and add your API keys:
   ```
   mkdir -p secrets
   echo "your_public_key" > secrets/public_key.txt
   echo "your_private_key" > secrets/private_key.txt
   ```

4. Copy the example configuration:
   ```
   cp config.yaml.example config.yaml
   ```

5. Edit the configuration file to add your weather stations.

6. Install Quarto for dashboards (optional):
   - Download from [https://quarto.org/docs/get-started/](https://quarto.org/docs/get-started/)

## Usage

### Data Collection

Run the data collector to fetch data from your weather stations:

```
fieldclimate-collector
```

For more options:

```
fieldclimate-collector --help
```

Specific commands:

```
# Collect data from all enabled stations
fieldclimate-collector collect

# Collect data for a specific station
fieldclimate-collector station 00208E6F

# Backfill data for the last 30 days
fieldclimate-collector station 00208E6F --days 30

# Show database statistics
fieldclimate-collector stats
```

### Visualization

To view the dashboards, you need to have Quarto installed. Then run:

```
cd dashboards
quarto preview overview.qmd
```

To view a specific station:

```
quarto preview station.qmd -P station_id=00208E6F
```

To change the time period:

```
quarto preview station.qmd -P station_id=00208E6F -P days=30
```

## Configuration

The `config.yaml` file contains all the configuration options:

```yaml
# API connection settings
api:
  public_key_path: "secrets/public_key.txt"
  private_key_path: "secrets/private_key.txt"
  base_url: "https://api.fieldclimate.com/v1"
  request_timeout_seconds: 30
  max_retries: 3

# Database settings
database:
  path: "data/fieldclimate.db"
  optimize_after_collection: false

# Data collection settings
collection:
  interval_minutes: 60
  backfill_days: 7
  batch_size: 100

# Weather stations
stations:
  - id: "00208E6F"
    name: "FHSWF Soest"
    enabled: true
    # Sensors will be auto-discovered

# Logging configuration
logging:
  level: "INFO"
  file: "logs/fieldclimate.log"
  max_size: 10485760  # 10 MB
  backup_count: 5
```

## Automated Data Collection

### Cron Job (Linux/macOS)

To set up automated data collection every hour:

```
0 * * * * /path/to/venv/bin/fieldclimate-collector --config /path/to/config.yaml
```

### Systemd Service (Linux)

Create a service file at `/etc/systemd/system/fieldclimate-collector.service`:

```ini
[Unit]
Description=FieldClimate Weather Data Collector
After=network.target

[Service]
Type=simple
User=yourusername
WorkingDirectory=/path/to/fieldclimate-collector
ExecStart=/path/to/venv/bin/fieldclimate-collector --config /path/to/config.yaml
Restart=on-failure
RestartSec=60

[Install]
WantedBy=multi-user.target
```

Enable and start the service:

```
sudo systemctl enable fieldclimate-collector.service
sudo systemctl start fieldclimate-collector.service
```

## Development

### Project Structure

```
fieldclimate-claude/
├── fieldclimate/
│   ├── collector/          # API and data collection
│   ├── database/           # Database models and manager
│   ├── config/             # Configuration handling
│   └── utils/              # Common utilities
├── dashboards/             # Quarto visualization
│   ├── assets/             # Dashboard styles 
│   ├── scripts/            # Dashboard helper scripts
│   ├── overview.qmd        # Main dashboard
│   └── station.qmd         # Station-specific dashboard
├── bin/                    # Command-line tools
├── tests/                  # Test suite
├── config.yaml.example     # Example configuration
└── README.md               # This file
```

### Running Tests

```
python -m pytest
```

## License

[MIT License](LICENSE)
