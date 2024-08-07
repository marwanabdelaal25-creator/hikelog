"""Seasonal visit interval multipliers.

Author: Marwan Helmy

Winter slows evaporation -> longer intervals.
Summer dries packs faster -> shorter intervals.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional


@dataclass
class SeasonWindow:
    name: str
    start_month: int
    start_day: int
    end_month: int
    end_day: int
    multiplier: float


DEFAULT_SEASONS = [
    SeasonWindow("winter", 12, 1, 2, 28, 1.25),
    SeasonWindow("spring", 3, 1, 5, 31, 1.0),
    SeasonWindow("summer", 6, 1, 8, 31, 0.85),
    SeasonWindow("fall", 9, 1, 11, 30, 1.05),
]


class SeasonCalendar:
    def __init__(self, seasons: Optional[list[SeasonWindow]] = None, hemisphere: str = "north"):
        self.seasons = seasons or list(DEFAULT_SEASONS)
        self.hemisphere = hemisphere  # TODO: flip months for south

    def _day_of_year(self, when: date) -> int:
        return when.timetuple().tm_yday

    def _window_spans_year_end(self, w: SeasonWindow) -> bool:
        return (w.start_month, w.start_day) > (w.end_month, w.end_day)

    def _in_window(self, when: date, w: SeasonWindow) -> bool:
        md = (when.month, when.day)
        start = (w.start_month, w.start_day)
        end = (w.end_month, w.end_day)
        if self._window_spans_year_end(w):
            return md >= start or md <= end
        return start <= md <= end

    def season_for(self, when: date | datetime) -> str:
        if isinstance(when, datetime):
            when = when.date()
        for w in self.seasons:
            if self._in_window(when, w):
                return w.name
        return "spring"

    def multiplier_for(self, when: date | datetime) -> float:
        if isinstance(when, datetime):
            when = when.date()
        for w in self.seasons:
            if self._in_window(when, w):
                return w.multiplier
        return 1.0

    def describe(self, when: Optional[date] = None) -> dict:
        when = when or date.today()
        return {
            "date": when.isoformat(),
            "season": self.season_for(when),
            "multiplier": self.multiplier_for(when),
        }


def effective_visit_interval(base_days: int, multiplier: float) -> int:
    adjusted = base_days * multiplier
    return max(1, int(round(adjusted)))
