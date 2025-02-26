"""Helper functions for FieldClimate dashboards."""

import os
import sqlite3
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


def get_database_path() -> str:
    """Get the path to the SQLite database file.
    
    Returns:
        Path to the database file.
    """
    # Default database path
    default_path = "../data/fieldclimate.db"
    
    # Check if path is overridden by environment variable
    db_path = os.environ.get("FIELDCLIMATE_DB_PATH", default_path)
    
    return db_path


def connect_to_database() -> sqlite3.Connection:
    """Connect to the SQLite database.
    
    Returns:
        SQLite connection object.
    """
    db_path = get_database_path()
    conn = sqlite3.connect(db_path)
    
    # Enable foreign keys
    conn.execute("PRAGMA foreign_keys = ON")
    
    # Convert rows to dictionaries
    conn.row_factory = sqlite3.Row
    
    return conn


def get_all_stations() -> pd.DataFrame:
    """Get all stations from the database.
    
    Returns:
        DataFrame with station data.
    """
    conn = connect_to_database()
    query = "SELECT * FROM stations"
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    return df


def get_station_details(station_id: str) -> Dict[str, Any]:
    """Get detailed information about a station.
    
    Args:
        station_id: Station ID.
        
    Returns:
        Dictionary with station details.
    """
    conn = connect_to_database()
    cursor = conn.cursor()
    
    query = "SELECT * FROM stations WHERE id = ?"
    cursor.execute(query, (station_id,))
    result = cursor.fetchone()
    
    conn.close()
    
    if result:
        return dict(result)
    
    return {}


def get_station_sensors(station_id: str) -> pd.DataFrame:
    """Get all sensors for a station.
    
    Args:
        station_id: Station ID.
        
    Returns:
        DataFrame with sensor data.
    """
    conn = connect_to_database()
    query = "SELECT * FROM sensors WHERE station_id = ?"
    df = pd.read_sql_query(query, conn, params=(station_id,))
    conn.close()
    
    return df


def get_sensor_data(
    sensor_id: str,
    start_date: Optional[Union[str, datetime]] = None,
    end_date: Optional[Union[str, datetime]] = None,
    limit: Optional[int] = None,
) -> pd.DataFrame:
    """Get measurement data for a sensor within a time range.
    
    Args:
        sensor_id: Sensor ID.
        start_date: Start date for data retrieval.
        end_date: End date for data retrieval.
        limit: Maximum number of rows to return.
        
    Returns:
        DataFrame with measurement data.
    """
    conn = connect_to_database()
    
    # Build query
    query = "SELECT * FROM measurements WHERE sensor_id = ?"
    params = [sensor_id]
    
    if start_date:
        if isinstance(start_date, datetime):
            start_date = start_date.isoformat()
        query += " AND timestamp >= ?"
        params.append(start_date)
    
    if end_date:
        if isinstance(end_date, datetime):
            end_date = end_date.isoformat()
        query += " AND timestamp <= ?"
        params.append(end_date)
    
    query += " ORDER BY timestamp"
    
    if limit:
        query += " LIMIT ?"
        params.append(limit)
    
    # Execute query
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    
    # Convert timestamp to datetime
    if not df.empty:
        df["timestamp"] = pd.to_datetime(df["timestamp"])
    
    return df


def get_latest_measurements(station_id: str) -> pd.DataFrame:
    """Get the latest measurement for each sensor in a station.
    
    Args:
        station_id: Station ID.
        
    Returns:
        DataFrame with latest measurements.
    """
    conn = connect_to_database()
    
    query = """
    SELECT s.id as sensor_id, s.name as sensor_name, s.type, s.unit, 
           m.timestamp, m.value
    FROM sensors s
    JOIN (
        SELECT sensor_id, MAX(timestamp) as max_timestamp
        FROM measurements
        GROUP BY sensor_id
    ) latest ON s.id = latest.sensor_id
    JOIN measurements m ON latest.sensor_id = m.sensor_id 
                       AND latest.max_timestamp = m.timestamp
    WHERE s.station_id = ?
    ORDER BY s.name
    """
    
    df = pd.read_sql_query(query, conn, params=(station_id,))
    conn.close()
    
    # Convert timestamp to datetime
    if not df.empty:
        df["timestamp"] = pd.to_datetime(df["timestamp"])
    
    return df


def get_daily_statistics(
    sensor_id: str,
    start_date: Optional[Union[str, datetime]] = None,
    end_date: Optional[Union[str, datetime]] = None,
) -> pd.DataFrame:
    """Calculate daily statistics for a sensor.
    
    Args:
        sensor_id: Sensor ID.
        start_date: Start date for data retrieval.
        end_date: End date for data retrieval.
        
    Returns:
        DataFrame with daily statistics.
    """
    # Get raw data
    df = get_sensor_data(sensor_id, start_date, end_date)
    
    if df.empty:
        return pd.DataFrame()
    
    # Convert timestamp to datetime if not already
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    
    # Extract date (without time)
    df["date"] = df["timestamp"].dt.date
    
    # Group by date and calculate statistics
    daily_stats = df.groupby("date").agg(
        min_value=("value", "min"),
        max_value=("value", "max"),
        mean_value=("value", "mean"),
        count=("value", "count"),
    ).reset_index()
    
    return daily_stats


