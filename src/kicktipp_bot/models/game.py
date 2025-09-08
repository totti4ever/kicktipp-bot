"""Game model for representing football matches and calculating betting tips."""

import random
from datetime import datetime
from typing import List, Tuple, Union, Optional
from .game_odds_dtos import GameOddsDTO



class GameDTO:
    """Data Transfer Object for a football game with teams, odds, and game time."""

    def __init__(self, home_team: str, away_team: str, odds: GameOddsDTO, game_time: datetime, detailed_odds: Optional[List[GameOddsDTO]] = None):
        """
        Initialize a GameDTO instance.

        Args:
            home_team: Name of the home team
            away_team: Name of the away team
            odds: Aggregated odds (GameOddsDTO)
            game_time: DateTime when the game starts
            detailed_odds: List of all available odds (optional)
        """
        self.home_team = home_team.strip()
        self.away_team = away_team.strip()
        self.odds = odds
        self.game_time = game_time
        self.detailed_odds = detailed_odds or []

    def __str__(self) -> str:
        """String representation of the game DTO."""
        return f"{self.home_team} vs {self.away_team} at {self.game_time.strftime('%d.%m.%y %H:%M')}"

    def __repr__(self) -> str:
        """Detailed string representation for debugging."""
        return (f"GameDTO(home='{self.home_team}', away='{self.away_team}', "
                f"game_time='{self.game_time}', odds={self.odds}, detailed_odds={self.detailed_odds})")
