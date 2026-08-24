import { useEffect, useState } from 'react'
import { api } from '../api/client'
import type { EventSummary } from '../api/types'
import EventCard from '../components/EventCard'
import { isUpcoming } from '../utils/format'

export default function EventsPage() {
  const [events, setEvents] = useState<EventSummary[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api.listEvents().then(setEvents).catch((e) => setError(e.message))
  }, [])

  if (error) return <ErrorState message={error} />
  if (!events) return <LoadingGrid />

  const upcoming = events.filter((e) => isUpcoming(e.date_timestamp))
  const past = events.filter((e) => !isUpcoming(e.date_timestamp))

  return (
    <div className="space-y-10">
      <div>
        <h1 className="mb-4 font-display text-3xl font-bold tracking-wide text-text">Upcoming Events</h1>
        {upcoming.length === 0 ? (
          <p className="text-text-muted">No upcoming events found.</p>
        ) : (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {upcoming.map((event) => (
              <EventCard key={event.event_slug} event={event} />
            ))}
          </div>
        )}
      </div>

      {past.length > 0 && (
        <div>
          <h2 className="mb-4 font-display text-2xl font-bold tracking-wide text-text-muted">Past Events</h2>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {past.map((event) => (
              <EventCard key={event.event_slug} event={event} />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function LoadingGrid() {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {Array.from({ length: 6 }).map((_, i) => (
        <div key={i} className="h-32 animate-pulse rounded-xl border border-border bg-surface" />
      ))}
    </div>
  )
}

export function ErrorState({ message }: { message: string }) {
  return (
    <div className="rounded-xl border border-brand/30 bg-brand/10 p-6 text-center">
      <p className="font-medium text-text">Couldn't load data</p>
      <p className="mt-1 text-sm text-text-muted">{message}</p>
    </div>
  )
}
