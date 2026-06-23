from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://postgres:postgres@db:5432/darkatlas_ai"
    anthropic_api_key: str = ""
    postgres_db: str = "darkatlas_ai"
    postgres_user: str = "postgres"
    postgres_password: str = "postgres"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
