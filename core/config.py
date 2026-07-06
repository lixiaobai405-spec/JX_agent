from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    APP_NAME: str = "jx-backend"
    DEBUG: bool = False

    DATABASE_URL: str
    SECRET_KEY: str = "change-this-secret-key-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    BCRYPT_COST: int = 12
    MAX_SESSIONS: int = 5
    PASSWORD_RESET_TOKEN_EXPIRE_HOURS: int = 1

    JXHOST: str = "0.0.0.0"
    JXPORT: int = 8000

@lru_cache
def get_settings() -> Settings:
    return Settings()