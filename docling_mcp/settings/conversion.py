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
    force_full_page_ocr: bool = True  # Force OCR on entire page, not just detected bitmap areas
    keep_images: bool = False
    num_threads: int = 30  # Number of CPU threads for parallel processing
    ocr_confidence_threshold: float = 0.5  # OCR confidence threshold (0.0-1.0)
    default_output_directory: str = "C:\\Users\\Iljaas\\Downloads\\"


settings = Settings()
