from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "Smart Building — Combined API"
    APP_VERSION: str = "1.0.0"
    APP_TZ: str = "Asia/Jakarta"

    # DB
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "smartbuilding"
    DB_USER: str = "postgres"
    DB_PASS: str = "1234"

    # Business constants
    TARIFF_IDR_PER_KWH: float = 1114.74
    FLOOR_AREA_M2: float = 1500.0

    # Realtime feature constants (kept as original defaults)
    ENABLE_SCHEDULER: bool = True
    SETPOINT_C: float = 24.5
    BASE_LOAD_NIGHT: float = 0.25
    BASE_LOAD_DAY: float = 0.35
    AC_COEFF: float = 0.28

    class Config:
        env_file = ".env"


settings = Settings()
