from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from pydantic_settings import BaseSettings, SettingsConfigDict # Обновили импорт

class Secrets(BaseSettings):
    token: str
    admin_id: int
    groq_api_key: str
    delay: int

    # Новый синтаксис для Pydantic V2 (убирает предупреждение)
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

secrets = Secrets()

bot = Bot(
    token=secrets.token,
    default=DefaultBotProperties(parse_mode="Markdown")
)