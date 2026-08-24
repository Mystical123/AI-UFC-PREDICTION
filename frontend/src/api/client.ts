// Thin fetch wrapper. Dev server proxies /api -> the FastAPI backend
// (see vite.config.ts), so no CORS setup needed locally.
import type { ChatResponse, EventDetail, EventSummary, FightDetail, FighterDetail, PredictionResponse } from './types'

const BASE = '/api'

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`)
  if (!res.ok) {
    throw new Error(`${res.status} ${res.statusText} for ${path}`)
  }
  return res.json()
}

export const api = {
  listEvents: () => get<EventSummary[]>('/events'),
  getEvent: (slug: string) => get<EventDetail>(`/events/${slug}`),
  getFighter: (slug: string) => get<FighterDetail>(`/fighters/${slug}`),
  getFight: (id: number) => get<FightDetail>(`/fights/${id}`),
  getPrediction: (id: number) => get<PredictionResponse>(`/fights/${id}/prediction`),
  chat: async (message: string, opts?: { event_slug?: string; fighter?: string }): Promise<ChatResponse> => {
    const res = await fetch(`${BASE}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, ...opts }),
    })
    if (!res.ok) {
      throw new Error(`${res.status} ${res.statusText} for /chat`)
    }
    return res.json()
  },
}
