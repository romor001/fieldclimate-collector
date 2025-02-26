"""Error handling utilities for FieldClimate application."""

import logging
import time
from functools import wraps
from typing import Any, Callable, List, Optional, Type, TypeVar, cast

# Logger for this module
logger = logging.getLogger(__name__)

# Type variables for generic function types
F = TypeVar("F", bound=Callable[..., Any])
T = TypeVar("T")


class FieldClimateError(Exception):
    """Base exception for all FieldClimate errors."""

    pass


class APIError(FieldClimateError):
    """Base exception for API-related errors."""

    pass


class APIAuthError(APIError):
    """Exception raised for API authentication errors."""

    pass


class APIRateLimitError(APIError):
    """Exception raised when API rate limits are exceeded."""

    pass


class APIResponseError(APIError):
    """Exception raised for unexpected API responses."""

    pass


class APITimeoutError(APIError):
    """Exception raised for API timeout errors."""

    pass


class ConfigError(FieldClimateError):
    """Exception raised for configuration errors."""

    pass


class DatabaseError(FieldClimateError):
    """Exception raised for database errors."""

    pass


def retry_with_backoff(
    max_retries: int = 3,
    initial_backoff: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: Optional[List[Type[Exception]]] = None,
) -> Callable[[F], F]:
    """Decorator for functions that should retry with exponential backoff.
    
    Args:
        max_retries: Maximum number of retry attempts.
        initial_backoff: Initial backoff time in seconds.
        backoff_factor: Factor to multiply backoff by after each attempt.
        exceptions: List of exception types to catch and retry on.
                   Defaults to [APIError, DatabaseError].
    
    Returns:
        A decorator function.
    """
    if exceptions is None:
        exceptions = [APIError, DatabaseError]

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            retries = 0
            backoff = initial_backoff

            while True:
                try:
                    return func(*args, **kwargs)
                except tuple(exceptions) as e:
                    retries += 1
                    if retries > max_retries:
                        logger.error(
                            f"Max retries ({max_retries}) exceeded for {func.__name__}: {e}"
                        )
                        raise

                    # Add jitter to avoid thundering herd problem (0.8-1.2 of backoff)
                    jitter = 0.8 + 0.4 * (time.time() % 1)
                    sleep_time = backoff * jitter
                    
                    logger.warning(
                        f"Retry {retries}/{max_retries} for {func.__name__} "
                        f"in {sleep_time:.2f}s: {e}"
                    )
                    
                    time.sleep(sleep_time)
                    backoff *= backoff_factor

        return cast(F, wrapper)

    return decorator


class RateLimiter:
    """Simple rate limiter to control request frequency."""

    def __init__(self, requests_per_hour: int = 8000):
        """Initialize the rate limiter.
        
        Args:
            requests_per_hour: Maximum number of requests per hour.
        """
        self.requests_per_hour = requests_per_hour
        self.request_interval = 3600.0 / requests_per_hour  # Time between requests
        self.last_request_time = 0.0
        self.request_count = 0

    def wait(self) -> None:
        """Wait until it's safe to make another request."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time

        if time_since_last < self.request_interval:
            sleep_time = self.request_interval - time_since_last
            time.sleep(sleep_time)

        self.last_request_time = time.time()
        self.request_count += 1

    def reset(self) -> None:
        """Reset the request counter."""
        self.request_count = 0
        self.last_request_time = 0.0