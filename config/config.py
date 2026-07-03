from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "sqlite:///./jobsearcher.db"
    
    # JWT
    SECRET_KEY: str = "your-secret-key-change-this"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Mistral AI
    MISTRAL_API_KEY: Optional[str] = None
    
    # Google OAuth
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    
    # ✅ Email Settings (NEW)
    EMAIL_FROM: str = ""
    SMTP_HOST: str = ""
    SMTP_USER: str = ""
    SMTP_PASS: str = ""
    SMTP_PORT: int = 587
    
    # ✅ Frontend (NEW)
    FRONTEND_URL: str = "http://localhost:3000"
    
    # ✅ Token expiration (NEW)
    RESET_TOKEN_EXPIRE_HOURS: int = 1
    
    # Environment
    ENV: str = "development"
    LOG_LEVEL: str = "INFO"
    
    class Config:
        env_file = ".env"


settings = Settings()