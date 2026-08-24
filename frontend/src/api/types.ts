// Mirrors backend/schemas.py -- keep in sync by hand for now (no codegen yet).

export interface EventSummary {
  event_slug: string
  event_name: string
  date_timestamp: number | null
  date_text: string | null
  venue: string | null
}

export interface FighterSummary {
  slug: string
  name: string
  record: string | null
  height_inches: number | null
  reach_inches: number | null
  stance: string | null
  style: string | null
  age: number | null
  win_streak: number | null
  image_url: string | null
}

export interface FighterDetail extends FighterSummary {
  weight_lbs: number | null
  date_of_birth: string | null
  sig_strikes_landed_per_min: number | null
  sig_strike_accuracy_pct: number | null
  sig_strikes_absorbed_per_min: number | null
  sig_strike_defense_pct: number | null
  takedown_avg_per_15min: number | null
  takedown_accuracy_pct: number | null
  takedown_defense_pct: number | null
  submission_avg_per_15min: number | null
  profile_url: string | null
}

export interface FightSummary {
  id: number
  event_slug: string
  fighter_red_name: string
  fighter_blue_name: string
  fighter_red_image_url: string | null
  fighter_blue_image_url: string | null
  weight_class: string | null
  card_segment: string | null
}

export interface EventDetail extends EventSummary {
  fights: FightSummary[]
}

export interface FightDetail {
  id: number
  event: EventSummary
  fighter_red: FighterDetail | null
  fighter_blue: FighterDetail | null
  weight_class: string | null
  card_segment: string | null
}

export interface Citation {
  source: string
  title: string | null
  author: string | null
  url: string | null
  text: string
}

export interface PredictionResponse {
  fight_id: number
  prediction: string
  citations: Citation[]
}

export interface ChatResponse {
  response: string
  citations: Citation[]
}
