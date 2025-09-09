from typing import Optional

class QuoteDTO:
    def __init__(self, home: float, draw: float, away: float, raw_text: Optional[str] = None):
        self.home = home
        self.draw = draw
        self.away = away
        self.raw_text = raw_text

    def __repr__(self):
        return f"QuoteDTO(home={self.home}, draw={self.draw}, away={self.away}, raw_text={self.raw_text})"
