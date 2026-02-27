from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # App
    app_name: str = "Label Stream API"
    debug: bool = True

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@db:5432/labelstream"
    database_url_sync: str = "postgresql://postgres:postgres@db:5432/labelstream"

    # Auth
    jwt_secret: str = "dev-secret-change-in-prod"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7  # 1 week

    # R2 / S3
    r2_endpoint: str = ""
    r2_access_key: str = ""
    r2_secret_key: str = ""
    r2_bucket: str = "labelstream-audio"
    presigned_url_expiry: int = 3600  # 1 hour

    model_config = {"env_file": ".env"}


settings = Settings()
