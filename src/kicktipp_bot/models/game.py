"""Game model for representing football matches and calculating betting tips."""

import random
from datetime import datetime
from typing import List, Tuple, Union, Optional
from .game_odds_dtos import GameOddsDTO


class Game:
    """Represents a football game with teams, betting quotes, and tip calculation logic."""

    def __init__(self, home_team: str, away_team: str, odds: GameOddsDTO, game_time: datetime, detailed_odds: Optional[List[GameOddsDTO]] = None):
        """
        Initialize a Game instance.

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

    def calculate_tip(self) -> Tuple[int, int]:
        """
        Calculate betting tip based on the quotes.

        Args:
            home_quote: Quote for home team win (uses self.quotes[0] if None)
            away_quote: Quote for away team win (uses self.quotes[2] if None)

        Returns:
            Tuple of (home_goals, away_goals) prediction
        """
        # Default: nutze h2h-odds
        if home_quote is None and self.odds and self.odds.h2h:
            home_quote = self.odds.h2h.winHomeOdd
        if away_quote is None and self.odds and self.odds.h2h:
            away_quote = self.odds.h2h.winAwayOdd

        # Calculate quote difference (negative = home team more likely to win)
        quote_difference = home_quote - away_quote

        # Add randomness for more realistic scores
        random_goal = random.randint(0, 1)

        # Adjust coefficient based on how unequal the match is
        # Lower coefficient for very unequal games to avoid extreme scores
        coefficient = 0.3 if abs(quote_difference) > 7 else 0.75

        # Calculate tips based on quote difference
        if abs(quote_difference) < 0.25:
            # Very close match - predict draw-like result
            return random_goal, random_goal
        elif quote_difference < 0:
            # Home team favored
            home_goals = max(
                0, round(-quote_difference * coefficient)) + random_goal
            away_goals = random_goal
            return home_goals, away_goals
        else:
            # Away team favored
            home_goals = random_goal
            away_goals = max(
                0, round(quote_difference * coefficient)) + random_goal
            return home_goals, away_goals

    def __str__(self) -> str:
        """String representation of the game."""
        return f"{self.home_team} vs {self.away_team} at {self.game_time.strftime('%d.%m.%y %H:%M')}"

    def __repr__(self) -> str:
        """Detailed string representation for debugging."""
        return (f"Game(home='{self.home_team}', away='{self.away_team}', "
                f"game_time='{self.game_time}', odds={self.odds}, detailed_odds={self.detailed_odds})")
