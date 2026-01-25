import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from .api import calls, agents, dashboard
from .config import get_settings
from .db.database import engine
from .utils.error_handling import APIError, AudioValidationError

settings = get_settings()

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging all requests and responses."""
    
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())[:8]
        start_time = time.time()
        
        # Log request
        logger.info(
            f"[{request_id}] {request.method} {request.url.path} "
            f"- Client: {request.client.host if request.client else 'unknown'}"
        )
        
        try:
            response = await call_next(request)
            
            # Log response
            duration_ms = (time.time() - start_time) * 1000
            logger.info(
                f"[{request_id}] {request.method} {request.url.path} "
                f"- Status: {response.status_code} - Duration: {duration_ms:.0f}ms"
            )
            
            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id
            return response
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(
                f"[{request_id}] {request.method} {request.url.path} "
                f"- Error: {str(e)} - Duration: {duration_ms:.0f}ms"
            )
            raise


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting Call Center Audio Intelligence API (env: {settings.APP_ENV})")
    logger.info(f"Debug mode: {settings.DEBUG}")
    yield
    await engine.dispose()
    logger.info("Shutting down API")


app = FastAPI(
    title="Call Center Audio Intelligence API",
    description="AI-driven call center audio analysis for sales intelligence",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list if settings.is_production else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(APIError)
async def api_error_handler(request: Request, exc: APIError):
    """Handle custom API errors with proper status codes."""
    logger.warning(f"API Error: {exc.message} (status: {exc.status_code})")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.message,
            "error_type": exc.__class__.__name__,
            "retryable": exc.retryable,
        },
    )


@app.exception_handler(AudioValidationError)
async def audio_validation_error_handler(request: Request, exc: AudioValidationError):
    """Handle audio validation errors."""
    logger.warning(f"Audio Validation Error: {exc.message}")
    return JSONResponse(
        status_code=400,
        content={
            "detail": exc.message,
            "error_type": "AudioValidationError",
        },
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error_type": "InternalError"},
    )


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint for monitoring and container orchestration."""
    return {
        "status": "healthy",
        "service": "call-center-audio-intelligence",
        "environment": settings.APP_ENV,
        "version": "0.1.0"
    }


@app.get("/ready", tags=["Health"])
async def readiness_check():
    """Readiness check - verifies the service can handle requests."""
    try:
        # Could add database connectivity check here
        return {"status": "ready"}
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "error": str(e)}
        )


app.include_router(calls.router, prefix="/api/calls", tags=["Calls"])
app.include_router(agents.router, prefix="/api/agents", tags=["Agents"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])
