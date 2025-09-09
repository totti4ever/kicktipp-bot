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

        # Prediction and result fields (set later)
        self.actual_home_goals = None
        self.actual_away_goals = None
        self._predicted_result: Optional[Tuple[int, int]] = None
        self._prediction_time: Optional[datetime] = None

    @property
    def prediction(self) -> Optional[Tuple[Tuple[int, int], datetime]]:
        """
        Returns a tuple: ((home_goals, away_goals), prediction_time) or None
        """
        if self._predicted_result is not None and self._prediction_time is not None:
            return (self._predicted_result, self._prediction_time)
        return None

    @prediction.setter
    def prediction(self, value):
        """
        Set prediction as ((home_goals, away_goals), prediction_time) or just (home_goals, away_goals).
        If prediction_time is not provided, set to datetime.now().
        """
        from datetime import datetime
        if value is None:
            self._predicted_result = None
            self._prediction_time = None
            return
        if (isinstance(value, tuple) and len(value) == 2 and
            isinstance(value[0], tuple) and len(value[0]) == 2 and
            all(isinstance(x, int) for x in value[0]) and
            isinstance(value[1], datetime)):
            self._predicted_result = value[0]
            self._prediction_time = value[1]
            return
        if (isinstance(value, tuple) and len(value) == 2 and
            all(isinstance(x, int) for x in value)):
            self._predicted_result = value
            self._prediction_time = datetime.now()
            return
        raise ValueError("prediction must be ((int, int), datetime) or (int, int)")

    @property
    def predicted_result(self) -> Optional[Tuple[int, int]]:
        return self._predicted_result


    def __str__(self) -> str:
        """String representation of the game DTO."""
        return f"{self.home_team} vs {self.away_team} at {self.game_time.strftime('%d.%m.%y %H:%M')}"

    def __repr__(self) -> str:
        """Detailed string representation for debugging."""
        return (f"GameDTO(home='{self.home_team}', away='{self.away_team}', "
                f"game_time='{self.game_time}', odds={self.odds}, detailed_odds={self.detailed_odds})")

    def to_dict(self):
        """
        Convert the GameDTO to a JSON-serializable dict, including odds and prediction.
        """
        def odds_to_dict(odds):
            if hasattr(odds, '__dict__'):
                d = dict(odds.__dict__)
                # Recursively convert nested odds objects
                for k, v in d.items():
                    if hasattr(v, '__dict__'):
                        d[k] = dict(v.__dict__)
                return d
            return str(odds)

        result = {
            "home_team": self.home_team,
            "away_team": self.away_team,
            "game_time": self.game_time.isoformat() if self.game_time else None,
            "odds": odds_to_dict(self.odds),
            "detailed_odds": [odds_to_dict(o) for o in getattr(self, "detailed_odds", [])],
            "actual_home_goals": self.actual_home_goals,
            "actual_away_goals": self.actual_away_goals,
        }
        if self.prediction:
            (res, ts) = self.prediction
            result["predicted_home_goals"] = res[0]
            result["predicted_away_goals"] = res[1]
            result["prediction_time"] = ts.isoformat()
        return result
