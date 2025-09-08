import random
from typing import Tuple
from kicktipp_bot.models.game import GameDTO

class TipCalculatorSimple:
	"""Simple tip calculation strategy based on h2h odds."""

	@staticmethod
	def calculate_tip(game_dto: GameDTO) -> Tuple[int, int]:
		"""
		Calculate betting tip based on the quotes in a GameDTO.

		Args:
			game_dto: GameDTO instance with .odds.h2h

		Returns:
			Tuple of (home_goals, away_goals) prediction
		"""
		home_quote = game_dto.odds.h2h.winHomeOdd
		away_quote = game_dto.odds.h2h.winAwayOdd

		quote_difference = home_quote - away_quote
		random_goal = random.randint(0, 1)
		coefficient = 0.3 if abs(quote_difference) > 7 else 0.75

		if abs(quote_difference) < 0.25:
			return random_goal, random_goal
		elif quote_difference < 0:
			home_goals = max(0, round(-quote_difference * coefficient)) + random_goal
			away_goals = random_goal
			return home_goals, away_goals
		else:
			home_goals = random_goal
			away_goals = max(0, round(quote_difference * coefficient)) + random_goal
			return home_goals, away_goals
