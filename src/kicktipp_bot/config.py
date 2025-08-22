"""Configuration module for Kicktipp Bot."""

import os
from datetime import timedelta
from typing import Optional


class Config:
    # Wenn true, werden used_odds geschrieben und Datei ggf. neu angelegt
    USED_ODDS_WRITE: bool = os.getenv("USED_ODDS_WRITE", "false").lower() == "true"
    # Wenn true, wird immer die vorhandene odds_cache.json verwendet (egal wie alt)
    ODDS_CACHE_ALWAYS_USE_FILE: bool = os.getenv("ODDS_CACHE_ALWAYS_USE_FILE", "false").lower() == "true"
    # Tipps überschreiben erlauben
    OVERWRITE_TIPS: bool = os.getenv("OVERWRITE_TIPS", "false").lower() == "true"
    # Odds-Strategie: 'classic' (nur H2H) oder 'smart' (H2H+Spread+Totals)
    ODDS_STRATEGY: str = os.getenv("ODDS_STRATEGY", "classic")
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

    # Odds API Konfiguration
    USE_ODDS_API: bool = os.getenv("USE_ODDS_API", "false").lower() == "true"
    ODDS_API_KEY: str = os.getenv("ODDS_API_KEY", "")

    @classmethod
    def validate_required_config(cls) -> bool:
        """Validate that all required configuration is present."""
        required_vars = [cls.EMAIL, cls.PASSWORD, cls.NAME_OF_COMPETITION]
        return all(var is not None for var in required_vars)

    @classmethod
    def get_tipp_url(cls) -> str:
        """Get the URL for the tipping page."""
        return f"https://www.kicktipp.de/{cls.NAME_OF_COMPETITION}/tippabgabe"
