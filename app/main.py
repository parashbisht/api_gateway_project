from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db.base import Base
from app.db.session import engine
from app.api.v1 import auth, api_keys, gateway, analytics, gateway_routes, plans
from app.models import request_log, product, order
from app.middleware.logging_middleware import log_requests_middleware
from app.middleware.security_headers import SecurityHeadersMiddleware

Base.metadata.create_all(bind=engine)

app = FastAPI(title="API Gateway")

app.include_router(auth.router)
app.include_router(api_keys.router)
app.include_router(gateway.router)
app.include_router(analytics.router)
app.include_router(gateway_routes.router)
app.include_router(plans.router)

app.middleware("http")(log_requests_middleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)