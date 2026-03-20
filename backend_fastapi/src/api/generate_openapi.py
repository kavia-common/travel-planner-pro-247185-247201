"""
OpenAPI schema generator for Travel Planner Pro.

Generates the OpenAPI JSON specification file from the FastAPI app
and writes it to the interfaces directory.
"""

import json
import os

from src.api.main import app

# Get the OpenAPI schema
openapi_schema = app.openapi()

# Write to file
output_dir = "interfaces"
os.makedirs(output_dir, exist_ok=True)
output_path = os.path.join(output_dir, "openapi.json")

with open(output_path, "w") as f:
    json.dump(openapi_schema, f, indent=2)

print(f"OpenAPI schema written to {output_path}")
