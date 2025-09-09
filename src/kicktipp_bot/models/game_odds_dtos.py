from typing import Optional

class GameOddsDTO:

    h2h=None
    spread=None
    totals=None

    def __init__(self, h2h: Optional["H2hDto"] = None, spread: Optional["SpreadsDto"] = None, totals: Optional["TotalsDto"] = None, provider: Optional[str] = None):
        self.h2h = h2h
        self.spread = spread
        self.totals = totals
        self.provider = provider
    def __repr__(self):
        return (f"GameOddsDTO(h2h={self.h2h}, spread={self.spread}, "
                f"totals={self.totals}, provider={self.provider})")

class H2hDto:
    def __init__(self, winHomeOdd: float, winAwayOdd: float, drawOdd: float):
        self.winHomeOdd = winHomeOdd
        self.drawOdd = drawOdd
        self.winAwayOdd = winAwayOdd
    def __repr__(self):
        return (f"H2hDto(winHomeOdd={self.winHomeOdd}, winAwayOdd={self.winAwayOdd}, "
                f"drawOdd={self.drawOdd})")

class SpreadsDto:
    def __init__(self, handycap: float, winFavouriteOdd: float, winUnderdogOdd: float):
        self.handycap = handycap
        self.winFavouriteOdd = winFavouriteOdd
        self.winUnderdogOdd = winUnderdogOdd
    def __repr__(self):
        return (f"SpreadsDto(handycap={self.handycap}, winFavouriteOdd={self.winFavouriteOdd}, "
                f"winUnderdogOdd={self.winUnderdogOdd})")

class TotalsDto:
    def __init__(self, total: float, overOdd: float, underOdd: float):
        self.total = total
        self.overOdd = overOdd
        self.underOdd = underOdd
    def __repr__(self):
        return (f"TotalsDto(total={self.total}, overOdd={self.overOdd}, "
                f"underOdd={self.underOdd})")
