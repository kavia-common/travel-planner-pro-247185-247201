"""
Travel Planner Pro — FastAPI Backend Application.

Main entry point that configures CORS, registers all route modules,
and provides health-check and WebSocket documentation endpoints.

Title: Travel Planner Pro API
Version: 1.0.0
"""

import os
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

# ─── OpenAPI tags for documentation grouping ───
openapi_tags = [
    {"name": "Health", "description": "Health check endpoints"},
    {"name": "Authentication", "description": "User registration, login, and profile"},
    {"name": "Trips", "description": "CRUD operations for trips"},
    {"name": "Itinerary", "description": "Itinerary days and activities management"},
    {"name": "Budget & Expenses", "description": "Budget and expense tracking"},
    {"name": "Packing", "description": "Packing checklist management"},
    {"name": "Sharing", "description": "Trip sharing and collaboration"},
    {"name": "Notifications", "description": "User notifications"},
    {"name": "Export", "description": "PDF export of trip itinerary"},
    {"name": "Admin", "description": "Admin user management and moderation"},
    {"name": "WebSocket", "description": "Real-time notification WebSocket connections"},
]

app = FastAPI(
    title="Travel Planner Pro API",
    description=(
        "Backend API for Travel Planner Pro. Supports user authentication (JWT), "
        "trip CRUD, day-by-day itinerary planning, activity management, budget & "
        "expense tracking, packing checklists, trip sharing with permission controls, "
        "PDF export, notifications, and admin moderation."
    ),
    version="1.0.0",
    openapi_tags=openapi_tags,
)

# ─── CORS Configuration ───
allowed_origins_str = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,http://localhost:4000"
)
allowed_origins = [o.strip() for o in allowed_origins_str.split(",") if o.strip()]

# Also add FRONTEND_URL and SITE_URL if present and not already listed
for env_key in ("FRONTEND_URL", "SITE_URL"):
    extra_origin = os.getenv(env_key, "")
    if extra_origin and extra_origin not in allowed_origins:
        allowed_origins.append(extra_origin)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*"],  # Allow all headers to ensure JWT Authorization works
    max_age=int(os.getenv("CORS_MAX_AGE", "3600")),
)

# ─── Register Routers ───
from src.api.routes_auth import router as auth_router
from src.api.routes_trips import router as trips_router
from src.api.routes_itinerary import router as itinerary_router
from src.api.routes_budget import router as budget_router
from src.api.routes_packing import router as packing_router
from src.api.routes_sharing import router as sharing_router
from src.api.routes_notifications import router as notifications_router
from src.api.routes_export import router as export_router
from src.api.routes_admin import router as admin_router

app.include_router(auth_router)
app.include_router(trips_router)
app.include_router(itinerary_router)
app.include_router(budget_router)
app.include_router(packing_router)
app.include_router(sharing_router)
app.include_router(notifications_router)
app.include_router(export_router)
app.include_router(admin_router)


# ─── Health Check ───

# PUBLIC_INTERFACE
@app.get(
    "/",
    tags=["Health"],
    summary="Health Check",
    description="Returns a simple health status to confirm the API is running.",
)
def health_check():
    """
    Health check endpoint.

    Returns:
        JSON object with status message.
    """
    return {"status": "healthy", "message": "Travel Planner Pro API is running"}


# ─── WebSocket Documentation Route ───

# PUBLIC_INTERFACE
@app.get(
    "/api/ws/info",
    tags=["WebSocket"],
    summary="WebSocket connection info",
    description=(
        "Provides usage instructions for the real-time notification WebSocket. "
        "Connect to ws://<host>:<port>/ws/notifications with a valid JWT token "
        "as a query parameter: ?token=<jwt_token>"
    ),
)
def websocket_info():
    """
    WebSocket usage information endpoint.

    Returns:
        JSON with WebSocket connection details and usage instructions.
    """
    ws_url = os.getenv("WS_URL", "ws://localhost:3001/ws")
    return {
        "websocket_endpoint": f"{ws_url}/notifications",
        "usage": "Connect with query parameter ?token=<jwt_token>",
        "description": "Real-time notifications are pushed to connected clients.",
        "events": [
            "trip_reminder",
            "share_invite",
            "trip_update",
            "budget_alert",
            "system",
        ],
    }
