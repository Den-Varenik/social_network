from pydantic import BaseSettings


class Settings(BaseSettings):
    debug: bool = False
    secret_key: str = "my-secret-key"
    main_database_url: str = "sqlite+aiosqlite:///db.sqlite3"
    test_database_url: str = "sqlite+aiosqlite:///test.sqlite3"

    api_prefix: str = "/api/v1"

    project_name: str = "Social Network"
    version: str = "0.1.0"
    description: str = "My test FastAPI project."

    docs_url: str = "/docs"
    redoc_url: str = "/redoc"
    openapi_url: str = "/openapi.json"

    class Config:
        env_file = ".env"


settings = Settings()
