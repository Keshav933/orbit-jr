from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "ORBIT-JR"
    app_env: str = "development"
    app_debug: bool = True
    api_prefix: str = "/api/v1"
    db_host: str = "127.0.0.1"
    db_port: int = 3306
    db_name: str = "orbit_jr"
    db_user: str = "orbit_user"
    db_password: str = "change_me"
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen3:4b"
    jobicy_enabled: bool = False
    cors_origins: str = "http://localhost:5173"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
