from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.db.prisma_client import connect_db, disconnect_db
from app.api.usage import router as usage_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage the application lifecycle.
    Connects to the database on startup and disconnects on shutdown.
    Using the lifespan context manager is the recommended approach in FastAPI
    (replaces the deprecated @app.on_event("startup/shutdown") pattern).
    """
    await connect_db()
    yield
    await disconnect_db()


app = FastAPI(title="Fidant Usage API", lifespan=lifespan)

# Allow the React dev server to call the API during local development.
# Restrict origins to your actual domain in production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(usage_router)


@app.exception_handler(404)
async def not_found_handler(request: Request, exc: Exception) -> JSONResponse:
    """Return a consistent JSON error body for unmatched routes."""
    return JSONResponse(
        status_code=404,
        content={"error": "not_found", "message": "Route not found"},
    )
