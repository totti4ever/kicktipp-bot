import logging
import random
import json
import os
from datetime import datetime
from typing import List, Tuple, Union, Optional, Dict
from kicktipp_bot.config import Config
from kicktipp_bot.utils.odds_api import OddsApiClient, KICKTIPP_TO_API


class Game:
    """Represents a football game with teams, betting quotes, and tip calculation logic."""
    def __init__(self, home_team, away_team, quotes, game_time, odds_event=None, odds_api_client=None):
        self.home_team = home_team
        self.away_team = away_team
        self.quotes = quotes
        self.game_time = game_time
        self.odds_event = odds_event
        self.odds_api_client = odds_api_client
    def _debug_totals_table(self, event):
        """Debug-Ausgabe für Totals-Tabelle analog zu Spreads."""
        try:
            import tabulate
            totals_table = []
            for bookmaker in event.get("bookmakers", []):
                name = bookmaker.get('title', bookmaker.get('key', ''))
                for market in bookmaker.get('markets', []):
                    if market['key'] == 'totals':
                        over = under = point = None
                        for o in market.get('outcomes', []):
                            if o['name'] == 'Over':
                                over = o['price']
                                point = o['point']
                            if o['name'] == 'Under':
                                under = o['price']
                        if over is not None and under is not None and point is not None:
                            totals_table.append([name, point, over, under])
            if totals_table:
                headers = ["Anbieter", "Linie", "Over", "Under"]
                table_str = tabulate.tabulate(totals_table, headers, tablefmt="github", floatfmt=".2f")
                logging.info("totals (debug):\n" + table_str)
        except Exception as e:
            logging.warning(f"Totals-Debug-Tabellen-Ausgabe fehlgeschlagen: {e}")

    def _validate_quotes(self, quotes: List[str]) -> List[float]:
        """
        Validate and convert quotes to float values.

        Args:
            quotes: List of quote strings

        Returns:
            List of float quotes

        Raises:
            ValueError: If quotes are invalid
        """
        if len(quotes) != 3:
            raise ValueError(f"Expected 3 quotes, got {len(quotes)}")

        try:
            return [float(quote) for quote in quotes]
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid quote values: {quotes}") from e

    def calculate_tip(self, home_quote: Union[float, None] = None, away_quote: Union[float, None] = None) -> Tuple[int, int]:
        """
        Calculate betting tip based on the quotes and config strategy.
        Returns:
            Tuple of (home_goals, away_goals) prediction
        """
        if Config.ODDS_STRATEGY == "classic" or not self.odds_event or not self.odds_api_client:
            # Klassische Logik wie bisher
            if home_quote is None:
                home_quote = self.quotes[0]
            if away_quote is None:
                away_quote = self.quotes[2]
            quote_difference = home_quote - away_quote
            random_goal = random.randint(0, 1)
            coefficient = 0.3 if abs(quote_difference) > 7 else 0.75
            if abs(quote_difference) < 0.25:
                return random_goal, random_goal
            elif quote_difference < 0:
                home_goals = max(0, round(-quote_difference * coefficient)) + random_goal
                away_goals = random_goal
                self._persist_used_odds("classic", home_goals, away_goals)
                logging.info(f"Calculated tip: {home_goals} - {away_goals} (classic)")
                return home_goals, away_goals
            else:
                home_goals = random_goal
                away_goals = max(0, round(quote_difference * coefficient)) + random_goal
                self._persist_used_odds("classic", home_goals, away_goals)
                logging.info(f"Calculated tip: {home_goals} - {away_goals} (classic)")
                return home_goals, away_goals

        # SMART STRATEGY: Nutze Spread und Totals
        # 1. H2H-Quoten verdichten
        # Strukturierte Quoten-Ausgabe pro Anbieter (nur im Debug-Modus)
        from kicktipp_bot.utils.odds_api import KICKTIPP_TO_API
        import tabulate
        home_api = KICKTIPP_TO_API.get(self.home_team, self.home_team)
        away_api = KICKTIPP_TO_API.get(self.away_team, self.away_team)
        # H2H Tabelle sortiert nach Favoritenquote (asc)
        h2h_table = []
        for bookmaker in self.odds_event['bookmakers']:
            name = bookmaker.get('title', bookmaker.get('key', ''))
            h2h = None
            for market in bookmaker.get('markets', []):
                if market['key'] == 'h2h':
                    vals = {o['name']: o['price'] for o in market.get('outcomes', [])}
                    h2h = [vals.get(home_api, '-'), vals.get('Draw', '-'), vals.get(away_api, '-')]
            if h2h:
                h2h_table.append([name] + h2h)
        # Favorit bestimmen (kleinste Quote, robust)
        fav_col = None
        try:
            min_home = min([row[1] for row in h2h_table if isinstance(row[1], (int, float))], default=999)
            min_away = min([row[3] for row in h2h_table if isinstance(row[3], (int, float))], default=999)
            fav_col = 1 if min_home < min_away else 3
        except Exception:
            fav_col = 1  # Fallback
            import math
            spread = math.ceil(float(spread_val)) if spread_val else 1
        # Sortiere h2h_table nach der niedrigsten Favoritenquote (Spalte fav_col)
        if h2h_table:
            if fav_col is not None:
                h2h_table_sorted = sorted(h2h_table, key=lambda x: x[fav_col] if isinstance(x[fav_col], (int, float)) else 999)
            else:
                h2h_table_sorted = h2h_table
            headers = ["Anbieter", self.home_team, "Draw", self.away_team]
            table_str = tabulate.tabulate(h2h_table_sorted, headers, tablefmt="github", floatfmt=".2f")
            logging.info("h2h:\n" + table_str)

        # Spreads: Eine Zeile pro Anbieter, sortiert nach Quotendifferenz (engste Differenz zuerst)
        spread_table = []
        for bookmaker in self.odds_event['bookmakers']:
            name = bookmaker.get('title', bookmaker.get('key', ''))
            # h2h-Quoten für diesen Anbieter bestimmen
            h2h = None
            for market in bookmaker.get('markets', []):
                if market['key'] == 'h2h':
                    vals = {o['name']: o['price'] for o in market.get('outcomes', [])}
                    h2h = vals
            # Favorit nach h2h-Quote bestimmen
            fav_name = None
            underdog_name = None
            if h2h and len(h2h) >= 2:
                sorted_teams = sorted([(team, price) for team, price in h2h.items() if team != 'Draw'], key=lambda x: x[1])
                if len(sorted_teams) == 2:
                    fav_name, _ = sorted_teams[0]
                    underdog_name, _ = sorted_teams[1]
            for market in bookmaker.get('markets', []):
                if market['key'] == 'spreads':
                    # Alle Spreads für beide Teams sammeln
                    team_spreads = {o['name']: (o['point'], o['price']) for o in market.get('outcomes', [])}
                    if fav_name and underdog_name:
                        fav_spread = team_spreads.get(fav_name)
                        underdog_spread = team_spreads.get(underdog_name)
                        # Zeige beide, auch wenn beide point==0.0
                        if fav_spread and underdog_spread and fav_spread[0] == underdog_spread[0]:
                            # Beide haben denselben Spread (z.B. 0.0)
                            spread_table.append([name, fav_spread[0], fav_spread[1], underdog_spread[1]])
                        else:
                            # Zeige beide, falls vorhanden, sonst nur einen
                            if fav_spread:
                                spread_table.append([name, fav_spread[0], fav_spread[1], underdog_spread[1] if underdog_spread else '-'])
                            elif underdog_spread:
                                spread_table.append([name, underdog_spread[0], '-', underdog_spread[1]])
                    else:
                        # Fallback: alle Spreads auflisten
                        for team, (point, price) in team_spreads.items():
                            spread_table.append([name, point, price, '-'])
        spread_table_sorted = sorted(
            spread_table,
            key=lambda x: abs(x[2] - x[3]) if isinstance(x[2], (int, float)) and isinstance(x[3], (int, float)) else 999
        )
        if spread_table_sorted:
            headers = ["Anbieter", "Handicap", "Quote Favorit", "Quote Underdog"]
            table_str = tabulate.tabulate(spread_table_sorted, headers, tablefmt="github", floatfmt=".2f")
            logging.info("spreads:\n" + table_str)
        else:
            logging.info("spreads: Keine Daten gefunden.")

        # Totals: Sortiert nach Differenz (Over/Under, asc)
        totals_table = []
        for bookmaker in self.odds_event['bookmakers']:
            name = bookmaker.get('title', bookmaker.get('key', ''))
            for market in bookmaker.get('markets', []):
                if market['key'] == 'totals':
                    over = under = point = None
                    for o in market.get('outcomes', []):
                        if o['name'] == 'Over':
                            over = o['price']
                            point = o['point']
                        if o['name'] == 'Under':
                            under = o['price']
                    if over is not None and under is not None:
                        totals_table.append([name, point, over, under])
        totals_table_sorted = sorted(totals_table, key=lambda x: abs(x[2] - x[3]) if isinstance(x[2], (int, float)) and isinstance(x[3], (int, float)) else 999)
        if totals_table_sorted:
            headers = ["Anbieter", "Linie", "Over", "Under"]
            table_str = tabulate.tabulate(totals_table_sorted, headers, tablefmt="github", floatfmt=".2f")
            logging.info("totals:\n" + table_str)
        h2h_quotes = self._aggregate_market_quotes(self.odds_event, "h2h")
        # 2. Spread-Quoten verdichten (nur für Favorit)
        spread_info = self._aggregate_spread(self.odds_event)
        # 3. Totals-Quoten verdichten
        totals_info = self._aggregate_totals(self.odds_event)
        self._debug_totals_table(self.odds_event)

        # 4. Tendenz bestimmen
        min_h2h = min(h2h_quotes.items(), key=lambda x: x[1])
        tendenz = min_h2h[0]  # Teamname oder 'Draw'

        # 5. Spread-Wert bestimmen (z.B. +1.5 → 2 Tore Unterschied)
        spread_val = 0
        used_spread = None
        used_spread_point = None
        if spread_info:
            spread_val = spread_info["point"]
            used_spread = spread_info["price"]
            used_spread_point = spread_info["point"]
        # 6. Totals-Wert bestimmen (z.B. 3.5 → 4 Tore insgesamt)
        totals_val = round(totals_info["point"], 2) if totals_info else 2.0
        used_totals = round(totals_info["price"], 2) if totals_info and "price" in totals_info else None
        used_totals_point = round(totals_info["point"], 2) if totals_info and "point" in totals_info else None

        # Debug: Zwischenwerte für Ergebnisableitung
        logging.info(f"[DEBUG] Tendenz: {tendenz}, Spread: {spread_val}, Totals: {totals_val}")
        logging.info(f"[DEBUG] used_spread: {used_spread}, used_spread_point: {used_spread_point}, used_totals: {used_totals}, used_totals_point: {used_totals_point}")

        # 7. Ergebnis ableiten (Spread als Handicap, Totals als Gesamtanzahl Tore)
        # Neue Rundungslogik für total_goals: Richtung nach Over/Under-Quote
        over_quote = totals_info["price"] if totals_info and "price" in totals_info else None
        under_quote = totals_info["under"] if totals_info and "under" in totals_info else None
        # Neue Spread-Logik: Bei ganzzahligem häufigstem Spread, gehe +/-1 in Richtung des Durchschnitts aller Anbieter
        spread = 1
        if spread_info:
            most_common_spread = spread_info["point"]
            # Sammle nur die Spreads für den h2h-Favoriten
            fav_spreads = []
            # Ermittle Favoritenname (wie oben bestimmt)
            fav_name = None
            h2h_quotes = self._aggregate_market_quotes(self.odds_event, "h2h")
            if h2h_quotes:
                fav_name = min(h2h_quotes, key=h2h_quotes.get)
            # Backmapping auf API-Namen
            from kicktipp_bot.utils.odds_api import KICKTIPP_TO_API
            api_fav_names = set()
            if fav_name:
                api_fav_names.add(fav_name)
                api_name = KICKTIPP_TO_API.get(fav_name)
                if api_name:
                    api_fav_names.add(api_name)
            for bookmaker in self.odds_event["bookmakers"]:
                for market in bookmaker.get("markets", []):
                    if market["key"] == "spreads":
                        for o in market.get("outcomes", []):
                            # Vergleiche Spread-Namen robust mit allen API-Varianten
                            if o.get("name") in api_fav_names:
                                try:
                                    fav_spreads.append(float(o["point"]))
                                except Exception:
                                    pass
            if fav_spreads:
                avg_spread = sum(fav_spreads) / len(fav_spreads)
                abs_common = abs(most_common_spread)
                sign = 1 if most_common_spread >= 0 else -1
                if float(abs_common).is_integer():
                    abs_avg = abs(avg_spread)
                    if abs_avg > abs_common:
                        spread = sign * (int(abs_common) + 1)
                    else:
                        spread = sign * int(abs_common)
                else:
                    import math
                    spread = sign * math.ceil(abs_common)
            else:
                spread = int(round(abs(spread_val))) if spread_val else 1
        else:
            spread = 1
        # Standard-Rundung nach Over/Under-Quote
        from math import ceil, floor
        if over_quote is not None and under_quote is not None:
            if over_quote < under_quote:
                total_goals = int(ceil(totals_val))
            else:
                total_goals = int(floor(totals_val))
        else:
            total_goals = int(totals_val)

        # Spezialfall: spread==0 und total_goals ungerade
        if spread == 0 and total_goals % 2 == 1 and totals_info and "point" in totals_info:
            # Ermittle den häufigsten Totals-Wert (Linie)
            # Hole alle Totals-Linien aus totals_table_sorted (bereits nach Häufigkeit sortiert)
            # Fallback: nutze totals_info["point"]
            most_common_line = totals_info["point"]
            if most_common_line > total_goals:
                total_goals = int(ceil(totals_val))
            else:
                total_goals = int(floor(totals_val))
        logging.info(f"[DEBUG] total_goals: {total_goals}, spread (Torabstand): {spread}")
        if tendenz == self.home_team:
            base = (total_goals - spread) // 2
            home_goals = base + spread
            away_goals = base
            if home_goals + away_goals < total_goals:
                home_goals += 1
        elif tendenz == self.away_team:
            base = (total_goals - spread) // 2
            away_goals = base + spread
            home_goals = base
            if home_goals + away_goals < total_goals:
                away_goals += 1
        else:
            home_goals = away_goals = total_goals // 2
        home_goals = max(0, home_goals)
        away_goals = max(0, away_goals)
        logging.info(f"[DEBUG] Ergebnisableitung: home_goals={home_goals}, away_goals={away_goals}")
        # Persistiere verwendete Quoten explizit, runde alle Quoten auf 2 Nachkommastellen
        used_h2h = {k: round(h2h_quotes.get(k), 2) if h2h_quotes.get(k) is not None else None for k in [self.home_team, 'Draw', self.away_team]}
        for team, quote in used_h2h.items():
            if quote is None:
                logging.warning(f"No h2h quote found for {team} in event: {self.odds_event}")
        self._persist_used_odds("smart", home_goals, away_goals, used_h2h, used_spread, used_totals)
        spread_str = f"{used_spread} ({tendenz} {used_spread_point:+}) [aggregiert]" if used_spread is not None and used_spread_point is not None else str(used_spread)
        totals_str = f"{used_totals} (über {used_totals_point})" if used_totals is not None and used_totals_point is not None else str(used_totals)
        logging.info(
            f"Calculated tip: {home_goals} - {away_goals} (smart) | h2h: {used_h2h} | spread: {spread_str} | totals: {totals_str}"
        )
        return home_goals, away_goals

    def _aggregate_market_quotes(self, event, market_key) -> Dict[str, float]:
        """Aggregiere Quoten für einen Markt über alle Buchmacher (Median nach Winsorizing) und mappe Namen direkt beim Auslesen auf Kicktipp-Namen."""
        from statistics import median
        from kicktipp_bot.utils.odds_api import KICKTIPP_TO_API
        # Mapping: API-Name -> Kicktipp-Name
        api_to_kicktipp = {v: k for k, v in KICKTIPP_TO_API.items()}
        api_to_kicktipp["Draw"] = "Draw"
        all_quotes = {}
        for bookmaker in event.get("bookmakers", []):
            for market in bookmaker.get("markets", []):
                if market["key"] == market_key:
                    for outcome in market.get("outcomes", []):
                        # Mapping direkt beim Auslesen
                        api_name = outcome["name"]
                        kicktipp_name = api_to_kicktipp.get(api_name, api_name)
                        price = outcome["price"]
                        all_quotes.setdefault(kicktipp_name, []).append(price)
        # Für jede Option Median nach Winsorizing
        result = {}
        for name, prices in all_quotes.items():
            if len(prices) > 2:
                prices = sorted(prices)[1:-1]  # Streiche Extremwerte
            if prices:
                result[name] = round(median(prices), 2)
        return result

    def _aggregate_spread(self, event) -> Optional[Dict]:
        """
        Aggregiere Spread für den Favoriten (nach h2h-Quote) über alle Anbieter:
        häufigster Punkt, bei Gleichstand geringste durchschnittliche Differenz.
        Teamnamen werden direkt beim Auslesen gemappt und robust verglichen inkl. Mapping-Varianten.
        """
        from collections import Counter
        from statistics import median
        from kicktipp_bot.utils.odds_api import KICKTIPP_TO_API
        import unicodedata

        def norm(s):
            if not isinstance(s, str):
                return s
            return unicodedata.normalize('NFC', s).strip().casefold()

        api_to_kicktipp = {v: k for k, v in KICKTIPP_TO_API.items()}
        spreads = []
        for bookmaker in event.get("bookmakers", []):
            fav_name = None
            h2h = None
            for market in bookmaker.get("markets", []):
                if market["key"] == "h2h":
                    vals = {api_to_kicktipp.get(o['name'], o['name']): o['price'] for o in market.get('outcomes', [])}
                    h2h = vals
            if h2h and len(h2h) >= 2:
                sorted_teams = sorted([(team, price) for team, price in h2h.items() if team != 'Draw'], key=lambda x: x[1])
                if len(sorted_teams) == 2:
                    fav_name, _ = sorted_teams[0]
            fav_names = set()
            if fav_name:
                fav_names.add(fav_name)
                api_fav = KICKTIPP_TO_API.get(fav_name, None)
                if api_fav:
                    fav_names.add(api_fav)
                for k, v in KICKTIPP_TO_API.items():
                    if v == fav_name:
                        fav_names.add(k)
            for market in bookmaker.get("markets", []):
                if market["key"] == "spreads":
                    all_outcomes = market.get("outcomes", [])
                    for o in all_outcomes:
                        for fav_variant in fav_names:
                            if norm(o["name"]) == norm(fav_variant):
                                underdog_price = None
                                for o2 in all_outcomes:
                                    if o2["point"] == o["point"] and norm(o2["name"]) != norm(o["name"]):
                                        underdog_price = o2["price"]
                                        break
                                spreads.append((o["point"], o["price"], underdog_price))
                                break

        # Spread-Tabelle für Debug-Ausgabe (wie gehabt, aber außerhalb der Schleife)
        spread_table = []
        for bookmaker in self.odds_event['bookmakers']:
            name = bookmaker.get('title', bookmaker.get('key', ''))
            h2h = None
            for market in bookmaker.get('markets', []):
                if market['key'] == 'h2h':
                    vals = {o['name']: o['price'] for o in market.get('outcomes', [])}
                    h2h = vals
            fav_name = None
            underdog_name = None
            if h2h and len(h2h) >= 2:
                sorted_teams = sorted([(team, price) for team, price in h2h.items() if team != 'Draw'], key=lambda x: x[1])
                if len(sorted_teams) == 2:
                    fav_name, _ = sorted_teams[0]
                    underdog_name, _ = sorted_teams[1]
            for market in bookmaker.get('markets', []):
                if market['key'] == 'spreads':
                    team_spreads = {o['name']: (o['point'], o['price']) for o in market.get('outcomes', [])}
                    fav_spread = team_spreads.get(fav_name)
                    underdog_spread = team_spreads.get(underdog_name)
                    if fav_spread and underdog_spread and fav_spread[0] == underdog_spread[0]:
                        spread_table.append([name, fav_spread[0], fav_spread[1], underdog_spread[1]])
                    else:
                        if fav_spread:
                            spread_table.append([name, fav_spread[0], fav_spread[1], '-'])
                        if underdog_spread:
                            spread_table.append([name, underdog_spread[0], '-', underdog_spread[1]])

        # Jetzt point_counter korrekt nach Aufbau der spreads-Liste
        point_counter = Counter([point for point, _, _ in spreads])
        logging.info(f"Favoriten-Spreads (point, price, underdog_price): {spreads}")
        logging.info(f"Spread-Counter: {point_counter}")
        if not spreads:
            return None
        if not point_counter:
            return None
        max_count = max(point_counter.values())
        candidates = [point for point, count in point_counter.items() if count == max_count]
        if len(candidates) == 1:
            best_point = candidates[0]
        else:
            avg_diff = {}
            for point in candidates:
                diffs = [abs(price - underdog) for p, price, underdog in spreads if p == point and underdog is not None]
                avg_diff[point] = sum(diffs) / len(diffs) if diffs else float('inf')
            best_point = min(avg_diff, key=avg_diff.get)
        prices = [price for point, price, underdog in spreads if point == best_point]
        fav_med = round(median(prices), 2) if prices else None
        return {"point": best_point, "price": fav_med}

    def _aggregate_totals(self, event) -> Optional[Dict]:
        """
        Finde die Over/Under-Linie, die am häufigsten vorkommt;
        bei Gleichstand geringste durchschnittliche Differenz.
        Mapping direkt beim Auslesen.
        """
        from collections import Counter
        from statistics import median
        totals = []
        for bookmaker in event.get("bookmakers", []):
            for market in bookmaker.get("markets", []):
                if market["key"] == "totals":
                    over = under = point = None
                    for o in market.get("outcomes", []):
                        if o["name"] == "Over":
                            over = o["price"]
                            point = o["point"]
                        if o["name"] == "Under":
                            under = o["price"]
                    if over is not None and under is not None and point is not None:
                        totals.append((point, over, under))
        if not totals:
            return None
        point_counter = Counter([point for point, _, _ in totals])
        max_count = max(point_counter.values())
        candidates = [point for point, count in point_counter.items() if count == max_count]
        avg_diff = {}
        for point in candidates:
            diffs = [abs(over - under) for p, over, under in totals if p == point]
            avg_diff[point] = sum(diffs) / len(diffs) if diffs else float('inf')
        best_point = min(avg_diff, key=avg_diff.get)
        over_prices = [over for p, over, under in totals if p == best_point]
        under_prices = [under for p, over, under in totals if p == best_point]
        over_med = round(median(over_prices), 2) if over_prices else None
        under_med = round(median(under_prices), 2) if under_prices else None
        return {"point": round(best_point, 2), "price": over_med, "under": under_med}

    def _persist_used_odds(self, strategy, home_goals, away_goals, h2h=None, spread=None, totals=None):
        """Speichere verwendete Quoten und Tipp persistent für Backtesting, wenn aktiviert."""
        from kicktipp_bot.config import Config
        if not Config.USED_ODDS_WRITE:
            return
        data = {
            "datetime": datetime.now().isoformat(),
            "game_time": self.game_time.isoformat(),
            "home_team": self.home_team,
            "away_team": self.away_team,
            "strategy": strategy,
            "tip": [home_goals, away_goals],
            "quotes": self.quotes,
            "used_h2h": h2h,
            "used_spread": spread,
            "used_totals": totals
        }
        path = os.path.join(os.path.dirname(__file__), '../data/used_odds.json')
        try:
            arr = []
            if os.path.exists(path):
                with open(path, 'r') as f:
                    try:
                        arr = json.load(f)
                        if not isinstance(arr, list):
                            arr = []
                    except Exception:
                        arr = []
            arr.append(data)
            with open(path, 'w') as f:
                json.dump(arr, f, indent=2)
        except Exception as e:
            pass  # Logging kann hier zu Endlosschleifen führen
