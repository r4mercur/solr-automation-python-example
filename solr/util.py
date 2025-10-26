import functools
import os
from typing import List, Optional

from dotenv import load_dotenv
from prometheus_client import REGISTRY


def with_env(required_variables: Optional[List[str]] = None):
    """
    Decorator to ensure that environment variables are set before running a function.

    Args:
        required_variables (Optional[List[str]]): A list of environment variable names that are required.
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            load_dotenv()

            if required_variables:
                missing_variables = [
                    var for var in required_variables if not os.getenv(var)
                ]
                if missing_variables:
                    raise ValueError(
                        f"Missing required environment variables: {', '.join(missing_variables)}"
                    )
            return func(*args, **kwargs)

        return wrapper

    return decorator


def get_or_create_metric(name: str, metric_class, *args, **kwargs):
    """Get existing metric or create new one if it doesn't exist."""
    try:
        existing = REGISTRY._names_to_collectors.get(name)
        if existing:
            return existing
    except:
        pass
    return metric_class(name, *args, **kwargs)
