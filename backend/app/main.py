import time
import os
from collections import defaultdict
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response, status
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from backend.app.config import get_settings
from backend.app.database import init_db
from backend.app.routes import health, verification, certificates

settings = get_settings()

MAX_REQUEST_BODY_BYTES = 16 * 1024  # 16 KB request body limit


class InMemoryRateLimiter:
    """
    Lightweight in-memory rate limiter per IP.
    Note: State is stored per-instance in RAM and resets when the application restarts.
    Provides free, zero-dependency abuse protection suitable for low-resource hosting.
    """
    def __init__(self, max_requests: int = 30, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = defaultdict(list)

    def is_rate_limited(self, client_ip: str, limit: int = None) -> bool:
        max_allowed = limit or self.max_requests
        now = time.time()
        # Clean timestamps older than window
        timestamps = [ts for ts in self.requests[client_ip] if now - ts < self.window_seconds]
        if len(timestamps) >= max_allowed:
            self.requests[client_ip] = timestamps
            return True
        timestamps.append(now)
        self.requests[client_ip] = timestamps
        return False


rate_limiter = InMemoryRateLimiter(
    max_requests=settings.RATE_LIMIT_MAX_REQUESTS,
    window_seconds=settings.RATE_LIMIT_WINDOW_SECONDS
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database tables non-destructively (CREATE TABLE IF NOT EXISTS)
    init_db()
    yield


app = FastAPI(
    title=settings.APP_NAME,
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url=None
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_and_rate_limit_middleware(request: Request, call_next):
    # 1. Payload size limit protection
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > MAX_REQUEST_BODY_BYTES:
        return JSONResponse(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            content={"detail": "Request payload too large."}
        )

    # 2. Rate limiting on API routes
    if settings.RATE_LIMIT_ENABLED and request.url.path.startswith("/api/"):
        client_ip = request.client.host if request.client else "unknown"
        # Stricter limit on verification to prevent enumeration (15/min)
        limit = 15 if request.url.path == "/api/verify" else settings.RATE_LIMIT_MAX_REQUESTS
        if rate_limiter.is_rate_limited(client_ip, limit=limit):
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": "Too many requests. Please wait a moment before trying again."}
            )

    response = await call_next(request)

    # 3. Security response headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    
    return response


# Include API Routers
app.include_router(health.router)
app.include_router(verification.router)
app.include_router(certificates.router)

# Mount Frontend static files
frontend_dir = os.path.join(os.getcwd(), "frontend")
if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
