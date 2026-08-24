import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { api } from '../api/client'
import type { EventDetail } from '../api/types'
import FightCard from '../components/FightCard'
import { formatEventDate } from '../utils/format'
import { ErrorState } from './EventsPage'

const SEGMENT_ORDER = ['main_card', 'prelims', 'early_prelims']

export default function EventDetailPage() {
  const { slug } = useParams<{ slug: string }>()
  const [event, setEvent] = useState<EventDetail | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!slug) return
    setEvent(null)
    api.getEvent(slug).then(setEvent).catch((e) => setError(e.message))
  }, [slug])

  if (error) return <ErrorState message={error} />
  if (!event) return <div className="h-40 animate-pulse rounded-xl border border-border bg-surface" />

  const bySegment = SEGMENT_ORDER.map((segment) => ({
    segment,
    fights: event.fights.filter((f) => f.card_segment === segment),
  })).filter((group) => group.fights.length > 0)

  return (
    <div className="space-y-8">
      <div>
        <h1 className="font-display text-3xl font-bold tracking-wide text-text sm:text-4xl">{event.event_name}</h1>
        <p className="mt-1 text-text-muted">
          {formatEventDate(event.date_timestamp)}
          {event.venue && ` • ${event.venue}`}
        </p>
      </div>

      {bySegment.map(({ segment, fights }) => (
        <div key={segment}>
          <h2 className="mb-2 font-display text-sm font-semibold uppercase tracking-wider text-text-muted">
            {segment.replace('_', ' ')}
          </h2>
          <div className="divide-y divide-border overflow-hidden rounded-xl border border-border bg-surface/60">
            {fights.map((fight) => (
              <FightCard key={fight.id} fight={fight} />
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}
