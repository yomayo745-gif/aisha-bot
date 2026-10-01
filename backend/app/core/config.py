from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    BOT_TOKEN: str = "8973551990:AAFQgayifyPx7RSQhnnOXjBkWDb-t8gADk8"
    DATABASE_URL: str = "sqlite+aiosqlite:///./aisha_mebel.db"
    REDIS_URL: str = "redis://localhost:6379/0"
    
    ADMIN_INITIAL_USERNAME: str = "Muhammad"
    ADMIN_INITIAL_PASSWORD: str = "dummy_password"
    
    SECRET_KEY: str = "dummy_secret"
    JWT_SECRET: str = "dummy_jwt_secret"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7 # 7 days
    
    # Comma-separated admin telegram IDs
    ADMIN_TELEGRAM_IDS: str = "298881982,6896779142,8032934304"
    
    OBJECT_STORAGE_ENDPOINT: Optional[str] = None
    OBJECT_STORAGE_BUCKET: Optional[str] = None
    OBJECT_STORAGE_ACCESS_KEY: Optional[str] = None
    OBJECT_STORAGE_SECRET_KEY: Optional[str] = None
    
    COMPANY_TELEGRAM: str = "@zjxkdjbd"
    COMPANY_PHONE_1: str = "880606040"
    COMPANY_PHONE_2: str = "934124604"
    
    PUBLIC_URL: str = "https://aisha-mebel-production.up.railway.app"
    APP_URL: Optional[str] = "https://admin.aisha-mebel.uz"
    WEB_APP_URL: Optional[str] = "https://frontend-production-7834.up.railway.app"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
