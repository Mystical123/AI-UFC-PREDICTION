"""Pydantic response models -- the API's actual contract with callers (and
with FastAPI's auto-generated docs at /docs)."""
from datetime import date

from pydantic import BaseModel


class EventSummary(BaseModel):
    event_slug: str
    event_name: str
    date_timestamp: int | None
    date_text: str | None
    venue: str | None


class FighterSummary(BaseModel):
    slug: str
    name: str
    record: str | None
    height_inches: float | None
    reach_inches: float | None
    stance: str | None
    style: str | None
    age: int | None
    win_streak: int | None


class FighterDetail(FighterSummary):
    weight_lbs: float | None
    date_of_birth: date | None
    sig_strikes_landed_per_min: float | None
    sig_strike_accuracy_pct: float | None
    sig_strikes_absorbed_per_min: float | None
    sig_strike_defense_pct: float | None
    takedown_avg_per_15min: float | None
    takedown_accuracy_pct: float | None
    takedown_defense_pct: float | None
    submission_avg_per_15min: float | None
    profile_url: str | None


class FightSummary(BaseModel):
    id: int
    event_slug: str
    fighter_red_name: str
    fighter_blue_name: str
    weight_class: str | None
    card_segment: str | None


class EventDetail(EventSummary):
    fights: list[FightSummary]


class FightDetail(BaseModel):
    id: int
    event: EventSummary
    fighter_red: FighterDetail | None
    fighter_blue: FighterDetail | None
    weight_class: str | None
    card_segment: str | None


class Citation(BaseModel):
    source: str
    title: str | None
    author: str | None
    url: str | None
    text: str


class PredictionResponse(BaseModel):
    fight_id: int
    prediction: str
    citations: list[Citation]


class ChatRequest(BaseModel):
    message: str
    event_slug: str | None = None
    fighter: str | None = None


class ChatResponse(BaseModel):
    response: str
    citations: list[Citation]
