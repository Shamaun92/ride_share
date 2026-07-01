"""Application configuration loaded from environment variables.

Uses pydantic-settings so every setting is typed, validated at startup, and
overridable via environment / .env. Fail-fast: a misconfigured deployment
crashes on boot instead of at first request.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, PostgresDsn, RedisDsn, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ---- App ----
    PROJECT_NAME: str = "RideShare API"
    API_V1_PREFIX: str = "/api/v1"
    ENVIRONMENT: Literal["local", "staging", "production"] = "local"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # ---- Security / JWT ----
    SECRET_KEY: str = Field(..., min_length=32)
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ---- Database ----
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "rideshare"
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10
    DB_ECHO: bool = False

    # ---- Redis ----
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str | None = None

    # ---- Ride dispatch ----
    RIDE_SEARCH_RADIUS_KM: float = 5.0
    RIDE_MAX_OFFERS: int = 10
    RIDE_OFFER_TTL_SECONDS: int = 120

    # ---- Fare engine (amounts in poisha; 1 BDT = 100 poisha) ----
    FARE_BASE_POISHA: int = 5000           # flat pickup fee (50 BDT)
    FARE_PER_KM_POISHA: int = 3000         # 30 BDT/km
    FARE_PER_MIN_POISHA: int = 200         # 2 BDT/min
    FARE_BOOKING_FEE_POISHA: int = 1000    # 10 BDT booking fee
    FARE_MIN_POISHA: int = 6000            # minimum total (60 BDT)
    FARE_AVG_SPEED_KMH: float = 20.0       # for duration estimate at request time
    PLATFORM_COMMISSION_BPS: int = 2000    # 20.00% in basis points
    CANCELLATION_FEE_POISHA: int = 3000    # 30 BDT late-cancel fee

    # ---- Surge ----
    SURGE_ENABLED: bool = True
    SURGE_MAX_BPS: int = 30000             # cap at 3.0x
    SURGE_DEMAND_RADIUS_KM: float = 3.0

    # ---- Pooling ----
    POOL_DISCOUNT_BPS: int = 2500          # 25% off for shared rides
    POOL_MATCH_RADIUS_KM: float = 1.5
    POOL_DEFAULT_CAPACITY: int = 2

    # ---- Admin ----
    ADMIN_BOOTSTRAP_SECRET: str | None = None

    # ---- Hardening ----
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_DEFAULT_PER_MIN: int = 60   # per-user, sensitive mutations
    RATE_LIMIT_AUTH_PER_MIN: int = 20      # per-IP, auth endpoints
    IDEMPOTENCY_TTL_SECONDS: int = 86400   # replay window for Idempotency-Key
    SECURITY_HEADERS_ENABLED: bool = True

    # ---- CORS ----
    BACKEND_CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        return str(
            PostgresDsn.build(
                scheme="postgresql+asyncpg",
                username=self.POSTGRES_USER,
                password=self.POSTGRES_PASSWORD,
                host=self.POSTGRES_HOST,
                port=self.POSTGRES_PORT,
                path=self.POSTGRES_DB,
            )
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def REDIS_URI(self) -> str:
        auth = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
        return f"redis://{auth}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


settings = get_settings()
