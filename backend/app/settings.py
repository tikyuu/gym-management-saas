from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    aws_region: str
    customer_user_pool_id: str
    staff_user_pool_id: str
    system_admin_user_pool_id: str

    model_config = SettingsConfigDict(extra="ignore")


class DatabaseSettings(BaseSettings):
    db_host: str
    db_port: int = 5432
    db_name: str
    db_username: str
    db_password: SecretStr
    db_ssl_root_cert: str

    model_config = SettingsConfigDict(extra="ignore")
