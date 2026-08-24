import { Link } from 'react-router-dom'
import type { EventSummary } from '../api/types'
import { formatEventDate, isUpcoming } from '../utils/format'
import Badge from './Badge'

export default function EventCard({ event }: { event: EventSummary }) {
  return (
    <Link
      to={`/events/${event.event_slug}`}
      className="group block cursor-pointer rounded-xl border border-border bg-surface/60 p-4 transition-colors duration-150 hover:border-brand/60 hover:bg-surface-hover"
    >
      <div className="mb-1.5 flex items-center justify-between">
        <Badge variant={isUpcoming(event.date_timestamp) ? 'brand' : 'muted'}>
          {isUpcoming(event.date_timestamp) ? 'Upcoming' : 'Past'}
        </Badge>
        <span className="text-xs text-text-muted">{formatEventDate(event.date_timestamp)}</span>
      </div>
      <h3 className="font-display text-xl font-semibold tracking-wide text-text group-hover:text-brand-hover">
        {event.event_name}
      </h3>
      {event.venue && <p className="mt-0.5 truncate text-xs text-text-muted">{event.venue}</p>}
    </Link>
  )
}
