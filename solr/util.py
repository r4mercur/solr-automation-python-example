import functools
import json
import logging
import os
from pathlib import Path
from typing import List, Optional

import pyfiglet
import requests
from dotenv import load_dotenv
from prometheus_client import REGISTRY

JSON_DIR = Path(__file__).resolve().parent.parent / "json"

# Timeout in seconds for HTTP calls against the Solr admin APIs
HTTP_TIMEOUT = 60


def require_env(*names: str) -> tuple[str, ...]:
    """
    Load the .env file and return the values of the given environment variables.

    Raises:
        ValueError: If one of the variables is not set.
    """
    load_dotenv()

    missing_variables = [name for name in names if not os.getenv(name)]
    if missing_variables:
        raise ValueError(
            f"Missing required environment variables: {', '.join(missing_variables)}"
        )
    return tuple(os.environ[name] for name in names)


def with_env(required_variables: Optional[List[str]] = None):
    """
    Decorator to ensure that environment variables are set before running a function.

    Args:
        required_variables (Optional[List[str]]): A list of environment variable names that are required.
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            require_env(*(required_variables or []))
            return func(*args, **kwargs)

        return wrapper

    return decorator


def setup_logging() -> None:
    """Configure the root logger. The level can be set via LOG_LEVEL (default: INFO)."""
    load_dotenv()
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    )
    # These libraries log every request/connection step on INFO, which drowns our own logs
    for noisy_logger in ("pika", "pysolr"):
        logging.getLogger(noisy_logger).setLevel(logging.WARNING)


def load_json(filename: str) -> dict:
    """Load a file from the project's json/ directory, independent of the working directory."""
    return json.loads((JSON_DIR / filename).read_text(encoding="utf-8"))


def check_response(response: requests.Response) -> requests.Response:
    """Like raise_for_status(), but keeps Solr's error message from the response body."""
    if not response.ok:
        raise requests.HTTPError(
            f"{response.status_code} {response.reason} for {response.url}: {response.text}",
            response=response,
        )
    return response


def print_ascii_title(title: str) -> None:
    art = pyfiglet.figlet_format(title)

    art_lines = [line for line in art.split("\n") if line.strip()]
    max_width = max(len(line) for line in art_lines)

    print("#" * (max_width + 4))
    for line in art_lines:
        print(f"# {line.ljust(max_width)} #")
    print("#" * (max_width + 4))


def get_or_create_metric(name: str, metric_class, *args, **kwargs):
    """Get existing metric or create new one if it doesn't exist."""
    try:
        existing = REGISTRY._names_to_collectors.get(name)
        if existing:
            return existing
    except:
        pass
    return metric_class(name, *args, **kwargs)
