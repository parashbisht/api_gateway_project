from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/api_gateway"
    REDIS_URL: str = "redis://localhost:6379/0"

    SECRET_KEY: str = "change-this-in-.env"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    ENVIRONMENT: str = "development"  # development | production

    # Rate limiting — previously hardcoded, now configurable
    RATE_LIMIT_WINDOW_SECONDS: int = 3600
    LOGIN_RATE_LIMIT_MAX_ATTEMPTS: int = 10
    LOGIN_RATE_LIMIT_WINDOW_SECONDS: int = 300

    # Downstream call timeout (see item 8 for context)
    DOWNSTREAM_TIMEOUT_SECONDS: float = 5.0

    class Config:
        env_file = ".env"

settings = Settings()