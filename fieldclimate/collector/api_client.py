"""FieldClimate API client for interacting with the FieldClimate platform."""

import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union

import requests
from requests.adapters import HTTPAdapter
from requests.auth import AuthBase
from urllib3.util.retry import Retry
import hmac
import hashlib

from fieldclimate.utils.error_handler import (
    APIAuthError,
    APIError,
    APIRateLimitError,
    APIResponseError,
    APITimeoutError,
    RateLimiter,
    retry_with_backoff,
)
from fieldclimate.utils.helpers import (
    format_datetime,
    parse_datetime,
)

# Set up module logger
logger = logging.getLogger(__name__)


# Class to perform HMAC authentication
class FieldClimateAuth(AuthBase):
    """Authentication handler for FieldClimate API requests."""
    
    def __init__(self, api_path: str, public_key: str, private_key: str, method: str = 'GET'):
        """Initialize the authentication handler.
        
        Args:
            api_path: The API endpoint path.
            public_key: Public API key.
            private_key: Private API key.
            method: HTTP method (GET, POST, etc.)
        """
        self._api_path = api_path
        self._public_key = public_key
        self._private_key = private_key
        self._method = method.upper()
    
    def __call__(self, request):
        """Add authentication headers to the request.
        
        Args:
            request: The request to authenticate.
            
        Returns:
            The authenticated request.
        """
        date_stamp = datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')
        request.headers['Date'] = date_stamp
        
        # Create message for signature
        msg = (self._method + self._api_path + date_stamp + self._public_key).encode('utf-8')
        
        # Generate signature
        signature = hmac.new(
            self._private_key.encode('utf-8'),
            msg,
            hashlib.sha256
        ).hexdigest()
        
        # Add authorization header
        request.headers['Authorization'] = f'hmac {self._public_key}:{signature}'
        
        return request


