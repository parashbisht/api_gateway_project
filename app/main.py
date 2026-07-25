from fastapi import FastAPI
from app.db.base import Base
from app.db.session import engine
from app.api.v1 import auth

Base.metadata.create_all(bind=engine)

app = FastAPI(title="API Gateway")
app.include_router(auth.router)