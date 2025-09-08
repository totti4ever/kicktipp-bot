import datetime
import logging
import os
import json
import requests
from typing import Optional, Any

from kicktipp_bot.models.quote_dto import QuoteDTO
from ..config import Config

logger = logging.getLogger(__name__)


class QuoteExtractorOddsApi: # Kicktipp : OddsAPI
    ODDS_API_URL = "https://api.the-odds-api.com/v4/sports/soccer_germany_bundesliga/odds?regions=eu&markets=h2h,totals,spreads&api_key={api_key}&ODDS_FORMAT=decimal&DATE_FORMAT=iso"

    KICKTIPP_TO_ODDSAPI = {
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
    ODDSAPI_TO_KICKTIPP = {v: k for k, v in KICKTIPP_TO_ODDSAPI.items()}

    odds: dict = {}

    @classmethod
    def _map_teamname_KicktippToOddsapi(cls, kicktipp_name: str) -> str:
        oddsapi_name = cls.KICKTIPP_TO_ODDSAPI.get(kicktipp_name)
        # logger.debug(f"Mapping Kicktipp team name to OddsAPI: {kicktipp_name} --> {oddsapi_name}")
        return oddsapi_name  # KeyError, wenn nicht vorhanden

    @classmethod
    def _map_teamname_OddsapiToKicktipp(cls, oddsapi_name: str) -> str:
        kicktipp_name = cls.ODDSAPI_TO_KICKTIPP.get(oddsapi_name)
        # logger.debug(f"Mapping OddsAPI team name to Kicktipp: {oddsapi_name} --> {kicktipp_name}")
        return kicktipp_name  # KeyError, wenn nicht vorhanden

    @classmethod
    def _parse_odds_cache(cls, odds_cache: Any) -> dict:
        """
        Parse the odds cache into a dict for quick lookup by (home_team, away_team, commence_time).
        Key: (home_team.lower(), away_team.lower(), commence_time as iso str)
        Value: odds dict for that game
        """
        if not odds_cache:
            return {}
        parsed = {}
        for game in odds_cache:
            commence_time_str = game.get('commence_time', '')
            try:
                commence_time_dt = datetime.datetime.strptime(commence_time_str, '%Y-%m-%dT%H:%M:%SZ')
            except ValueError:
                logger.warning(f"Could not parse commence_time: {commence_time_str}")
                commence_time_dt = None

            key = (
                cls._map_teamname_OddsapiToKicktipp(game.get('home_team')),
                cls._map_teamname_OddsapiToKicktipp(game.get('away_team')),
                commence_time_dt
            )
            parsed[key] = game
        return parsed

    @classmethod
    def _fetch_odds_from_file(cls) -> Any:
        cache_path = Config.ODDS_CACHE_PERSIST_TO
        if not os.path.isabs(cache_path):
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            cache_path = os.path.join(project_root, cache_path)
        if os.path.isfile(cache_path):
            cls._cache_path = cache_path
            try:
                with open(cache_path, 'r', encoding='utf-8') as f:
                    logger.info(f"Loading odds from cache file: {cache_path}")
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load odds cache: {e}")
        else:
            logger.debug(f"No odds cache file not found, fetching live from API")
            return None

    @classmethod
    def _persist_odds_cache_to_file(cls, odds: Any) -> None:
        cache_path = Config.ODDS_CACHE_PERSIST_TO
        if not os.path.isabs(cache_path):
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            cache_path = os.path.join(project_root, cache_path)
        if cache_path:
            try:
                with open(cache_path, 'w', encoding='utf-8') as f:
                    json.dump(odds, f, ensure_ascii=False, indent=2)
                logger.info(f"Odds persisted to cache file: {cache_path}")
            except Exception as e:
                logger.warning(f"Failed to persist odds cache: {e}")
        else:
            logger.warning("No cache path configured, skipping cache persistence.") 

    @classmethod
    def _fetch_odds_from_api(cls) -> Any:
        url = cls.ODDS_API_URL.format(api_key=Config.THE_ODDS_API_KEY)
        logger.info("Fetching new odds data from API...")
        try:
            response = requests.get(url)
            response.raise_for_status()
            logger.info("Fetched new odds data from API.")
            if Config.ODDS_CACHE_PERSIST_TO:
                cls._persist_odds_cache_to_file(response.json())
            logger.info("Persisted new odds data to cache.")
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching odds from API: {e}")
            return cls._odds_cache  # fallback to possibly stale cache

    @classmethod
    def init(cls):
        # Get odds either from cache file (if exists) or from API
        cls._odds_raw = (Config.ODDS_CACHE_PERSIST_TO and cls._fetch_odds_from_file()) or cls._fetch_odds_from_api()
        # Parse raw odds to map by game
        cls.odds = cls._parse_odds_cache(cls._odds_raw)

    @classmethod
    def extract_quotes(cls, home_team: str, away_team: str, game_time: datetime) -> Optional[QuoteDTO]:
        if game_time.tzinfo is not None:
            game_time = game_time.astimezone(datetime.timezone.utc).replace(tzinfo=None)

        odds = cls.odds.get((
            home_team,
            away_team,
            game_time
        ))

        from kicktipp_bot.models.game_odds_dtos import GameOddsDTO, H2hDto, SpreadsDto, TotalsDto
        game_odds_dtos = []
        if odds:
            # odds['bookmakers'] is a list of bookmakers, each with a 'markets' list
            for bookmaker in odds.get('bookmakers', []):
                provider = bookmaker.get('title')
                h2h = None
                spread = None
                totals = None
                # market can be h2h, spreads, or totals
                h2h_home = h2h_away = None
                for market in bookmaker.get('markets', []):
                    # h2h
                    if market.get('key') == 'h2h':
                        outcomes = market.get('outcomes', [])
                        winHomeOdd = winAwayOdd = drawOdd = None
                        for outcome in outcomes:
                            outcome_name = outcome.get('name')
                            mapped_name = None
                            if outcome_name and outcome_name.lower() != 'draw':
                                try:
                                    mapped_name = cls._map_teamname_OddsapiToKicktipp(outcome_name)
                                except Exception:
                                    logger.error(f"Could not map team name from OddsAPI to Kicktipp: {outcome_name}")
                            if mapped_name == home_team:
                                winHomeOdd = outcome.get('price')
                            elif mapped_name == away_team:
                                winAwayOdd = outcome.get('price')
                            elif outcome_name and outcome_name.lower() == 'draw':
                                drawOdd = outcome.get('price')
                        if winHomeOdd is not None and winAwayOdd is not None and drawOdd is not None:
                            h2h = H2hDto(winHomeOdd, winAwayOdd, drawOdd)
                            h2h_home = winHomeOdd
                            h2h_away = winAwayOdd
                    # Spreads
                    elif market.get('key') == 'spreads':
                        outcomes = market.get('outcomes', [])
                        handycap = winFavouriteOdd = winUnderdogOdd = None
                        favourite_team = underdog_team = None
                        # Determine favourite/underdog based on h2h odds
                        if h2h_home is not None and h2h_away is not None:
                            if h2h_home < h2h_away:
                                favourite_team = home_team
                                underdog_team = away_team
                            else:
                                favourite_team = away_team
                                underdog_team = home_team
                        for outcome in outcomes:
                            if outcome.get('point') is not None:
                                handycap = outcome.get('point')
                            if cls._map_teamname_OddsapiToKicktipp(outcome.get('name')) == favourite_team:
                                winFavouriteOdd = outcome.get('price')
                            elif cls._map_teamname_OddsapiToKicktipp(outcome.get('name')) == underdog_team:
                                winUnderdogOdd = outcome.get('price')
                        if handycap is not None and winFavouriteOdd is not None and winUnderdogOdd is not None:
                            spread = SpreadsDto(handycap, winFavouriteOdd, winUnderdogOdd)
                    # Totals
                    elif market.get('key') == 'totals':
                        outcomes = market.get('outcomes', [])
                        total = overOdd = underOdd = None
                        for outcome in outcomes:
                            if outcome.get('point') is not None:
                                total = outcome.get('point')
                            if outcome.get('name').lower() == 'over':
                                overOdd = outcome.get('price')
                            elif outcome.get('name').lower() == 'under':
                                underOdd = outcome.get('price')
                        if total is not None and overOdd is not None and underOdd is not None:
                            totals = TotalsDto(total, overOdd, underOdd)
                game_odds_dtos.append(GameOddsDTO(h2h=h2h, spread=spread, totals=totals, provider=provider))
        # game_odds_dtos is now an array of all odds for the match

        # --- Aggregation logic for a single aggregated GameOddsDTO ---
        from collections import Counter
        agg_h2h = agg_spread = agg_totals = None

        # Aggregate H2H: average odds
        h2h_home_odds = [dto.h2h.winHomeOdd for dto in game_odds_dtos if dto.h2h]
        h2h_away_odds = [dto.h2h.winAwayOdd for dto in game_odds_dtos if dto.h2h]
        h2h_draw_odds = [dto.h2h.drawOdd for dto in game_odds_dtos if dto.h2h]
        if h2h_home_odds and h2h_away_odds and h2h_draw_odds:
            avg_home = sum(h2h_home_odds) / len(h2h_home_odds)
            avg_away = sum(h2h_away_odds) / len(h2h_away_odds)
            avg_draw = sum(h2h_draw_odds) / len(h2h_draw_odds)
            agg_h2h = H2hDto(avg_home, avg_away, avg_draw)

        # Aggregate Spreads: most common handycap, then average odds for that handycap
        spread_handycaps = [dto.spread.handycap for dto in game_odds_dtos if dto.spread]
        agg_spread = None
        if spread_handycaps:
            most_common_handycap, _ = Counter(spread_handycaps).most_common(1)[0]
            spreads_with_common = [dto.spread for dto in game_odds_dtos if dto.spread and dto.spread.handycap == most_common_handycap]
            fav_odds = [s.winFavouriteOdd for s in spreads_with_common]
            und_odds = [s.winUnderdogOdd for s in spreads_with_common]
            if fav_odds and und_odds:
                avg_fav = sum(fav_odds) / len(fav_odds)
                avg_und = sum(und_odds) / len(und_odds)
                agg_spread = SpreadsDto(most_common_handycap, avg_fav, avg_und)

        # Aggregate Totals: most common total, then average over/under odds for that total
        totals_points = [dto.totals.total for dto in game_odds_dtos if dto.totals]
        agg_totals = None
        if totals_points:
            most_common_total, _ = Counter(totals_points).most_common(1)[0]
            totals_with_common = [dto.totals for dto in game_odds_dtos if dto.totals and dto.totals.total == most_common_total]
            over_odds = [t.overOdd for t in totals_with_common]
            under_odds = [t.underOdd for t in totals_with_common]
            if over_odds and under_odds:
                avg_over = sum(over_odds) / len(over_odds)
                avg_under = sum(under_odds) / len(under_odds)
                agg_totals = TotalsDto(most_common_total, avg_over, avg_under)

        # Compose aggregated GameOddsDTO (provider=None)
        agg_dto = GameOddsDTO(h2h=agg_h2h, spread=agg_spread, totals=agg_totals, provider=None)

        return agg_dto, game_odds_dtos
