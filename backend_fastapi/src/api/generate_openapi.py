"""
OpenAPI schema generator for Travel Planner Pro.

Generates the OpenAPI JSON specification file from the FastAPI app
and writes it to the interfaces directory within the backend container.

Usage:
    cd backend_fastapi && python -m src.api.generate_openapi
"""

import json
import os
import sys

# Ensure we can import the app regardless of working directory
_this_dir = os.path.dirname(os.path.abspath(__file__))
_backend_root = os.path.abspath(os.path.join(_this_dir, "..", ".."))
if _backend_root not in sys.path:
    sys.path.insert(0, _backend_root)

from src.api.main import app  # noqa: E402

# PUBLIC_INTERFACE
def generate_openapi_spec() -> dict:
    """
    Generate the OpenAPI JSON schema from the FastAPI application.

    Returns:
        The OpenAPI schema as a dictionary.
    """
    return app.openapi()


if __name__ == "__main__":
    openapi_schema = generate_openapi_spec()

    # Write to interfaces/ directory at the backend container root
    output_dir = os.path.join(_backend_root, "interfaces")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "openapi.json")

    with open(output_path, "w") as f:
        json.dump(openapi_schema, f, indent=2)

    print(f"OpenAPI schema written to {output_path}")
