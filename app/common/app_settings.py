from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    DB_CONNECTION_STRING: str = Field(alias="DB_CONNECTION_STRING", min_length=1)

    model_config = SettingsConfigDict(env_file=".env")


try:
    settings = AppSettings()  # type: ignore
except Exception as e:
    print("Error loading settings:", e)
