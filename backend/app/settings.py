from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    aws_region: str
    customer_user_pool_id: str
    staff_user_pool_id: str
    system_admin_user_pool_id: str

    model_config = SettingsConfigDict(extra="ignore")
