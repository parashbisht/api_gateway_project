from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/api_gateway"
    REDIS_URL: str = "redis://localhost:6379/0"

    SECRET_KEY: str = "change-this-in-.env"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    CORS_ALLOWED_ORIGINS: str = "http://localhost:3000"

    GEMINI_API_KEY: str = ""
    TAVILY_API_KEY: str = ""

    @property
    def cors_origins_list(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.CORS_ALLOWED_ORIGINS.split(",")
            if origin.strip()
        ]

    ENVIRONMENT: str = "development"

    RATE_LIMIT_WINDOW_SECONDS: int = 3600
    LOGIN_RATE_LIMIT_MAX_ATTEMPTS: int = 10
    LOGIN_RATE_LIMIT_WINDOW_SECONDS: int = 300

    DOWNSTREAM_TIMEOUT_SECONDS: float = 5.0

    class Config:
        env_file = ".env"


settings = Settings()