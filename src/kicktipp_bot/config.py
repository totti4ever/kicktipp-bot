"""Configuration module for Kicktipp Bot."""

import os
from datetime import timedelta
from typing import Optional


class Config:
    """Configuration class containing all environment variables and constants."""

    # Base URLs
    BASE_URL = "https://www.kicktipp.de/"
    LOGIN_URL = "https://www.kicktipp.de/info/profil/login/"

    # Required environment variables
    EMAIL: Optional[str] = os.getenv("KICKTIPP_EMAIL")
    PASSWORD: Optional[str] = os.getenv("KICKTIPP_PASSWORD")
    NAME_OF_COMPETITION: Optional[str] = os.getenv(
        "KICKTIPP_NAME_OF_COMPETITION")

    # Optional environment variables with defaults
    RUN_EVERY_X_MINUTES: Optional[int] = int(
        os.getenv("KICKTIPP_RUN_EVERY_X_MINUTES", "60"))

    # Chrome driver path
    CHROMEDRIVER_PATH: Optional[str] = os.getenv("CHROMEDRIVER_PATH")

    # Time configuration
    HOURS_UNTIL_GAME: Optional[int] = int(
        os.getenv("KICKTIPP_HOURS_UNTIL_GAME", "2"))
    TIME_UNTIL_GAME: timedelta = timedelta(hours=HOURS_UNTIL_GAME)

    # Notification URLs
    ZAPIER_URL: Optional[str] = os.getenv("ZAPIER_URL")
    NTFY_URL: Optional[str] = os.getenv("NTFY_URL")
    NTFY_USERNAME: Optional[str] = os.getenv("NTFY_USERNAME")
    NTFY_PASSWORD: Optional[str] = os.getenv("NTFY_PASSWORD")
    WEBHOOK_URL: Optional[str] = os.getenv("WEBHOOK_URL")

    # Odds provider ("kicktipp.de" (default) or "the-odds-api.com")
    ODDS_PROVIDER: str = os.getenv("ODDS_PROVIDER", "kicktipp.de")
    # API Key für the-odds-api.com (Pflicht, wenn ODDS_PROVIDER='the-odds-api.com')
    THE_ODDS_API_KEY: Optional[str] = os.getenv("THE_ODDS_API_KEY")
    # Validierung für Odds-API-Key
    if ODDS_PROVIDER == "the-odds-api.com" and not THE_ODDS_API_KEY:
        raise ValueError("THE_ODDS_API_KEY muss gesetzt sein, wenn ODDS_PROVIDER='the-odds-api.com'!")

    @classmethod
    def validate_required_config(cls) -> bool:
        """Validate that all required configuration is present."""
        required_vars = [cls.EMAIL, cls.PASSWORD, cls.NAME_OF_COMPETITION]
        return all(var is not None for var in required_vars)

    @classmethod
    def get_tipp_url(cls) -> str:
        """Get the URL for the tipping page."""
        return f"https://www.kicktipp.de/{cls.NAME_OF_COMPETITION}/tippabgabe"
