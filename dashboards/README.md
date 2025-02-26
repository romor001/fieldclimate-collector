# FieldClimate Dashboards

This directory contains interactive Quarto dashboards for visualizing weather data collected from FieldClimate weather stations.

## Setup

### Prerequisites

1. Install Quarto CLI from [https://quarto.org/docs/get-started/](https://quarto.org/docs/get-started/)

2. Install required Python packages:
   ```
   pip install pandas plotly numpy
   ```

### Dashboard Overview

This dashboard suite consists of:

1. **Overview Dashboard** (`overview.qmd`): A summary of all weather stations, including their status, locations on a map, and latest measurements.

2. **Station Dashboard** (`station.qmd`): Detailed view for a specific weather station, showing all sensor data with charts and statistics.

## Usage

### Preview Dashboards

To preview the overview dashboard:

```bash
quarto preview overview.qmd
```

To preview a specific station dashboard:

```bash
quarto preview station.qmd -P station_id=00208E6F
```

### Render Static Versions

To render static HTML versions of the dashboards:

```bash
quarto render overview.qmd
quarto render station.qmd -P station_id=00208E6F
```

### Publishing

To publish the dashboards as a website:

```bash
quarto publish [destination] .
```

Replace `[destination]` with your preferred publishing target (e.g., `github-pages`, `netlify`).

## Customization

### Styling

The dashboards use a custom Quarto theme defined in:

- `_brand.yml`: Brand colors, fonts, and general styling
- `assets/styles.scss`: Custom SCSS styles

### Dashboard Helpers

Common functions for data retrieval and visualization are in:

- `scripts/dashboard_helpers.py`: Utility functions for database access and chart creation

## Database Connection

The dashboards connect to the SQLite database created by the FieldClimate collector. By default, the database path is set to `../data/fieldclimate.db`.

To use a different database location, set the `FIELDCLIMATE_DB_PATH` environment variable:

```bash
export FIELDCLIMATE_DB_PATH=/path/to/your/fieldclimate.db
quarto preview overview.qmd
```