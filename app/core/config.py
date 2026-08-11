from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(case_sensitive=True, env_file=".env", extra="ignore")

    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "deluzex-backend"
    RAZORPAY_KEY_ID: str = "rzp_test_TMTdBccApgaZzL"
    RAZORPAY_KEY_SECRET: str = "sEB6k9oHAtCsE8nd9sB6tBoY"

settings = Settings()
