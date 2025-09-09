import math
from typing import Tuple
from kicktipp_bot.models.game_dto import GameDTO

class TipCalculatorAdvanced:
    """Advanced tip calculation strategy based on h2h, spread and totals odds."""

    @staticmethod
    def round_half_up(n, decimals=0):
        """Commercial rounding: .5 always rounds up."""
        import math
        multiplier = 10 ** decimals
        return math.floor(n * multiplier + 0.5) / multiplier

    @staticmethod
    def calculate_tip(game_dto: GameDTO) -> Tuple[int, int]:
        h2h_home = h2h_away = h2h_draw = h2h_fav = None
        if game_dto.odds.h2h:
            h2h_home = TipCalculatorAdvanced.round_half_up(game_dto.odds.h2h.winHomeOdd, 2)
            h2h_away = TipCalculatorAdvanced.round_half_up(game_dto.odds.h2h.winAwayOdd, 2)
            h2h_draw = TipCalculatorAdvanced.round_half_up(game_dto.odds.h2h.drawOdd, 2)
            h2h_fav = "home" if h2h_home < h2h_away else "away"

        spread_handycap = spread_winFavouriteOdd = spread_winUnderdogOdd = None
        if game_dto.odds.spread:
            spread_handycap = abs(game_dto.odds.spread.handycap)
            spread_winFavouriteOdd = TipCalculatorAdvanced.round_half_up(game_dto.odds.spread.winFavouriteOdd, 2)
            spread_winUnderdogOdd = TipCalculatorAdvanced.round_half_up(game_dto.odds.spread.winUnderdogOdd, 2)

        totals_total = totals_overOdd = totals_underOdd = None
        if game_dto.odds.totals:
            totals_total = game_dto.odds.totals.total
            totals_overOdd = TipCalculatorAdvanced.round_half_up(game_dto.odds.totals.overOdd, 2)
            totals_underOdd = TipCalculatorAdvanced.round_half_up(game_dto.odds.totals.underOdd, 2)

        handycap = TipCalculatorAdvanced.round_half_up(spread_handycap)
        favGoals = underdogGoals = 0

        # make sure to have always even total goals
        totalGoals = math.floor(totals_total)
        if totalGoals % 2 != 0:
            totalGoals = math.ceil(totals_total)

        goals_left = totalGoals - handycap
        favGoals = handycap + goals_left//2
        underdogGoals = goals_left//2

        if h2h_fav == "home":
            homeGoals = favGoals
            awayGoals = underdogGoals
        else:
            homeGoals = underdogGoals
            awayGoals = favGoals

        return int(homeGoals), int(awayGoals)