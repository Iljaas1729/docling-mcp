"""This module contains the settings for conversion tools."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Settings for the conversion tools."""

    model_config = SettingsConfigDict(
        env_prefix="DOCLING_MCP_",
        env_file=".env",
        # extra="allow",
    )
    do_ocr: bool = True
    keep_images: bool = False
    default_output_directory: str = "C:\\Users\\Iljaas\\Downloads\\"


settings = Settings()
