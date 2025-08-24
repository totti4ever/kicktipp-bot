import logging
from typing import Optional
from selenium.webdriver.common.by import By
from ..utils.selenium_utils import SeleniumUtils

logger = logging.getLogger(__name__)

class QuoteExtractorKicktipp:
    @staticmethod
    def extract_quotes(game_row) -> Optional[list]:
        """Extract betting quotes directly from a game row element (kicktipp.de)."""
        quotes_element = SeleniumUtils.safe_find_element(
            game_row, By.XPATH, './/a[contains(@class, "quote-link")]')
        if not quotes_element:
            logger.warning("Could not find quotes element")
            return None

        quotes_raw = SeleniumUtils.safe_get_text(
            quotes_element, 'quotes element')
        if not quotes_raw:
            logger.warning("Could not extract quotes content")
            return None

        quotes_text = quotes_raw.replace("Quote: ", "").strip()

        if " / " in quotes_text:
            quotes = quotes_text.split(" / ")
        elif " | " in quotes_text:
            quotes = quotes_text.split(" | ")
        else:
            logger.warning(f"Could not parse quotes format: {quotes_text}")
            return None

        if len(quotes) != 3:
            logger.warning(f"Expected 3 quotes, got {len(quotes)}: {quotes}")
            return None

        return quotes
