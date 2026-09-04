from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')
    rally_base_url: str = 'https://rally1.rallydev.com'
    rally_auth_mode: str = 'browser_snapshot'
    rally_snapshot_file: str = 'data/rally_snapshot.json'
    rally_api_key: str = ''
    rally_workspace_oid: str = ''
    rally_project_oid: str = ''
    rally_squad_field: str = 'Project'
    rally_squad_value: str = ''
    rally_quarter_field: str = 'c_Quarter'
    gitlab_base_url: str = 'https://gitlab.com'
    gitlab_token: str = ''
    gitlab_project_id: str = ''
    gitlab_project_path: str = ''
    database_url: str = 'sqlite:///./bridge.db'
    sync_secret: str = 'change-me'
    config_file: str = 'config.yaml'

@lru_cache
def get_settings() -> Settings:
    return Settings()
