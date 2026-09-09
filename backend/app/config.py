from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    database_url: str = 'postgresql+psycopg2://peblo:peblo@localhost:5432/peblo'
    jwt_secret: str = 'dev-secret'
    storage_root: str = './storage'
    cors_origins: str = 'http://localhost:5173,http://localhost:5174'
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')

    @property
    def cors_list(self): return [x.strip() for x in self.cors_origins.split(',') if x.strip()]

settings = Settings()
