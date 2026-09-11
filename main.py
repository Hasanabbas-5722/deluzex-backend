import uuid
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.api import api_router
from app.core.config import settings
from app.core.database import init_db
from app.core.logger import app_logger, log_request, print_startup_banner
import uvicorn
import logging

# Silence standard uvicorn access logger to prevent duplicate plain logs
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

@asynccontextmanager
async def lifespan(app: FastAPI):
    db, ping_ms, is_connected = init_db()
    routes_count = len([r for r in app.routes if hasattr(r, "path")])
    print_startup_banner(
        project_name=settings.PROJECT_NAME,
        host="127.0.0.1",
        port=8000,
        db_connected=is_connected,
        db_name="Deluzex",
        db_ping_ms=ping_ms,
        routes_count=routes_count
    )
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

# Set up CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:8000",
        "http://localhost:8080",
        "http://34.14.217.7:3001",
        "*"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request Logging Middleware with Latency & User Tracking
@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    start_time = time.perf_counter()
    
    user_info = None
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        try:
            from jose import jwt
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            sub = payload.get("sub")
            if sub:
                is_admin = payload.get("is_admin", False)
                user_info = f"admin:{sub}" if is_admin else f"user:{sub}"
        except Exception:
            pass
            
    client_ip = request.client.host if request.client else "-"
    
    try:
        response: Response = await call_next(request)
        duration_ms = (time.perf_counter() - start_time) * 1000.0
        response.headers["X-Request-ID"] = request_id
        
        path = request.url.path
        if request.url.query:
            path = f"{path}?{request.url.query}"
            
        log_request(
            method=request.method,
            path=path,
            status_code=response.status_code,
            duration_ms=duration_ms,
            client_ip=client_ip,
            request_id=request_id,
            user_info=user_info
        )
        return response
    except Exception as exc:
        duration_ms = (time.perf_counter() - start_time) * 1000.0
        app_logger.error(f"Unhandled Exception on {request.method} {request.url.path}: {exc}", exc_info=True)
        log_request(
            method=request.method,
            path=request.url.path,
            status_code=500,
            duration_ms=duration_ms,
            client_ip=client_ip,
            request_id=request_id,
            user_info=user_info
        )
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error", "request_id": request_id}
        )

app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
def root():
    return {"message": "Welcome to deluzex-backend"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, access_log=False)