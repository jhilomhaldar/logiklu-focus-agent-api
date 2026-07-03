from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "LogiKlu Focus Agent API"
    APP_ENV: str = "local"
    APP_DEBUG: bool = True
    API_VERSION: str = "v1"
    API_ENV: str = "production"

    MASTER_DB_HOST: str = "localhost"
    MASTER_DB_PORT: int = 3306
    MASTER_DB_NAME: str = "logiklu0_leadactuator"
    MASTER_DB_USER: str = "logiklu0_global"
    MASTER_DB_PASSWORD: str = "e[[U6Js,MP%O"

    API_AUTH_ENABLED: bool = True
    API_SIGNATURE_REQUIRED: bool = False

    ALLOWED_ORIGINS: str = "*"

    JWT_SECRET_KEY: str = ""
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_SECONDS: int = 900
    JWT_ISSUER: str = "logiklu-focus-api"
    JWT_AUDIENCE: str = "cognitive-ai"

    MASTER_USAGE_USERNAME: str = "logikluadmin"
    MASTER_USAGE_PASSWORD: str = ""

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"


settings = Settings()