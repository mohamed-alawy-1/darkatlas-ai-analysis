from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://postgres:postgres@db:5432/darkatlas_ai"
    anthropic_api_key: str = ""

    model_config = {"env_file": ".env"}


settings = Settings()
