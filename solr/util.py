import functools
import os
from dotenv import load_dotenv

def with_env(required_variables: list[str] | None = None):
    """
    Decorator to ensure that environment variables are set before running a function.

    Args:
        required_variables (list[str] | None): A list of environment variable names that are required.
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