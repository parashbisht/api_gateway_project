from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db.base import Base
from app.db.session import engine
from app.api.v1 import auth, api_keys, gateway, analytics, gateway_routes, plans
from app.models import request_log, product, order
from app.middleware.logging_middleware import log_requests_middleware
from app.middleware.security_headers import SecurityHeadersMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.exceptions import RequestValidationError
from app.core.exceptions import (
    http_exception_handler,
    validation_exception_handler,
    unhandled_exception_handler,
)
from app.api.v1 import health


Base.metadata.create_all(bind=engine)

app = FastAPI(title="API Gateway")

@app.get("/")
def root():
    return {
        "message": "API Gateway is running",
        "docs": "/docs",
        "health": "/health",
    }

app.include_router(auth.router)
app.include_router(api_keys.router)
app.include_router(gateway.router)
app.include_router(analytics.router)
app.include_router(gateway_routes.router)
app.include_router(plans.router)
app.include_router(health.router)

app.middleware("http")(log_requests_middleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)