class FieldClimateClient:
    """Client for interacting with the FieldClimate API."""

    def __init__(
        self,
        public_key: str,
        private_key: str,
        base_url: str = "https://api.fieldclimate.com/v2",
        timeout: int = 30,
        max_retries: int = 3,
        requests_per_hour: int = 7200,  # 90% of limit to be safe
    ) -> None:
        """Initialize the FieldClimate API client.
        
        Args:
            public_key: Public API key.
            private_key: Private API key.
            base_url: Base URL for the API.
            timeout: Request timeout in seconds.
            max_retries: Maximum number of retries for failed requests.
            requests_per_hour: Maximum requests per hour (default: 7200, 90% of 8000 limit).
        """
        self.public_key = public_key
        self.private_key = private_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        
        # Set up session with retry
        self.session = requests.Session()
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Rate limiter to control request frequency
        self.rate_limiter = RateLimiter(requests_per_hour=requests_per_hour)

    @retry_with_backoff(
        max_retries=3, 
        initial_backoff=5.0, 
        exceptions=[APIResponseError, APITimeoutError]
    )
    def _request(
        self, 
        method: str, 
        endpoint: str, 
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Make a request to the FieldClimate API.
        
        Args:
            method: HTTP method (GET, POST, etc.).
            endpoint: API endpoint, will be appended to base_url.
            params: URL parameters for the request.
            data: JSON data to include in request body.
            headers: Additional headers to include.
            
        Returns:
            JSON response from the API.
            
        Raises:
            APIAuthError: If authentication fails.
            APIRateLimitError: If rate limit is exceeded.
            APIResponseError: If there's an unexpected response.
            APITimeoutError: If the request times out.
            APIError: For other API-related errors.
        """
        # Apply rate limiting
        self.rate_limiter.wait()
        
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        method = method.upper()
        api_path = f"/{endpoint.lstrip('/')}"
        
        # Prepare request data
        request_data = ""
        if data:
            request_data = json.dumps(data)
        
        # Prepare headers
        base_headers = {'Accept': 'application/json'}
        if data:
            base_headers['Content-Type'] = 'application/json'
        if headers:
            base_headers.update(headers)
        
        # Create authentication handler
        auth = FieldClimateAuth(
            api_path=api_path,
            public_key=self.public_key,
            private_key=self.private_key,
            method=method
        )
        
        try:
            # Log request details for debugging
            logger.debug(f"Request URL: {url}")
            logger.debug(f"Request Method: {method}")
            logger.debug(f"Request Headers: {base_headers}")
            if params:
                logger.debug(f"Request Params: {params}")
            if data:
                logger.debug(f"Request Data: {data}")
            
            # Make the request
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                data=request_data if data else None,
                headers=base_headers,
                auth=auth,  # Use the auth handler
                timeout=self.timeout
            )
            
            logger.debug(f"Response Status: {response.status_code}")
            logger.debug(f"Response Headers: {response.headers}")
            logger.debug(f"Response Body: {response.text[:200]}...")
            
            # Check for rate limiting
            if response.status_code == 429:
                logger.warning(f"Rate limit exceeded for {endpoint}")
                raise APIRateLimitError(f"Rate limit exceeded: {response.text}")
                
            # Check for auth errors
            if response.status_code in (401, 403):
                logger.error(f"Authentication error: {response.text}")
                raise APIAuthError(f"Authentication failed: {response.text}")
                
            # Raise for other bad responses
            response.raise_for_status()
            
            # Parse and return JSON response
            result = response.json()
            
            # Check for error in response body
            if isinstance(result, dict) and result.get("error"):
                logger.error(f"API error: {result.get('error')}")
                raise APIResponseError(f"API error: {result.get('error')}")
                
            return result
            
        except requests.exceptions.Timeout:
            logger.error(f"Request timeout for {endpoint}")
            raise APITimeoutError(f"Request timed out after {self.timeout} seconds")
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed for {endpoint}: {str(e)}")
            raise APIError(f"Request failed: {str(e)}")

    def get_stations(self) -> List[Dict[str, Any]]:
        """Get list of stations accessible to the user.
        
        Returns:
            List of station data objects.
        """
        logger.info("Fetching list of stations")
        result = self._request("GET", "user/stations")
        return result

    def get_station(self, station_id: str) -> Dict[str, Any]:
        """Get detailed information about a specific station.
        
        Args:
            station_id: ID of the station.
            
        Returns:
            Station details.
        """
        logger.info(f"Fetching details for station {station_id}")
        result = self._request("GET", f"station/{station_id}")
        return result

    def get_station_sensors(self, station_id: str) -> List[Dict[str, Any]]:
        """Get the list of sensors for a station.
        
        Args:
            station_id: ID of the station.
            
        Returns:
            List of sensor data objects.
        """
        logger.info(f"Discovering sensors for station {station_id}")
        result = self._request("GET", f"station/{station_id}/sensors")
        return result

    def get_sensor_data(
        self,
        station_id: str,
        sensor_id: str,
        start_date: Union[datetime, str],
        end_date: Optional[Union[datetime, str]] = None,
        data_group: str = "raw",
    ) -> Dict[str, Any]:
        """Get data for a specific sensor in a time range.
        
        Args:
            station_id: ID of the station.
            sensor_id: ID of the sensor.
            start_date: Start date for data retrieval.
            end_date: End date for data retrieval. If None, uses current time.
            data_group: Type of data to retrieve ('raw', 'hourly', 'daily').
                       We prefer 'raw' as specified in the requirements.
            
        Returns:
            Sensor data for the specified time period.
        """
        # Convert datetime objects to strings if needed
        if isinstance(start_date, datetime):
            start_date = format_datetime(start_date)
        
        if end_date is None:
            end_date = format_datetime(datetime.now().replace(microsecond=0))
        elif isinstance(end_date, datetime):
            end_date = format_datetime(end_date)
            
        logger.info(
            f"Fetching {data_group} data for station {station_id}, sensor {sensor_id} "
            f"from {start_date} to {end_date}"
        )
        
        params = {
            "date_from": start_date,
            "date_to": end_date,
            "group": data_group,
        }
        
        result = self._request(
            "GET",
            f"station/{station_id}/sensor/{sensor_id}/data",
            params=params
        )
        
        return result

    def get_station_data(
        self,
        station_id: str,
        start_date: Union[datetime, str],
        end_date: Optional[Union[datetime, str]] = None,
        data_group: str = "raw",
    ) -> Dict[str, Any]:
        """Get data for all sensors in a station for a time range.
        
        Args:
            station_id: ID of the station.
            start_date: Start date for data retrieval.
            end_date: End date for data retrieval. If None, uses current time.
            data_group: Type of data to retrieve ('raw', 'hourly', 'daily').
                       We prefer 'raw' as specified in the requirements.
            
        Returns:
            Data for all sensors for the specified time period.
        """
        # Convert datetime objects to strings if needed
        if isinstance(start_date, datetime):
            start_date = format_datetime(start_date)
        
        if end_date is None:
            end_date = format_datetime(datetime.now().replace(microsecond=0))
        elif isinstance(end_date, datetime):
            end_date = format_datetime(end_date)
            
        logger.info(
            f"Fetching {data_group} data for station {station_id} from {start_date} to {end_date}"
        )
        
        params = {
            "date_from": start_date,
            "date_to": end_date,
            "group": data_group,
        }
        
        result = self._request(
            "GET",
            f"station/{station_id}/data",
            params=params
        )
        
        return result