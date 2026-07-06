from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = True
    secret_key: str = "dev-secret-key-change-in-production"

    database_url: str = "sqlite:///./lingshan.db"

    wechat_appid: str = ""
    wechat_secret: str = ""

    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"

    alibaba_access_key_id: str = ""
    alibaba_access_key_secret: str = ""
    alibaba_tts_voice: str = "aixia"
    alibaba_asr_model: str = "paraformer-v1"

    hefeng_api_key: str = ""

    audio_base_url: str = "http://localhost:8000/static/audio"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
