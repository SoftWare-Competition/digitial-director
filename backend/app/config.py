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
    alibaba_asr_appkey: str = ""
    

    seniverse_api_key: str = ""

    # SMTP email configuration
    smtp_host: str = "smtp.qq.com"
    smtp_port: int = 587
    smtp_username: str = "2149561658@qq.com"
    smtp_password: str = "xseggviroxfkecgj"
    smtp_from_name: str = "灵山AI导游"

    # Baidu Maps (在 .env 中配置 BAIDU_MAP_AK=xxx)
    baidu_map_ak: str = ""

    audio_base_url: str = "http://localhost:8000/static/audio"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
