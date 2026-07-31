from fastapi import FastAPI
from app.db.base import Base
from app.db.session import engine
from app.api.v1 import auth
from app.api.v1 import api_keys
from app.api.v1 import gateway
from app.middleware.logging_middleware import log_requests_middleware
from app.api.v1 import analytics
from app.api.v1 import gateway_routes
from app.models import product, order  



Base.metadata.create_all(bind=engine)
from app.models import request_log  

app = FastAPI(title="API Gateway")
app.include_router(auth.router)
app.include_router(api_keys.router)
app.include_router(gateway.router)
app.middleware("http")(log_requests_middleware)
app.include_router(analytics.router)
app.include_router(gateway_routes.router)