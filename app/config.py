from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    PSEUDOGRAM_API_KEY: str = "mock_api_key_test"
    PSEUDOGRAM_BASE_URL: str = "https://pseudogram-api.onrender.com"
    MONGODB_URI: str = "mongodb://localhost:27017"
    DATABASE_NAME: str = "linkplease"
    MAX_RETRIES: int = 5
    WEBHOOK_SIGNATURE_REQUIRED: bool = True
    RATE_LIMIT_REQUESTS: int = 10
    RATE_LIMIT_WINDOW_SECONDS: int = 60
    WORKER_POLL_INTERVAL: float = 0.5



settings = Settings()
