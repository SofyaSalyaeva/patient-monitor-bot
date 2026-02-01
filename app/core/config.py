from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    BOT_TOKEN: str

    YANDEX_CLOUD_FOLDER: str
    YANDEX_CLOUD_API_KEY: str

    DB_PATH: str = "data.db"

    SUMMARY_DAYS: int = 30
    NLU_CACHE_TTL: int = 30

    model_config = {"env_file": ".env", "extra": "ignore"}

    @property
    def db_url(self) -> str:
        return f"sqlite+aiosqlite:///{self.DB_PATH}"


settings = Settings()
