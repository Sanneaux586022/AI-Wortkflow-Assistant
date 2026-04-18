import os
from datetime import timedelta

from dotenv import load_dotenv

load_dotenv()


# BASE_DIR = os.path.abspath(os.path.dirname(__file__))
# SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(BASE_DIR, "app.db")
class Config:
    # Ambiente
    FLASK_ENV = os.getenv("FLASK_ENV", "production")

    # API Keys
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL")

    # Database
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "SQLALCHEMY_DATABASE_URI", "sqlite:///custumer_requests.db"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Flask Smorest / OpenAPI
    API_TITLE = "AI Workflow Assistant"
    API_VERSION = "v1"
    OPENAPI_VERSION = "3.0.3"
    OPENAPI_URL_PREFIX = "/docs" if os.getenv("FLASK_ENV") == "development" else None
    OPENAPI_SWAGGER_UI_PATH = "/swagger-ui"
    OPENAPI_SWAGGER_UI_URL = "https://cdn.jsdelivr.net/npm/swagger-ui-dist/"

    JWT_SECRET_KEY = os.getenv("PRIVATE_APP_KEY")
    JWT_ACCESS_TOKEN_EXPIRE = timedelta(minutes=30)
    JWT_REFRESH_TOKEN_EXPIRE = timedelta(days=7)
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
    MAILGUN_API_KEY = os.getenv("MAILGUN_API_KEY")
    MAILGUN_DOMAIN_NAME = os.getenv("MAILGUN_DOMAIN_NAME")
    # config.py
    ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")

    CRON_SECRET = os.getenv("CRON_SECRET_KEY")