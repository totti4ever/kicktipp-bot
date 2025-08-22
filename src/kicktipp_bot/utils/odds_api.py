KICKTIPP_TO_API = {
    "FC Bayern München": "Bayern Munich",
    "RB Leipzig": "RB Leipzig",
    "1. FC Heidenheim 1846": "1. FC Heidenheim",
    "VfL Wolfsburg": "VfL Wolfsburg",
    "SC Freiburg": "SC Freiburg",
    "FC Augsburg": "Augsburg",
    "Bayer 04 Leverkusen": "Bayer Leverkusen",
    "1899 Hoffenheim": "TSG Hoffenheim",
    "Eintracht Frankfurt": "Eintracht Frankfurt",
    "Werder Bremen": "Werder Bremen",
    "1. FC Union Berlin": "Union Berlin",
    "VfB Stuttgart": "VfB Stuttgart",
    "FC St. Pauli": "FC St. Pauli",
    "Borussia Dortmund": "Borussia Dortmund",
    "FSV Mainz 05": "FSV Mainz 05",
    "1. FC Köln": "1. FC Köln",
    "Bor. Mönchengladbach": "Borussia Monchengladbach",
    "Hamburger SV": "Hamburger SV"
}
import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import requests

logger = logging.getLogger(__name__)

ODDS_API_URL = "https://api.the-odds-api.com/v4/sports/soccer_germany_bundesliga/odds?regions=eu&markets=h2h,totals,spreads&api_key={api_key}&ODDS_FORMAT=decimal&DATE_FORMAT=iso"
CACHE_FILE = os.path.join(os.path.dirname(__file__), '../../data/odds_cache.json')
CACHE_TTL = timedelta(hours=6)  # Cache für 6 Stunden gültig

class OddsApiClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.cache: Optional[Dict[str, Any]] = None
        self.cache_time: Optional[datetime] = None
        self._load_cache()

    def _load_cache(self):
        if os.path.exists(CACHE_FILE):
            try:
                with open(CACHE_FILE, 'r') as f:
                    data = json.load(f)
                    self.cache = data.get('odds')
                    self.cache_time = datetime.fromisoformat(data.get('cache_time'))
                    logger.info(f"Loaded odds cache from file: {CACHE_FILE}")
            except Exception as e:
                logger.warning(f"Could not load odds cache: {e}")
        else:
            logger.info(f"No odds cache file found at {CACHE_FILE}")

    def _save_cache(self):
        try:
            os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
            with open(CACHE_FILE, 'w') as f:
                json.dump({
                    'odds': self.cache,
                    'cache_time': self.cache_time.isoformat() if self.cache_time else None
                }, f)
            logger.info(f"Saved odds cache to file: {CACHE_FILE}")
        except Exception as e:
            logger.warning(f"Could not save odds cache: {e}")

    def _is_cache_valid(self) -> bool:
        from kicktipp_bot.config import Config
        # Wenn ODDS_CACHE_ALWAYS_USE_FILE true ist, ist die Datei immer "gültig"
        if Config.ODDS_CACHE_ALWAYS_USE_FILE:
            return self.cache is not None
        valid = self.cache is not None and self.cache_time and (datetime.now() - self.cache_time) < CACHE_TTL
        return valid

    def fetch_odds(self, force_refresh: bool = False) -> Optional[Dict[str, Any]]:
        from kicktipp_bot.config import Config
        if Config.ODDS_CACHE_ALWAYS_USE_FILE:
            if self.cache is not None:
                logger.info(f"ODDS_CACHE_ALWAYS_USE_FILE=True: Using cached odds data from {CACHE_FILE} (no refresh).")
                return self.cache
            # Wenn keine Datei existiert, wird wie bisher geladen und gespeichert
        if not force_refresh and self._is_cache_valid():
            logger.info(f"Odds cache valid: True (file: {CACHE_FILE})")
            logger.info(f"Using cached odds data from {CACHE_FILE}.")
            return self.cache
        url = ODDS_API_URL.format(api_key=self.api_key)
        logger.info("Fetching new odds data from API...")
        try:
            response = requests.get(url)
            response.raise_for_status()
            self.cache = response.json()
            self.cache_time = datetime.now()
            self._save_cache()
            logger.info("Fetched new odds data from API.")
            return self.cache
        except Exception as e:
            logger.error(f"Error fetching odds from API: {e}")
            return self.cache  # fallback to possibly stale cache

    def get_odds_for_match(self, home_team: str, away_team: str, match_time: datetime) -> Optional[Dict[str, Any]]:
        odds_data = self.fetch_odds()
        if not odds_data:
            return None
        # Mapping anwenden
        api_home = KICKTIPP_TO_API.get(home_team, home_team)
        api_away = KICKTIPP_TO_API.get(away_team, away_team)
        from datetime import timezone
        for event in odds_data:
            try:
                if (event['home_team'].lower() == api_home.lower() and
                    event['away_team'].lower() == api_away.lower()):
                    # Optional: Zeitfenster prüfen
                    event_time = datetime.fromisoformat(event['commence_time'].replace('Z', '+00:00'))
                    if match_time.tzinfo is None:
                        match_time_aware = match_time.replace(tzinfo=timezone.utc)
                    else:
                        match_time_aware = match_time.astimezone(timezone.utc)
                    if abs((event_time - match_time_aware).total_seconds()) < 6*3600:  # 6h Toleranz
                        return event
            except Exception as e:
                logger.warning(f"Error matching event: {e}")
        return None

    def get_h2h_quotes(self, event: Dict[str, Any]) -> Optional[Dict[str, float]]:
        for bookmaker in event.get('bookmakers', []):
            for market in bookmaker.get('markets', []):
                if market['key'] == 'h2h':
                    outcomes = market.get('outcomes', [])
                    return {o['name']: o['price'] for o in outcomes}
        return None

    def get_spreads(self, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        for bookmaker in event.get('bookmakers', []):
            for market in bookmaker.get('markets', []):
                if market['key'] == 'spreads':
                    return market.get('outcomes', [])
        return None

    def get_totals(self, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        for bookmaker in event.get('bookmakers', []):
            for market in bookmaker.get('markets', []):
                if market['key'] == 'totals':
                    return market.get('outcomes', [])
        return None