def plot_sensor_data(
    sensor_data: pd.DataFrame,
    sensor_name: str,
    sensor_unit: str,
    plot_type: str = "line",
) -> go.Figure:
    """Generate a plot for sensor data.
    
    Args:
        sensor_data: DataFrame with sensor measurements.
        sensor_name: Name of the sensor for the plot title.
        sensor_unit: Unit of measurement.
        plot_type: Type of plot (line, bar, scatter).
        
    Returns:
        Plotly figure object.
    """
    if sensor_data.empty:
        # Create empty figure with message
        fig = go.Figure()
        fig.add_annotation(
            text="No data available",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=20),
        )
        fig.update_layout(
            title=f"{sensor_name} - No Data",
            height=400,
        )
        return fig
    
    # Determine the appropriate plot type
    if plot_type == "bar":
        fig = px.bar(
            sensor_data,
            x="timestamp",
            y="value",
            title=f"{sensor_name} ({sensor_unit})",
        )
    elif plot_type == "scatter":
        fig = px.scatter(
            sensor_data,
            x="timestamp",
            y="value",
            title=f"{sensor_name} ({sensor_unit})",
        )
    else:  # Default to line plot
        fig = px.line(
            sensor_data,
            x="timestamp",
            y="value",
            title=f"{sensor_name} ({sensor_unit})",
        )
    
    # Update layout
    fig.update_layout(
        xaxis_title="Time",
        yaxis_title=sensor_unit,
        height=400,
        hovermode="x unified",
    )
    
    return fig


def plot_daily_statistics(
    daily_stats: pd.DataFrame,
    sensor_name: str,
    sensor_unit: str,
) -> go.Figure:
    """Generate a plot for daily sensor statistics.
    
    Args:
        daily_stats: DataFrame with daily statistics.
        sensor_name: Name of the sensor for the plot title.
        sensor_unit: Unit of measurement.
        
    Returns:
        Plotly figure object.
    """
    if daily_stats.empty:
        # Create empty figure with message
        fig = go.Figure()
        fig.add_annotation(
            text="No data available",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=20),
        )
        fig.update_layout(
            title=f"{sensor_name} - Daily Statistics - No Data",
            height=400,
        )
        return fig
    
    # Create figure
    fig = go.Figure()
    
    # Add min-max range
    fig.add_trace(
        go.Scatter(
            x=daily_stats["date"],
            y=daily_stats["min_value"],
            mode="lines",
            line=dict(width=0),
            showlegend=False,
        )
    )
    fig.add_trace(
        go.Scatter(
            x=daily_stats["date"],
            y=daily_stats["max_value"],
            mode="lines",
            line=dict(width=0),
            fill="tonexty",
            fillcolor="rgba(52, 152, 219, 0.3)",
            name="Min-Max Range",
        )
    )
    
    # Add mean line
    fig.add_trace(
        go.Scatter(
            x=daily_stats["date"],
            y=daily_stats["mean_value"],
            mode="lines+markers",
            line=dict(color="rgb(41, 128, 185)", width=2),
            name="Daily Mean",
        )
    )
    
    # Update layout
    fig.update_layout(
        title=f"{sensor_name} - Daily Statistics ({sensor_unit})",
        xaxis_title="Date",
        yaxis_title=sensor_unit,
        height=400,
        hovermode="x unified",
    )
    
    return fig


def create_sensor_type_plots(
    station_id: str,
    sensor_type: str,
    start_date: Optional[Union[str, datetime]] = None,
    end_date: Optional[Union[str, datetime]] = None,
) -> List[go.Figure]:
    """Create plots for sensors of a specific type.
    
    Args:
        station_id: Station ID.
        sensor_type: Type of sensors to plot.
        start_date: Start date for data retrieval.
        end_date: End date for data retrieval.
        
    Returns:
        List of Plotly figure objects.
    """
    # Get all sensors for the station
    sensors_df = get_station_sensors(station_id)
    
    # Filter by sensor type
    type_sensors = sensors_df[sensors_df["type"].str.contains(sensor_type, case=False)]
    
    if type_sensors.empty:
        return []
    
    figures = []
    
    # Determine appropriate plot type
    plot_type = "line"
    if sensor_type.lower() in ["rain", "precipitation"]:
        plot_type = "bar"
    
    # Create a plot for each sensor
    for _, sensor in type_sensors.iterrows():
        sensor_id = sensor["id"]
        sensor_name = sensor["name"]
        sensor_unit = sensor["unit"] or ""
        
        # Get sensor data
        data = get_sensor_data(sensor_id, start_date, end_date)
        
        # Create plot
        fig = plot_sensor_data(data, sensor_name, sensor_unit, plot_type)
        figures.append(fig)
        
        # Create daily statistics plot if appropriate
        if len(data) > 10:  # Only if we have enough data
            daily_stats = get_daily_statistics(sensor_id, start_date, end_date)
            if not daily_stats.empty:
                stats_fig = plot_daily_statistics(daily_stats, sensor_name, sensor_unit)
                figures.append(stats_fig)
    
    return figures